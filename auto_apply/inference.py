"""Standalone pretrained model inference. Does not import slime, train, Ray or SGLang."""
import base64
import io
import json
import os
import re
import urllib.request


class EndpointModel:
    def __init__(self, base_url, model):
        self.base_url, self.model = base_url.rstrip("/"), model

    def generate(self, prompt, screenshot):
        body = {"model": self.model, "temperature": 0, "max_tokens": 256,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(screenshot).decode()}}
                ]}]}
        key = os.environ.get("MODEL_API_KEY", "")
        request = urllib.request.Request(self.base_url + "/chat/completions", json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)["choices"][0]["message"]["content"]


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
    blocks = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL)
    if not blocks:
        # Some small instruction models emit JSON without the XML envelope.
        blocks = [text.strip().removeprefix("```json").removesuffix("```").strip()]
    calls = [json.loads(block) for block in blocks]
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
