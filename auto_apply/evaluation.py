"""Deterministic fixture oracle, independent of the agent's selected profile paths."""
import base64
import json
from pathlib import Path
from .safety import snapshot
from .upstream import upstream_root


async def evaluate_fixture(page, expected_path):
    expected = json.loads(Path(expected_path).read_text(encoding="utf-8"))
    state = await snapshot(page)
    actual = {x["id"]: x["value"] for x in state}
    checks = {key: {"expected": value, "actual": actual.get(key), "correct": actual.get(key) == value}
              for key, value in expected.items()}
    resume = next(x for x in state if x["id"] == "resume")
    expected_hash = Path(expected_path).with_name("expected_resume.sha256").read_text().strip()
    checks["resume"] = {"correct": len(resume["files"]) == 1 and resume["files"][0]["name"] == "dummy-resume.txt" and resume["files"][0]["sha256"] == expected_hash}
    return {"checks": checks, "score": sum(v["correct"] for v in checks.values()) / len(checks),
            "all_correct": all(v["correct"] for v in checks.values()), "oracle": "local_fixture_v1"}


def export_episode(directory: Path):
    """Canonical OpenAI messages compatible with upstream's SFT Stage 2 input shape.

    Upload/select remain explicit extensions. No fabricated reasoning, tokens,
    log probabilities, policy rewards, or RL-ready claim for off-policy traces.
    """
    events = [json.loads(line) for line in (directory / "trajectory.jsonl").read_text(encoding="utf-8").splitlines()]
    def image(name):
        return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode((directory / name).read_bytes()).decode()}}
    messages = [{"role": "system", "content": "Fill the synthetic application with verified profile facts. Leave unknown answers empty. Stop for human review before submission."}]
    profile_path = directory / "profile.snapshot.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else None
    if profile:
        messages[0]["content"] += "\nCandidate profile: " + json.dumps(profile)
    extensions = set()
    native = {tool["function"]["name"] for tool in json.loads((upstream_root() / "openwebrl/env/prompts/tools_all.json").read_text())}
    # First navigation record is the initial observation; every subsequent action
    # is preceded by the previous action's resulting screenshot.
    for i, event in enumerate(events[1:], start=1):
        action = event["action"]
        name = action["name"]
        if name not in native:
            extensions.add(name)
        previous = events[i - 1]["observation_after"]["screenshot"]
        call_id = f"step_{i}"
        messages.extend([
            {"role": "user", "content": [image(previous)]},
            {"role": "assistant", "content": "", "tool_calls": [{"id": call_id, "type": "function", "function": {"name": name, "arguments": action["args"]}}]},
            {"role": "tool", "tool_call_id": call_id, "name": name,
             "content": [{"type": "text", "text": json.dumps(event["result"])}, image(event["observation_after"]["screenshot"])]},
        ])
    tools = json.loads((upstream_root() / "openwebrl/env/prompts/tools_all.json").read_text())
    for name in sorted(extensions):
        tools.append({"type": "function", "function": {"name": name, "description": "Application MVP extension; requires adapter support before upstream replay.", "parameters": {"type": "object"}}})
    result_path = directory / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    episode = {"messages": messages, "tools": tools, "metadata": {
        "task_id": "synthetic-application-v1", "policy": result.get("policy", "profile_baseline"),
        "model": result.get("model"), "model_inference": result.get("model_inference", False),
        "synthetic": profile.get("synthetic", True) if profile else True, "action_extensions": sorted(extensions), "requires_extension_adapter": bool(extensions),
        "reward": json.loads((directory / "fixture_evaluation.json").read_text())["score"] if (directory / "fixture_evaluation.json").exists() else None}}
    (directory / "openai_episode.jsonl").write_text(json.dumps(episode) + "\n", encoding="utf-8")
    url = events[0]["observation_after"]["url"]
    task = {"id": "synthetic-application-v1", "web": url,
            "ques": "Fill the synthetic application using this candidate profile: " + json.dumps(profile) + ". Leave unknown answers blank. Stop before final submission.",
            "metadata": {"task_id": "synthetic-application-v1", "start_url": url,
                         "synthetic": profile.get("synthetic", True) if profile else True}}
    (directory / "benchmark.jsonl").write_text(json.dumps(task) + "\n", encoding="utf-8")
    return episode
