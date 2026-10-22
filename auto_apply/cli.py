import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from .agent import fill_application
from .fixture import serve
from .inference import EndpointModel, LocalModel, OpenWebRLModel, smoke
from .computer import DEFAULT_MODEL, DEFAULT_REVISION, fill_with_computer
from .safety import SubmissionGuard, local_origin
from .trajectory import Trajectory
from .upstream import make_env, ROOT
from .evaluation import evaluate_fixture, export_episode
from .cloud import download_profile


async def run(args, origin, token, records):
    trace = Trajectory(Path(args.output) / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]))
    env = make_env(headless=not args.headed, browser_channel=args.browser_channel)
    try:
        await env.setup()
        guard = SubmissionGuard(origin, token)
        await guard.install(env.context)
        await env.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        path = "/smoke" if args.command == "smoke" else "/apply"
        url = args.url or origin + path
        if local_origin(url) != origin or url != origin + path:
            raise ValueError("This version accepts only the bundled local fixture URL.")
        await env.page.goto(url)
        await trace.record(env, {"name": "goto_url", "args": {"url": url}}, {"success": True})
        if args.command == "smoke":
            model = EndpointModel(args.endpoint, args.model) if args.endpoint else LocalModel(args.model)
            result = await smoke(env, model, trace, protocol="native" if args.endpoint else "focused-write")
        else:
            profile_path = download_profile(trace.directory / "candidate") if args.cloud_profile else Path(args.profile).resolve()
            if args.command == "agent":
                model = (EndpointModel(args.endpoint, args.model, max_tokens=2048, computer_use=True) if args.endpoint else
                         OpenWebRLModel(args.model, revision=args.model_revision))
                result = await fill_with_computer(
                    env, profile_path, trace, model, allow_personal=args.cloud_profile,
                    max_steps=args.max_steps, timeout=args.run_timeout,
                    coordinate_space=args.coordinate_space,
                )
            else:
                result = await fill_application(env, profile_path, trace, allow_personal=args.cloud_profile)
            if not args.cloud_profile and not args.application_id:
                evaluation = await evaluate_fixture(env.page, ROOT / "fixtures/expected.json")
                trace.write("fixture_evaluation.json", evaluation)
                result["fixture_evaluation"] = evaluation
                result["success"] = result.get("success", result["all_fills_verified"]) and evaluation["all_correct"]
            else:
                result["success"] = result.get("success", result["all_fills_verified"]) and bool(result["filled"])
                result["evaluation_note"] = "Per-field readback only. Original dummy-profile oracle does not apply."
            result["application_id"] = args.application_id or "original-fixture"
            if args.review:
                print("Unanswered questions:", json.dumps(result["needs_human"], indent=2))
                if await guard.approve_from_terminal(env.page):
                    await env.page.locator("#submit").click()
                    await env.page.locator("#receipt").wait_for()
                    result["submitted"] = bool(records)
            result["blocked_requests"] = guard.blocked
            trace.write("result.json", result)
            export_episode(trace.directory)
        await env.context.tracing.stop(path=trace.directory / "playwright-trace.zip")
        print(json.dumps({"artifact_directory": str(trace.directory.resolve()), **result}, indent=2))
        if args.inspect and not env.page.is_closed():
            print("Demo complete. Inspect the browser; close its window when finished.", flush=True)
            await env.page.wait_for_event("close", timeout=0)
        return 0 if result.get("success", result.get("all_fills_verified", False)) else 1
    except Exception as exc:
        trace.write("error.json", {"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        await env.exit()


def main():
    parser = argparse.ArgumentParser(description="OpenWebRL visual application agent and baseline benchmarks")
    parser.add_argument("command", choices=["agent", "demo", "smoke"],
                        help="agent: screenshot-driven OpenWebRL policy; demo: scripted baseline; smoke: inference test")
    parser.add_argument("--profile", default=str(ROOT / "profiles/dummy.json"))
    parser.add_argument("--cloud-profile", action="store_true", help="Sign in to Supabase and load your own profile and private resume")
    parser.add_argument("--application-id", help="Simulated application ID, e.g. workday-1 or lever-3")
    parser.add_argument("--output", default=str(ROOT / "artifacts"))
    parser.add_argument("--review", action="store_true", help="Offer terminal review and explicit approval for local synthetic submission")
    parser.add_argument("--headed", action="store_true", help="Show the Chromium browser while the agent works")
    parser.add_argument("--inspect", action="store_true", help="Keep the visible browser open until you close it")
    parser.add_argument("--browser-channel", choices=["msedge", "chrome"], help="Use installed Edge or Chrome instead of downloaded Chromium")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--url", help="Exact bundled local URL; other URLs are rejected")
    parser.add_argument("--endpoint", help="OpenAI-compatible base URL including /v1")
    parser.add_argument("--model", help="Visual policy model ID; agent defaults to OpenWebRL's released 9B SFT model")
    parser.add_argument("--model-revision", help="Pinned Hugging Face revision for local agent inference")
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--run-timeout", type=int, default=1800, help="Agent time budget in seconds")
    parser.add_argument("--coordinate-space", choices=['normalized', 'pixels'], default='normalized',
                        help="Model coordinate convention; the released Qwen-based policy uses normalized 0-1000")
    args = parser.parse_args()
    args.model = args.model or (DEFAULT_MODEL if args.command == "agent" else "HuggingFaceTB/SmolVLM-256M-Instruct")
    if args.command == "agent" and args.model == DEFAULT_MODEL and not args.model_revision:
        args.model_revision = DEFAULT_REVISION
    if args.max_steps < 1 or args.run_timeout < 1:
        parser.error("--max-steps and --run-timeout must be positive.")
    if args.inspect:
        args.headed = True
    if args.command == "smoke" and (args.cloud_profile or args.application_id):
        parser.error("Cloud profiles and application IDs are for the demo command.")
    with serve(args.port, args.application_id) as (origin, token, records):
        raise SystemExit(asyncio.run(run(args, origin, token, records)))


if __name__ == "__main__":
    main()
