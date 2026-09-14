# SRS Records — OMR CRM Connector

Student data entry with owner-managed phone/password accounts. Interns enter student name, school, father’s number, mother’s number, and class. The owner reviews all submissions and downloads filtered CSV files.

## Render deployment

Connect this repository as a Render **Web Service**, branch `main`, runtime **Node**. Leave Root Directory blank.

- Build: `npm ci && npm run build`
- Start: `npm start`
- Health check: `/api/health`
- `NODE_VERSION`: `22.16.0`
- `DATABASE_URL`: your full Supabase PostgreSQL connection URL; percent-encode special characters in its password.
- `OWNER_SETUP_KEY`: a private random value of at least 24 characters (e.g. generate with `openssl rand -hex 32`).

Alternatively create a Render Blueprint from `render.yaml`; it generates the setup key automatically. Copy its value privately from the Render environment settings when completing setup.

After deployment, open `/owner-setup`, enter the setup key, and choose the owner password. The owner number is **9665821832**. Setup closes after the owner exists. Normal login does not use ChatGPT. The owner can create, disable, enable, and reset intern accounts. Resetting a password invalidates existing sessions.

For a custom domain, set `APP_URL` to its canonical HTTPS origin (no path). Otherwise the app uses Render’s `RENDER_EXTERNAL_URL`. Keep one canonical URL for login and form submission.

## Database

The app uses Supabase PostgreSQL through `pg` with TLS certificate verification and the bundled Supabase CA. The server initializes the `srs_records` schema transactionally before listening; initialization is idempotent and protected by an advisory lock. It does not delete existing rows. Tables are in a private schema, not Supabase’s public Data API schema.

The old Cloudflare D1 data is not automatically migrated. Existing Sites records remain in the old deployment. Request a separate migration if needed. Render starts with the PostgreSQL records in `srs_records`.

## Local development

Use Node 22. Copy `.env.example` to `.env.local`, set `DATABASE_URL` and a private `OWNER_SETUP_KEY`, then run:

```
npm ci
npm run db:migrate
npm run dev
```

For local form requests set `APP_URL` to the exact origin used in the browser, e.g. `http://localhost:3000`.

## Validation

The production Next.js build passes TypeScript checks. Integration checks against an isolated PostgreSQL schema cover owner setup restrictions, phone login, wrong passwords, role enforcement, password resets, session revocation, logout, record submission/review, and filtered CSV exports.

Secrets and local test state are excluded from Git. Legacy Sites/Vinext files remain for source history but are not used by the Render build or server.
