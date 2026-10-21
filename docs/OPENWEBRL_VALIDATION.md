# OpenWebRL inspection and inference validation

Inspected checkout: `OpenWebRL/OpenWebRL`, revision `9a120949aca3e58a2628f4b4e6edd0474d984873` (cloned during development).

## Findings from source inspection

| Area | Source files | Finding |
| --- | --- | --- |
| Browser execution | `openwebrl/env/web_env.py`, `base_env.py` | Async Playwright-backed `WebEnv` exposes setup, screenshot, action execution, step and cleanup. Native actions include click/write/navigation; no file upload action. |
| Environment hosting | `local_process_env.py`, `sandbox_env.py`, `browser_use_env.py`, `env/config.yaml` | Local subprocess, Orchard sandbox and remote browser modes exist. Direct `WebEnv` suits a single local guarded episode. |
| Inference rollout | `openwebrl/generate_browser.py`, `response_format.py`, `base/utils.py` | Model responses become browser actions over multiple turns; browser_env and slime response formats exist. The full driver imports Torch, slime and SGLang components. |
| Evaluation | `openwebrl/run_evaluate.py`, `scripts/run_evaluation_local.sh` | A dedicated evaluation runner loads tasks from JSONL/parquet, performs rollout and judge evaluation. The local launcher can serve a checkpoint with SGLang; it does not require launching RL training. |
| Rewards | `openwebrl/reward_browser.py`, `openwebrl/eval/` | Format rewards and model judges support general browser and benchmark-specific success evaluation. This MVP uses a deterministic local oracle instead of an external judge. |
| Future data use | `sft/convert_to_openai_messages.py`, `sft/prepare_openai_for_llamafactory.py` | Canonical multimodal messages and tool calls form an existing SFT interchange path. MVP exports that shape and flags its action extensions. |

## Concrete blocker and minimal patch

Importing only `openwebrl.env.web_env.WebEnv` initially executed `openwebrl/__init__.py`, which eagerly imported `generate_browser` and its RL dependency chain. The first import failed with `ModuleNotFoundError: transformers`; continuing the original chain also requires the training stack.

Rather than replace OpenWebRL, the recorded patch makes root exports lazy. Browser-only operation then needs Playwright, Pillow, and timeout-decorator instead of the full GPU training runtime. A second one-line context setting disables service workers so the submission guard covers requests. The same upstream WebEnv executes browser actions.

## Actual tests performed

Environment: Windows, Python 3.14.3, NVIDIA RTX 5070-class laptop GPU with approximately 8 GB VRAM. Local model inference used CPU, not the GPU training runtime.

1. Cloned and inspected the upstream source and pinned its commit.
2. Ran the local application using the patched upstream WebEnv, without importing the training driver.
3. Downloaded pretrained `HuggingFaceTB/SmolVLM-256M-Instruct` and loaded it through Transformers. No model was trained or fine-tuned.
4. First attempted JSON action generation; the model emitted the wrong envelope and placeholder text. That smoke run failed and its raw response was saved.
5. Used the focused-write protocol: screenshot + instruction -> generated text -> native OpenWebRL write -> actual DOM readback. The model generated `ORCHID`, the browser field contained `ORCHID`, and the test passed.

This proves standalone pretrained inference can feed a browser action through OpenWebRL without RL training. It does **not** validate the upstream SGLang evaluation runner end to end, benchmark a released OpenWebRL checkpoint, establish general GUI planning ability, or make the tiny model suitable for job applications.

## Preserved integration points and limits

The pinned checkout, native action shapes, screenshots, benchmark JSONL task schema, and canonical OpenAI episode export preserve a path to OpenWebRL evaluation and future training. `upload_resume` and select-related `profile_fill` actions are explicit extensions and require replay/adapter support. These offline baseline traces are not on-policy RL samples. Future rollout integration must preserve the approval gate and missing-answer behavior.

No OpenEnv was installed or integrated, no framework replacement was made, and no RL launch script was run.

Primary references: [upstream source](https://github.com/OpenWebRL/OpenWebRL/tree/9a120949aca3e58a2628f4b4e6edd0474d984873), [SmolVLM model card](https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct).
