# Continue Supabase provisioning

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
