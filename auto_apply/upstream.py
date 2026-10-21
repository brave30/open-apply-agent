"""Use upstream WebEnv directly; never import the RL training driver."""
import os
import sys
import subprocess
from pathlib import Path

PIN = "9a120949aca3e58a2628f4b4e6edd0474d984873"
ROOT = Path(__file__).resolve().parents[1]


def upstream_root() -> Path:
    root = Path(os.environ.get("OPENWEBRL_ROOT", str(ROOT / "vendor/OpenWebRL"))).resolve()
    if not (root / "openwebrl/env/web_env.py").is_file():
        raise RuntimeError("OpenWebRL missing. Run scripts/bootstrap.ps1 or scripts/bootstrap.sh.")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def make_env(*, headless=True, browser_channel=None):
    root = upstream_root()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    if revision != PIN:
        raise RuntimeError(f"Expected OpenWebRL {PIN}, found {revision}. Use the bootstrap script.")
    patch = ROOT / "patches/lazy-package-import.patch"
    check = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=root, capture_output=True)
    if check.returncode:
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=root, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=root, check=True)
    from openwebrl.env.web_env import WebEnv

    env = WebEnv(width=1280, height=900, dpr=1, max_retries=1,
                 wait_timeout=5000, screenshot_timeout=15000, start_url="about:blank",
                 resize_output_coords=False, resize_scale=1, image_patch_size=28,
                 tool_list=[], policy="Use stored candidate facts. Never submit without approval.")
    # Upstream's permissive flags are unnecessary for this local fixture.
    env.browser_args = ["--disable-dev-shm-usage"]
    env.headless = headless
    env.browser_channel = browser_channel
    return env
