"""Standalone pretrained model inference. Does not import slime, train, Ray or SGLang."""
import base64
import io
import json
import os
import re
import urllib.request


def computer_tools():
    from .upstream import upstream_root
    definitions = json.loads((upstream_root() / "openwebrl/env/prompts/tool_list.json").read_text(encoding="utf-8"))
    names = {"click", "write", "press_keys", "scroll", "wait", "done"}
    tools = [tool for tool in definitions if tool["function"]["name"] in names]
    for tool in tools:
        point = tool["function"]["parameters"].get("properties", {}).get("point_2d")
        if point:
            point["description"] = "The [x,y] position in the coordinate space specified by the task instructions."
    for name, properties, description in [
        ("upload_resume", {"point_2d": {"type": "array", "items": {"type": "number"}},
                           "resume_index": {"type": "integer"}}, "Upload the supplied resume at a visible file input."),
        ("select_option", {"point_2d": {"type": "array", "items": {"type": "number"}},
                           "label": {"type": "string"}}, "Choose the exact supplied fact in a native dropdown at the selected screen point."),
        ("call_user", {"response": {"type": "string"}}, "Stop and ask the user for missing information or assistance."),
    ]:
        tools.append({"type": "function", "function": {"name": name, "description": description,
                     "parameters": {"type": "object", "properties": properties, "required": list(properties)}}})
    return tools


class EndpointModel:
    def __init__(self, base_url, model, *, max_tokens=256, computer_use=False):
        self.base_url, self.model = base_url.rstrip("/"), model
        self.max_tokens = max_tokens
        self.computer_use = computer_use

    def generate(self, prompt, screenshot):
        body = {"model": self.model, "temperature": 0, "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(screenshot).decode()}}
                ]}]}
        if self.computer_use:
            body["messages"][0]["content"][0]["text"] = "Current browser screenshot. Choose the next computer-use action."
            body["messages"].insert(0, {"role": "system", "content": prompt})
            body["tools"] = computer_tools()
        key = os.environ.get("MODEL_API_KEY", "")
        request = urllib.request.Request(self.base_url + "/chat/completions", json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        with urllib.request.urlopen(request, timeout=120) as response:
            message = json.load(response)["choices"][0]["message"]
            if message.get("tool_calls"):
                return json.dumps([{"name": call["function"]["name"],
                                    "arguments": json.loads(call["function"]["arguments"])}
                                   for call in message["tool_calls"]])
            return message["content"]


class OpenWebRLModel:
    """Run the released visual policy on one explicitly selected CUDA device."""
    def __init__(self, model, *, revision=None, max_tokens=2048):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        if not torch.cuda.is_available():
            raise RuntimeError("The OpenWebRL visual policy requires a CUDA GPU or --endpoint.")
        self.model, self.max_tokens = model, max_tokens
        self.tools = computer_tools()
        self.processor = AutoProcessor.from_pretrained(model, revision=revision)
        self.network = AutoModelForImageTextToText.from_pretrained(
            model, revision=revision, dtype=torch.bfloat16, device_map={"": "cuda:0"},
            attn_implementation="sdpa",
        ).eval()
        self.revision = getattr(self.network.config, "_commit_hash", revision)

    def generate(self, prompt, screenshot):
        import torch
        from PIL import Image
        image = Image.open(io.BytesIO(screenshot)).convert("RGB")
        messages = [{"role": "system", "content": [{"type": "text", "text": prompt}]}, {"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": "Current browser screenshot. Inspect the visible input bounds carefully and choose the next tool call."},
        ]}]
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True,
            return_tensors="pt", enable_thinking=False, tools=self.tools,
        ).to(self.network.device)
        with torch.inference_mode():
            ids = self.network.generate(**inputs, max_new_tokens=self.max_tokens, do_sample=False)
        return self.processor.batch_decode(
            ids[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True,
        )[0]


class LocalModel:
    def __init__(self, model="HuggingFaceTB/SmolVLM-256M-Instruct"):
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText
        self.model = model
        torch.set_num_threads(min(8, os.cpu_count() or 1))
        self.processor = AutoProcessor.from_pretrained(model)
        self.network = AutoModelForImageTextToText.from_pretrained(model)
        self.network.eval()
        self.revision = getattr(self.network.config, "_commit_hash", None)

    def generate(self, prompt, screenshot):
        import torch
        from PIL import Image
        image = Image.open(io.BytesIO(screenshot)).convert("RGB")
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        text = self.processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = self.processor(text=text, images=[image], return_tensors="pt")
        with torch.inference_mode():
            ids = self.network.generate(**inputs, max_new_tokens=128, do_sample=False)
        return self.processor.batch_decode(ids[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]


def parse_actions(text):
    """Same tool-call envelope/argument conversion as upstream regex ToolParser."""
    blocks = re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.DOTALL)
    if not blocks:
        # Some small instruction models emit JSON without the XML envelope.
        blocks = [text.strip().removeprefix("```json").removesuffix("```").strip()]
    calls = []
    for block in blocks:
        if block.strip().startswith('<function='):
            function = re.fullmatch(r'\s*<function=([a-z_]+)>\s*(.*?)\s*</function>\s*', block, re.DOTALL)
            if not function:
                raise ValueError("Malformed Qwen function call.")
            arguments, end = {}, 0
            for parameter in re.finditer(r'<parameter=([a-z_][a-z0-9_]*)>\s*(.*?)\s*</parameter>', function[2], re.DOTALL):
                if function[2][end:parameter.start()].strip() or parameter[1] in arguments:
                    raise ValueError("Malformed or duplicate function parameter.")
                value = parameter[2].strip()
                try:
                    value = json.loads(value)
                except ValueError:
                    if parameter[1] not in {'message', 'response', 'direction', 'label'}:
                        raise ValueError("Numeric and array parameters must be JSON.") from None
                arguments[parameter[1]] = value
                end = parameter.end()
            if function[2][end:].strip():
                raise ValueError("Unexpected content in function parameters.")
            calls.append({'name': function[1], 'arguments': arguments})
            continue
        parsed = json.loads(block)
        calls.extend(parsed if isinstance(parsed, list) else [parsed])
    if any(not isinstance(c, dict) or not isinstance(c.get("name"), str) for c in calls):
        raise ValueError('Each tool call needs a string "name" and an "arguments" object, e.g. '
                         '{"name":"click","arguments":{"point_2d":[350,320]}}.')
    return [{"name": c["name"], "args": c.get("arguments", c.get("args", {}))} for c in calls]


async def smoke(env, model, trace, protocol="native"):
    """A narrow but real screenshot -> pretrained output -> browser action -> DOM assertion."""
    prompt = ('You control a browser. The Test word input is already focused. '
              'Type ORCHID into it. Output only this JSON action format, filling message with the requested word: '
              '{"name":"write","arguments":{"message":"the requested word"}}')
    if protocol == "focused-write":
        prompt = "The browser input is focused. The user asks you to type ORCHID. What text should you type? Answer with only the exact word."
    screenshot = await env.get_screenshot()
    trace.directory.joinpath("before.png").write_bytes(screenshot)
    raw = model.generate(prompt, screenshot)
    trace.write("model_response.json", {"model": model.model, "revision": getattr(model, "revision", None), "protocol": protocol, "prompt": prompt, "response": raw})
    try:
        actions = ([{"name": "write", "args": {"message": raw.strip()}}]
                   if protocol == "focused-write" else parse_actions(raw))
        # No arbitrary navigation, code evaluation, submission or untrusted file access.
        if len(actions) != 1 or actions[0]["name"] != "write" or not isinstance(actions[0]["args"].get("message"), str):
            raise ValueError("Smoke model must return exactly one write action")
        ok, feedback = await env.execute_single_action(actions[0])
        actual = await env.page.locator("#test").input_value()
        success = ok and actual == "ORCHID"
        await trace.record(env, actions[0], {"success": success, "feedback": feedback, "actual": actual}, policy="pretrained")
        result = {"success": success, "model": model.model, "actual": actual, "training_launched": False, "protocol": protocol}
    except (ValueError, KeyError, TypeError) as exc:
        result = {"success": False, "model": model.model, "error": str(exc), "training_launched": False}
    trace.write("result.json", result)
    return result
