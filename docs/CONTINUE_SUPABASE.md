# Continue Supabase provisioning

## Provisioning update — October 21, 2026

- Supabase connector is available. With the user's confirmation, created the free ($0/month quoted) `open-apply-agent` project in brave30's Org, region `us-east-1`, reference `aajwxgywjrymkjfmqtbz`.
- API origin: https://aajwxgywjrymkjfmqtbz.supabase.co. Modern publishable key is in ignored `web/.env.local`; no service-role key is used.
- Applied `workspace` and `catalog` migrations. Verified all four public tables have RLS, the catalog contains 20 rows, and the private resumes bucket has a 5 MB limit.
- All eight pgTAP tenant tests passed against this new dedicated project in a rolled-back transaction. The MCP returns only the last result set, so results were collected into a temporary table and returned as one JSON array.
- All 18 live checks passed through the public client API with two disposable synthetic accounts: password sign-in, catalog access, private profiles, cross-tenant read/update/upload/download/submission denial, resume hash, draft persistence, stale review rejection, snapshot submission, duplicate rejection, protected submitted resume, and Python cloud-profile browser execution.
- Removed the disposable resume through Storage API and deleted both synthetic accounts after sign-out; verified no test users, storage objects, profiles, or submissions remain. Public Auth settings confirm email/password is enabled and email confirmation remains enabled.
- Python evidence: `artifacts/20261021T233845Z-bf0ac0e9/result.json`: 11 filled fields verified, missing answers left unanswered, no submission. Summary: `artifacts/supabase-live-verification.json`. Scratch verifier: `artifacts/verify-supabase.mjs` (credentials supplied through hidden stdin, not persisted).
- Frontend build and all three frontend tests passed. Browser UI QA remains unavailable because this session has no browser surfaces.
- Republished the SAME owner-private Site successfully: https://open-apply-workspace-brave30.sweetghost128.chatgpt.site.
- Site source commit: `77591e0dbb77b3d3fa1c1ac0eda7e06e57b67787`; saved version: `appgprj_6ad9464497c48191a85fde8b010eff8b~appgver_1d0fabe92e308191941d64a01154d5fb`; deployment: `appgdep_6ad94d11a5f881918ca93f8681248aed`.
- Latest pre-update GitHub CI is green: https://github.com/brave30/open-apply-agent/actions/runs/39692735748.
- Security advisor reports the intentionally authenticated `SECURITY DEFINER` submission RPC. It requires `auth.uid()`, locks only the owner's draft, compares the reviewed snapshot, checks resume ownership/existence, and denies anonymous/public execute. [Advisor reference](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable). Performance info notices: two unindexed catalog foreign keys and unused indexes on the new project.

### Remaining dashboard action

The connector cannot read/write Auth URL configuration, and no browser is connected. The user was asked to open https://supabase.com/dashboard/project/aajwxgywjrymkjfmqtbz/auth/url-configuration, set Site URL to `https://open-apply-workspace-brave30.sweetghost128.chatgpt.site`, and allow that URL plus `http://127.0.0.1:5173`. Do not claim email confirmation/reset redirects have been verified until this is saved and tested. Keep email confirmation enabled; configure production SMTP before broader signup traffic. Account deletion/export UI, orphan cleanup, and abuse monitoring remain deferred.

The sections below preserve the earlier handoff; their unprovisioned status is superseded by this update.

The user authorized building and hosting a React + TypeScript candidate website using Watermelon UI, Supabase, twenty application simulations (five each Workday, Greenhouse, Lever, Other), and a GitHub repository. They said Supabase was connected. Discovery confirmed the Supabase plugin is installed, but this session never received its tools; no browser surfaces were available either. Do not repeat installation instructions. Discover newly available Supabase tools first.

## Completed

- Private GitHub repository: https://github.com/brave30/open-apply-agent
- React site source: `web/`; npm dependencies installed; build and 3 unit tests passed.
- Navigation and workspace shell adapt Watermelon UI's Agndex Dashboard, with attribution.
- Initial browser/profile suite: 13 Python tests passed, including Workday multi-step flow and submission protection. Four additional mocked cloud adapter tests passed separately.
- Supabase migrations: `supabase/migrations/202610210001_workspace.sql` and `202610210002_catalog.sql`.
- SQL tenancy tests in `supabase/tests/tenant_isolation.sql` are written but NOT run.
- Owner-private Sites preview deployed successfully:
  https://open-apply-workspace-brave30.sweetghost128.chatgpt.site
- Site project ID: `appgprj_6ad9464497c48191a85fde8b010eff8b`
- Published version: `appgprj_6ad9464497c48191a85fde8b010eff8b~appgver_e93670232ff08191be06f29d1a4b35d8`
- Deployment: `appgdep_6ad94806b37081918ff8b9a4b63ebd15`
- Source checkout for Sites: `artifacts/site-source`; source commit `40c26b7193225cfdaa782923ba79701edd6b4bd3`.
- Hosting manifest also tracked in `web/.openai/hosting.json`. Reuse this project; never create a second Site.
- GitHub source is the full project; Sites source is the frontend only. Sync frontend edits to the Sites checkout before republishing with its source helper and fresh credentials. Do not put credentials in files or logs.

## Required next

1. Discover Supabase tools; list the user's organizations/projects. Reuse an appropriate dedicated project if identified, otherwise create a free project within the user's authorized account. Do not incur paid charges.
2. Apply both migrations in order. Verify table grants, RLS, private resumes bucket and owner policies. Run tenant isolation tests in a test environment; use disposable synthetic test users and verify uploads/submission behavior with at least two users.
3. Configure Supabase Auth Site URL and email/password redirect URLs for the deployed Site and http://127.0.0.1:5173. Keep email verification enabled. Do not disable authentication to make testing easier.
4. Put only public build-time URL/publishable key in ignored `web/.env.local`; never expose a service-role or management secret in VITE variables.
5. Rebuild, verify signup/login, profile persistence, resume upload, draft save, stale review rejection and explicit simulated submission.
6. Update and republish the SAME owner-private Site. A publicly accessible multi-user release requires the user's audience preference; current Site is owner-private by default.
7. Verify the Python `demo --cloud-profile --application-id workday-1` against a synthetic cloud account. It signs in using getpass or a candidate JWT and downloads only the user's records; it does not use a service key. It runs Chromium locally, not in the static host.
8. Push tested updates to GitHub and check Actions. First run failed because ubuntu-latest became 26.04, unsupported by pinned Playwright 1.58.0. The workflow now pins ubuntu-24.04. Check current run rather than assuming it passed.

## Local execution notes

- Project: C:/Users/brave/Desktop/auto-apply
- GitHub authenticated as brave30 through `gh`.
- Windows sandbox requires escalation for browser launches, dependency networking and .git writes.
- Elevated Git sees sandbox-owned repos. Use process-scoped GIT_CONFIG_COUNT/GIT_CONFIG_KEY_0=safe.directory/GIT_CONFIG_VALUE_0 with the exact workspace or vendor/OpenWebRL path, rather than permanent global exceptions.
- System npm reliably runs as `node 'C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js'`. The Sites dependency helper misresolved npm on this host.
- Use unique `--basetemp=artifacts/<name>` for pytest; the default temp root has ACL conflicts.
- Current frontend is visibly labelled preview mode because Supabase is unconfigured. Do not claim accounts or cloud persistence are live until tested.
- Browser UI QA was unavailable. Build, unit tests and local Python browser fixtures passed; these do not substitute for frontend visual QA or live database checks.
