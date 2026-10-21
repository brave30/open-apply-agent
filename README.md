# Open Apply Agent — first working version

A synthetic-data job application agent using **OpenWebRL's actual `WebEnv`**. It opens a locally hosted application, reads labelled controls, fills known candidate facts, uploads a resume, and stops for human review. No RL training or OpenEnv integration is included.

The application policy is a conservative deterministic baseline. A separate pretrained vision-model smoke test demonstrates standalone inference and browser execution. This is not yet a general model-driven application agent for real job boards.

## Multi-user web workspace

`web/` now contains a React + TypeScript website using Watermelon UI navigation and workspace components. It provides Supabase email/password accounts, per-user candidate profiles, private resume uploads, saved application drafts, and explicitly reviewed simulated submissions.

The catalog contains **20 fictional applications**: five Workday-style multi-step flows, five Greenhouse-style forms, five Lever-style forms, and five custom flows. Source is `web/src/catalog.ts`; generated browser fixtures are in `fixtures/applications.json`. These are independent test simulations, not real employer applications or complete ATS integrations.

See [web setup](web/README.md). Database migrations and tenant isolation tests live in `supabase/`. Without public Supabase configuration the website displays preview mode; it does not claim that cloud saving works.

To run the browser agent against a specific form:

```powershell
.venv/Scripts/python -m auto_apply.cli demo --application-id workday-1 --headed --inspect --browser-channel msedge
```

To load the signed-in candidate's cloud profile and private resume, set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`, then add `--cloud-profile`. The CLI prompts for the candidate's email/password without saving the password, or accepts a candidate JWT in `SUPABASE_ACCESS_TOKEN`. It downloads only that user's records using Supabase RLS. The agent still runs against the bundled local simulation; Chromium is not hosted by the website. Local artifacts contain a profile snapshot and remain Git-ignored. Cloud connectivity requires separate live verification after provisioning.

The original synthetic demo and its fixed correctness oracle remain available without these flags. Catalog/custom-profile runs report per-field readback and do not claim the original oracle's score.

## Run on Windows

Prerequisites: Git, Python 3.10+, internet for initial dependencies and Chromium.

```powershell
./scripts/bootstrap.ps1
.venv/Scripts/python -m auto_apply.cli demo
.venv/Scripts/python -m pytest -q
```

The demo starts its own server on an available loopback port, launches headless Chromium through OpenWebRL, fills the application, writes artifacts, and closes both browser and server. It requires no API key. Allow about 35 seconds for native browser click/write actions.

To watch it on your screen and inspect the finished form:

```powershell
.venv/Scripts/python -m auto_apply.cli demo --headed --inspect
```

Close the Chromium window when finished. This command does not approve or submit the application.

If downloaded Chromium cannot launch on Windows, use installed Microsoft Edge:

```powershell
.venv/Scripts/python -m auto_apply.cli demo --headed --inspect --browser-channel msedge
```

Installed Chrome can be selected with `--browser-channel chrome`. Visible Edge execution was verified on October 21, 2026, with all 13 fixture checks passing. The browser stays open until you close it.

On Linux/macOS:

```bash
bash scripts/bootstrap.sh
.venv/bin/python -m auto_apply.cli demo
.venv/bin/python -m pytest -q
```

Linux may also need `python -m playwright install-deps chromium` for system libraries. Windows was tested; Linux/macOS bootstrap paths have not been exercised here.

To offer explicit terminal approval for a **synthetic** submission:

```powershell
.venv/Scripts/python -m auto_apply.cli demo --review
```

Inspect the printed field values and resume hash, then type the exact randomized phrase. Other responses decline approval. The default command never submits. The browser is headless; use `review.json`, screenshots, and the terminal review to inspect it.

## Pretrained inference, without training

Install optional local inference dependencies and run:

```powershell
python -m uv pip install --python .venv/Scripts/python.exe -e '.[test,inference]'
.venv/Scripts/python -m auto_apply.cli smoke
```

If `uv` is unavailable, use `.venv/Scripts/python -m pip install -e '.[test,inference]'` instead. The local model download is approximately 500 MB and uses Hugging Face's cache. Inference runs on CPU by default.

The default model is `HuggingFaceTB/SmolVLM-256M-Instruct`. It receives the browser screenshot and an instruction to type a word into an already focused input. Its generated text becomes the `message` argument to OpenWebRL's `write` action. The test checks the actual rendered field value. A successful run produced `ORCHID`; no training ran. This narrow test does not demonstrate autonomous visual navigation or OpenWebRL's released policy weights.

For a separately served OpenWebRL/Qwen vision policy:

```powershell
# Only if the server requires a key:
$env:MODEL_API_KEY = 'your-local-secret'
.venv/Scripts/python -m auto_apply.cli smoke --endpoint http://127.0.0.1:30000/v1 --model your-served-model-id
```

The endpoint path accepts native JSON / `<tool_call>` actions. That endpoint mode is implemented but has not been tested against a hosted policy in this environment. The first local attempt at native JSON action generation failed; the simpler focused-write protocol passed. Failures are retained as failures in artifacts.

## Candidate data and missing answers

`profiles/dummy.json` is persistent, validated candidate data. `profiles/profile.schema.json` is its JSON Schema. Sections cover personal details, education, work history, skills, resume file paths and hashes, and answers with verification source/date.

Only exact recognized questions and stored facts are used. Multiple education records, multiple resumes, conflicting verified answers, unsupported controls, and unknown questions require human input. Salary and motivation deliberately remain empty in the demo. `needs_human.json` asks for the missing answers; edit the synthetic profile, add a verified question/answer with a date and source, and rerun. The agent never writes guessed answers back into the profile. The demo's independent oracle is fixed to the original dummy data: if you intentionally change expected answers, separately review/update `fixtures/expected.json` and, for a changed resume, `fixtures/expected_resume.sha256`. Otherwise the demo correctly reports an oracle mismatch.

Resume paths must stay inside the profile directory and their SHA-256 must match. The fixture uses a small text resume so upload checks require no PDF tooling. `scripts/create_dummy.py` regenerates the sample data and schema, overwriting the synthetic fixtures only.

## Submission protection

The MVP intentionally accepts only the bundled HTTP fixture at `127.0.0.1` and rejects real application URLs and non-synthetic profiles. `--port 8765 --url http://127.0.0.1:8765/apply` exercises explicit URL input; arbitrary job boards are not supported yet.

All browser network requests pass through a context-wide guard. Only the fixture's exact read paths are allowed by default. POST requests, unknown GET paths/query strings, external origins, and WebSockets are blocked. Service workers are disabled. The fixture server independently requires an approval capability header; DOM scripts cannot supply the secret through page state.

Terminal approval binds to a snapshot of every field and the SHA-256 of uploaded file contents. The local server checks the received multipart payload against that approved fingerprint; changed contents are rejected. Approval permits one POST attempt to the local `/submit` endpoint. The application policy and model smoke policy cannot create approval. Tests exercise click, Enter, native form submission, fetch, GET submission, direct HTTP bypass attempts, changed fields, and a simulated explicit approval.

These controls are designed and tested for the bundled simulation. They do not establish a universal submission detector for arbitrary websites.

## Trajectories and evaluation

Every run writes a unique directory under `artifacts/`:

| Artifact | Purpose |
| --- | --- |
| `trajectory.jsonl`, numbered PNGs | Actions, source provenance, execution results, post-action screenshots, upstream revision |
| `profile.snapshot.json` | Exact synthetic profile used in this run |
| `questions.json`, `needs_human.json`, `review.json` | Discovered controls, unresolved questions, final field/file snapshot |
| `result.json`, `fixture_evaluation.json` | Per-fill readback plus an independent fixture oracle including correct abstentions |
| `playwright-trace.zip` | Playwright trace viewer replay/debugging |
| `benchmark.jsonl` | Task shape accepted by OpenWebRL's `load_tasks_from_jsonl` |
| `openai_episode.jsonl` | Canonical multimodal OpenAI messages/tool calls matching upstream's SFT Stage 2 input structure |
| `model_response.json` | Raw model response and prompt for the smoke test |

View a browser trace with `.venv/Scripts/python -m playwright show-trace <path-to-zip>`.

The oracle is `fixtures/expected.json`; it checks ten text/select answers, the exact uploaded resume contents, and two deliberately blank answers. The application baseline is labelled off-policy. No token IDs, log probabilities, optimization, or on-policy RL batches are fabricated. Select/upload/DOM-scroll extensions are flagged in exported metadata and need an upstream adapter before replay/training. Export shape compatibility is tested; full upstream SFT conversion and RL training have not been run.

Benchmark exports contain the run's ephemeral localhost URL. Rehost the fixture on a fixed port and update the URL before a future upstream evaluation run. That raw evaluation runner does not automatically inherit this project's submission guard; do not run it against real applications.

## OpenWebRL integration

Source: [OpenWebRL/OpenWebRL](https://github.com/OpenWebRL/OpenWebRL), pinned to `9a120949aca3e58a2628f4b4e6edd0474d984873`. Bootstrap clones it into ignored `vendor/OpenWebRL`; `OPENWEBRL_ROOT` can select another checkout at the same revision.

`auto_apply/upstream.py` instantiates upstream `openwebrl.env.web_env.WebEnv`; clicks, writes, screenshots, and lifecycle use that implementation. Selects and file uploads use small Playwright extensions on its page because the native action dispatcher has no resume-upload action. There is no substitute browser framework.

`patches/lazy-package-import.patch` records small upstream changes: lazy package exports to avoid the eager RL imports, blocked service workers for reliable request interception, and an optional headed-browser launch setting. The adapter verifies the pinned commit and applies the patch idempotently. Upstream public exports remain available lazily; RL internals are otherwise untouched. The adapter also removes upstream's permissive browser launch flags.

Read [the framework inspection](docs/OPENWEBRL_VALIDATION.md), [the plain-language workflow](docs/WORKFLOW.md), and [the implementation status](docs/STATUS.md).

## Scope remaining

Real job board URLs, multipage flows, iframes/shadow DOM, custom widgets, unlabeled/id-less controls, profile editing UI, reliable general visual planning, and an OpenWebRL policy benchmark are incomplete. Profile matching intentionally recognizes a small question vocabulary. RL training is deferred. Generalizing the browser environment requires new task fixtures, guarded adapters and evaluation coverage.

## License

Apache-2.0; see `LICENSE` and `NOTICE`. OpenWebRL retains its upstream license and attribution in its checkout. Model weights retain their own licenses.
