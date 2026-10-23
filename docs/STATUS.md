# MVP status — October 20, 2026

## Website-to-GPU connection ? October 23, 2026

The public website at https://open-apply.sweetghost128.chatgpt.site now exposes Start Agent on each simulated application. Supabase stores private owner-scoped jobs; an outbound-only worker on Context3 polls, snapshots the saved profile, checks the signed private resume URL and SHA-256, and launches the real OpenWebRL 9B model through the existing GPU 0 launcher. No inbound university port or user password is needed. One worker is maintained by a Context3 crontab restart and flock; caches, configuration (mode 600), logs and job artifacts stay under `/data01/tmalekar/open-apply`.

The website polls progress and a private browser screenshot every five seconds, supports cancellation and refresh recovery, and loads only independently verified answers when the user chooses ?Use verified answers in my draft.? Model-selected browser actions remain independent of the DOM audit. No automatic submission occurs. The exact profile-fill shortcut remains a separate baseline.

The live disposable-account Workday job `080f9760-72a1-4787-9a7c-4b3bf49a6ed1` completed with `success=true`, 11/11 fills verified (10 answers plus resume), 27 model actions, and `submitted=false`. Four unknown answers stayed empty. Fourteen live API checks passed, covering anonymous access, worker credentials, cross-user reads/cancellation, forged browser results, duplicate runs, owner cancellation, and actual model results/preview. A headless Edge browser test loaded the real answers into React and exercised Start Agent and Cancel against the live queue with no page errors. Evidence: `artifacts/website-agent-verification.json` and `artifacts/connected-agent-ui.png`.

All 41 Python tests, including browser submission guards, and three frontend tests passed; the frontend production build passed. A second headless browser check on the public deployed URL verified authenticated Start Agent and Cancel with no page errors. Public deployment source commit: `1eedeb48408e6f23e70792be2821277a79e0ec66`. Queue limits are one active job per user, five starts per hour and ten queued/running jobs globally, with expiration and worker leases. The server loads the model per run; startup takes several minutes. Other GPUs and unrelated processes were left untouched.

The security advisor flags the intentionally privileged RPC wrappers: user operations check authenticated ownership; worker operations require a separate high-entropy credential whose hash lives in the unexposed private schema. PUBLIC execution is revoked and grants are scoped to the intended callers. No service-role credential is used by the browser or worker. Leaked-password protection remains an existing project advisory. Real employer URLs remain unsupported.

## OpenWebRL computer-use deployment — October 22, 2026

The `agent` command now implements a model-driven screenshot/action loop through the real pinned OpenWebRL `WebEnv`. The released `OpenWebRL/OpenWebRL-9B-SFT` checkpoint is pinned to `4398ade320ea15660c2dfc125973232ea8bd33c7`. It receives screenshots, supplied facts, native tool schemas and action feedback. It chooses its own clicks, writes, scrolling, dropdown selection and resume upload. There is no deterministic-filler fallback. The earlier `demo` command remains a baseline benchmark.

The runtime is installed on Context3 under `/data01/tmalekar/open-apply`. GPU 0 is selected by UUID `GPU-b9defd43-7472-55d9-ed1f-271f39c3e878`, with an idle-process/memory check before starting and a lock for our runs. GPU 1 was occupied by another user's vLLM process and was not used. GPU 0 is exposed as logical CUDA device 0 to this process; GPUs 2 and 3 remain untouched.

Source and environments are on shared data storage. Model weights are under `/data01/tmalekar/cache/huggingface/hub`; browser/model/compiler caches, temporary files, logs and artifacts are configured under `/data01/tmalekar/open-apply`. No project files or model data are installed in home. The server environment and launcher templates are `scripts/server-env.sh` and `scripts/run-server-agent.sh`.

The adapter handles the checkpoint's Qwen function tags and normalized 0–1000 screen coordinates. Resume uploads and native dropdown selection are explicit coordinate-based execution extensions: the model chooses the target point and the supplied file/option; the executor does not discover and map fields for it. An editable-focus check prevents typing into the page body. Independent DOM readback and the original fixture oracle validate completion after the visual loop stops.

The original-form live GPU run passed all 13 independent fixture checks: 11 correct fills including the resume and two intentionally blank unknown answers. It finished with `stop_reason=done`, no submission, and no verification retry. Evidence on Context3: `/data01/tmalekar/open-apply/artifacts/20261022T061800Z-b0c00a2c/result.json`.

The multi-step Workday visual-policy run also passed: 11/11 fills verified, three model-chosen Continue clicks, resume uploaded, and four unknown answers left blank. It stopped with `done`, no submission, and no verification retry. Evidence: `/data01/tmalekar/open-apply/artifacts/20261022T062152Z-d86266c1/result.json`. The original run executed 24 model actions; Workday executed 30. These are real pretrained-model runs, separate from the scripted model doubles in regression tests.

All 38 regression tests passed on Context3, including blocked model Submit clicks, native dropdown/upload execution, and rejected premature completion. Both frontend and agent CI jobs passed for code commit `26ca714`: https://github.com/brave30/open-apply-agent/actions/runs/39733871232. GPU 0 was released after the tests and returned to 5 MiB/0% utilization with no compute processes; the existing GPU 1 job remained untouched. A combined `verification.json` and `verified-pilot-evidence.tar.gz` are saved under `/data01/tmalekar/open-apply`; the latter includes both complete run directories.

The website-to-worker connection and real employer URLs remain incomplete; the hosted site's existing profile-fill shortcut still uses its earlier TypeScript matcher. The server runner currently operates on the bundled simulations and does not turn the website button into a cloud browser job.

The older implementation notes below describe the baseline and are superseded where this update says otherwise.

## Visible test update — October 21, 2026

Added `--headed`, `--inspect`, and optional installed-browser selection via `--browser-channel`. The upstream launch patch now exposes those settings while retaining headless Chromium as the default. Downloaded headed Chromium failed with `spawn UNKNOWN` on this system; installed Microsoft Edge successfully ran the complete visible workflow with **13/13 checks**, uploaded resume, two unanswered fields left blank, and no submission. The completed form remains open until the user closes its browser window. Evidence: `artifacts/20261021T222052Z-163475c7/result.json`. Ruff passed after the change.

## Working and verified

- Cloned and inspected OpenWebRL at `9a120949aca3e58a2628f4b4e6edd0474d984873`.
- Browser execution uses upstream WebEnv, with a recorded lazy-import/service-worker patch. Browser-only import loads none of `slime`, Torch, SGLang, or Ray.
- Persistent Pydantic candidate profile and generated JSON Schema cover personal information, education, jobs, skills, resume files, and verified answers.
- The local application run filled ten stored text/select answers, uploaded the checked synthetic resume, and left salary/motivation empty with human-input requests.
- Independent fixture evaluation passed **13/13 checks**, including exact resume bytes and correct abstention. The default run made **no submission**.
- A real pretrained SmolVLM-256M CPU inference smoke test passed through an OpenWebRL write action, with the actual field containing `ORCHID`. No training ran.
- Submission defense tests blocked unapproved browser and direct HTTP attempts, rejected changed approved contents, and accepted a simulated explicit approval for exactly one synthetic application.
- Screenshots, action JSONL, profile snapshot, correctness results, Playwright trace, benchmark task JSONL, and canonical multimodal episode export are generated.
- **10 tests passed** in 37.22 seconds. Ruff checks passed. Editable package installation and the installed CLI help command passed on Windows.

## Evidence saved in this workspace

| Check | Artifact |
| --- | --- |
| Final application run | `artifacts/20261020T232156Z-a90aea0f/result.json` |
| Independent correctness oracle | `artifacts/20261020T232156Z-a90aea0f/fixture_evaluation.json` |
| Review values/file hash | `artifacts/20261020T232156Z-a90aea0f/review.json` |
| Browser trace | `artifacts/20261020T232156Z-a90aea0f/playwright-trace.zip` |
| Evaluation/SFT-shape exports | `artifacts/20261020T232156Z-a90aea0f/benchmark.jsonl`, `openai_episode.jsonl` |
| Real pretrained smoke success | `artifacts/20261020T231420Z-feedaac5/result.json`, `model_response.json` |
| Earlier native-JSON model failure | `artifacts/20261020T231147Z-340cbe7b/result.json`, `model_response.json` |
| Machine-readable test results | `artifacts/tests.xml` |

Artifacts are ignored by Git; they remain available locally. Source code and reproduction commands are in the repository.

## Incomplete or deliberately deferred

- The application policy is deterministic profile matching. General model-driven visual planning and a released OpenWebRL policy evaluation are not implemented/verified.
- The pretrained smoke test is one focused-field task. It does not prove autonomous navigation or application completion by that model. Native structured output from the tiny model failed on the first attempt.
- The adapter accepts only the bundled loopback fixture and synthetic profiles. Real job boards, multipage workflows, custom widgets, iframes/shadow DOM, controls without IDs, and broad question interpretation need more implementation and fixtures.
- Human-input requests are written to JSON and the console; profile editing currently means editing the JSON file and rerunning.
- Resume upload uses a text fixture. PDF/DOCX resume handling on real job boards has not been tested.
- The full upstream SGLang evaluation runner and SFT conversion were inspected but not executed. Hosted native endpoint mode has not been validated against an actual policy server.
- Exported select/upload/scroll actions need an adapter for upstream replay. These offline traces lack on-policy sampling metadata needed for RL; no claim is made that they can be passed directly into RL training.
- Linux/macOS setup scripts have not been exercised. This development run used Windows and Python 3.14.3.
- No OpenEnv integration, RL training, real applications, repository publication, or deployment occurred.

## Important implementation choices

The upstream root initializer eagerly imported the training driver; a minimal lazy-import patch avoids installing the GPU training stack for ordinary browser runs. The project retains OpenWebRL and its native action conventions.

The approval gate uses a fingerprint of reviewed field values and resume bytes. Browser routing blocks unapproved requests; the simulated server independently checks the approved multipart payload. This avoids trying to evaluate a page while Chromium has its navigation request paused, which deadlocked an earlier implementation.

The fixed fixture oracle must be independently updated when intentional changes are made to the dummy candidate's expected answers. The oracle reports those changes as mismatches until reviewed.

Future work should first add more local ATS-style fixtures and a reliable visual policy, then connect the guarded environment and explicit action extensions to upstream evaluation. RL training remains a later stage.
