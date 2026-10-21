# Open Apply web workspace

React 19 + TypeScript + Vite. Navigation and workspace shell adapt Watermelon UI's Agndex Dashboard; attribution is in THIRD_PARTY_NOTICES.md.

## Develop

```powershell
cd web
npm ci
Copy-Item .env.example .env.local
# Set the project's public Supabase URL and publishable key in .env.local.
npm run dev
```

Without those variables, the website explicitly runs in preview mode. You can browse all twenty simulated roles, but accounts and cloud saving are unavailable. Candidate data is never silently saved to browser local storage as a database substitute. Supabase Auth manages its own session storage.

## Database

Apply both SQL migrations in ../supabase/migrations to a dedicated Supabase project in filename order. They create candidate_profiles, applications, application_drafts, application_submissions, and the private resumes storage bucket. Row-level security limits personal records and resume paths to the authenticated user's UUID. The public browser key cannot modify the catalog or write submission records directly.

Configure Supabase Auth's Site URL and allowed redirect URLs with the deployed website origin and your local development origin (http://127.0.0.1:5173). Keep email confirmation enabled; configure production SMTP before broader signup traffic. No service-role or management token belongs in VITE_ variables.

The simulated submission RPC locks the draft, compares the reviewed answers and resume with stored values, verifies resume ownership and file existence, and atomically saves a submission snapshot. It never sends data to real employers. Submissions cannot be edited by the browser.

The catalog is intentionally versioned in src/catalog.ts. Regenerate its matching database seed and local Python fixtures with:

```powershell
node scripts/generate-fixtures.mjs
```

Tests: `npm test` and `npm run build`. Database tenancy tests: `supabase test db` against a local test instance, after migrations. Hosted database tests require a configured test project; frontend unit tests do not establish live tenant isolation.

## Hosting

`npm run build` produces dist, suitable for Sites or a static hosting provider. Public Supabase values are build-time configuration, so rebuild when they change. .openai/hosting.json records the Sites project identity. The initial Sites publication is owner-private. Broader visitor access requires changing its audience.

## Scope

- Five Workday-style multi-step flows; five Greenhouse-style forms; five Lever-style forms; five custom flows.
- Fictional companies and roles, independent of and unaffiliated with those ATS vendors.
- Different layouts, optional field sets, and five custom question types. These are not faithful reproductions of each vendor's entire product.
- Exact profile matching; no inferred answers or vision-model calls from the web UI.
- The Python browser agent runs separately on your machine; this static host does not execute Chromium jobs.
- End-to-end cloud verification, account deletion/export UI, upload orphan cleanup, and abuse monitoring are needed before calling this production-ready.
