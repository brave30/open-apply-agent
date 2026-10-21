from pathlib import Path
import hashlib
import json
from .forms import DISCOVER, match
from .profile import Profile
from .safety import snapshot


async def fill_application(env, profile_path: Path, trace, *, allow_personal=False, _state=None):
    profile = Profile.load(profile_path)
    if not profile.synthetic and not allow_personal:
        raise ValueError("This MVP only accepts synthetic candidate profiles.")
    trace.write("profile.snapshot.json", profile.model_dump())
    facts = profile.facts()
    fields = await env.page.evaluate(DISCOVER)
    state = _state if _state is not None else {"questions": [], "missing": [], "filled": [], "pages": 0}
    state["pages"] += 1
    if state["pages"] > 10:
        raise RuntimeError("Application exceeded the supported page limit.")
    state["questions"].extend(fields)
    trace.write("questions.json", state["questions"])
    missing, filled = state["missing"], state["filled"]
    for field in fields:
        source = match(field, profile)
        question = {"field_id": field["id"], "question": field["label"], "required": field["required"]}
        if not source:
            missing.append({**question, "reason": "Missing, ambiguous, or unverified information. Please supply and verify this answer in the profile."})
            continue
        # Escape IDs without allowing page-supplied selectors.
        locator = env.page.locator('[id=' + json.dumps(field["id"]) + ']')
        before_scroll = await env.page.evaluate("window.scrollY")
        await locator.scroll_into_view_if_needed()
        if await env.page.evaluate("window.scrollY") != before_scroll:
            await trace.record(env, {"name": "scroll_to_field", "args": {"field_id": field["id"]}}, {"success": True}, policy="profile")
        action = {"name": "profile_fill", "args": {"field_id": field["id"], "source": source}}
        if source.startswith("resume_files"):
            resume = profile.resume_files[0]
            path = (profile_path.parent / resume.path).resolve()
            if not path.is_relative_to(profile_path.parent.resolve()):
                raise ValueError("Resume must be inside the profile directory.")
            if hashlib.sha256(path.read_bytes()).hexdigest() != resume.sha256:
                raise ValueError("Resume hash mismatch: review the file before uploading.")
            await locator.set_input_files(path)
            actual = await locator.evaluate("e => e.files[0].name")
            success = actual == path.name
            action["name"] = "upload_resume"  # Explicit extension; upstream has no upload tool.
            action["args"].update({"file": resume.path, "sha256": resume.sha256})
        elif field["tag"] == "select":
            value = facts[source]
            options = [o for o in field["options"] if o["label"].casefold() == value.casefold()]
            if len(options) != 1:
                missing.append({**question, "reason": "No unambiguous option matches stored answer."})
                continue
            await locator.select_option(value=options[0]["value"])
            action["args"]["value"] = options[0]["value"]
            actual = await locator.input_value()
            success = actual == options[0]["value"]
        elif field["type"] in {"text", "email", "tel", "url", "number", "textarea"} or field["tag"] == "textarea":
            box = await locator.bounding_box()
            click = {"name": "click", "args": {"point_2d": [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2]}}
            ok, feedback = await env.execute_single_action(click)
            if not ok:
                raise RuntimeError(feedback)
            await trace.record(env, click, {"success": ok, "feedback": feedback}, policy="profile")
            action = {"name": "write", "args": {"message": facts[source]}}
            success, feedback = await env.execute_single_action(action)
            actual = await locator.input_value()
            success = success and actual == facts[source]
        else:
            missing.append({**question, "reason": "Unsupported control; human input required."})
            continue
        await trace.record(env, action, {"success": success, "actual": actual}, source=source, policy="profile")
        filled.append({**question, "source": source, "correct": success})
    next_step = env.page.locator("#next-step")
    if await next_step.count() and await next_step.is_visible():
        await next_step.click()
        await trace.record(env, {"name": "application_next_step", "args": {}}, {"success": True}, policy="profile")
        return await fill_application(env, profile_path, trace, allow_personal=allow_personal, _state=state)
    trace.write("needs_human.json", missing)
    trace.write("review.json", await snapshot(env.page))
    result = {"filled": filled, "needs_human": missing, "all_fills_verified": all(x["correct"] for x in filled),
              "submitted": False, "policy": "deterministic_profile_baseline", "model_inference": False}
    trace.write("result.json", result)
    return result
