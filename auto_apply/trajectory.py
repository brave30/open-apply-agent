from datetime import datetime, timezone
from pathlib import Path
import json
from .upstream import PIN


class Trajectory:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=False)
        self.events = directory / "trajectory.jsonl"
        self.index = 0

    async def record(self, env, action, result, **extra):
        name = f"{self.index:03d}.png"
        (self.directory / name).write_bytes(await env.get_screenshot())
        event = {"schema_version": 1, "step": self.index,
                 "timestamp": datetime.now(timezone.utc).isoformat(),
                 "framework": "OpenWebRL", "upstream_commit": PIN,
                 "observation_after": {"screenshot": name, "url": env.page.url},
                 "action": action, "result": result, **extra}
        with self.events.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        self.index += 1

    def write(self, name, value):
        (self.directory / name).write_text(json.dumps(value, indent=2), encoding="utf-8")
