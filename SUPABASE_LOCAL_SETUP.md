# MihiMura v4 — Local Supabase Setup

This version uses **Supabase Auth + PostgreSQL + Storage** and removes the previous split identity/local-database architecture. React and FastAPI still run locally during development; the Supabase development project provides identity, durable data and private report storage.

## 1. Create a development Supabase project

Create a new Supabase project specifically for local MihiMura development. Do not reuse production data while validating the migration.

From Supabase Project Settings / API, copy:

- Project URL
- Publishable key (or legacy anon key if that is what the dashboard exposes)
- Backend secret/service-role key

The publishable key may be used in the browser. The secret/service-role key must remain backend-only.

## 2. Create the MihiMura schema

Open **Supabase Dashboard → SQL Editor** and run the complete file:

```text
supabase/migrations/20260812_0001_mihimura_supabase.sql
```

It creates:

- profiles
- farms / projects / tasks / observations / expenses / harvests
- orders / expert cases / notifications / community reports
- conversations / messages / conversation memory
- agent runs / tool calls / audit events
- reports / attachments
- private report and attachment Storage buckets
- ownership RLS policies
- a fixed local demo profile and demo farm/project/task data

After the query succeeds, check **Table Editor** and confirm the tables exist.

## 3. Configure Supabase Auth

In **Authentication → Providers**:

1. Keep Email enabled for the first local test.
2. Google is optional. Configure Google provider credentials only if you want to test social sign-in now.
3. Phone OTP is optional and also requires a supported SMS provider.

In **Authentication → URL Configuration** for local testing, use:

```text
Site URL: http://localhost:5173/
Redirect URL: http://localhost:5173/**
```

The frontend uses Supabase PKCE with `detectSessionInUrl` and hash-router-safe redirect URLs. Still test email confirmation, Google OAuth and password recovery end-to-end before deployment.

## 4. Backend environment

From:

```text
mihimura-backend
```

create `.env` from `.env.example`:

```powershell
copy .env.example .env
```

Fill at minimum:

```env
DEMO_MODE=true
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_BACKEND_SECRET_KEY
SUPABASE_REPORTS_BUCKET=mihimura-reports
SUPABASE_ATTACHMENTS_BUCKET=mihimura-attachments
```

Then add your Gemini key if you want live AI responses. Without it, the orchestrator/report paths retain deterministic safety fallbacks where implemented.

Never commit `.env`.

## 5. Frontend environment

From:

```text
mihimura-web
```

create `.env`:

```powershell
copy .env.example .env
```

Fill:

```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_VITE_DEMO_AUTH=true
```

Do not put the Supabase service-role/secret key in this file.

## 6. Start the backend

```powershell
cd mihimura-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Check:

```text
http://127.0.0.1:8000/api/v1/health
```

Expected key fields:

```json
{
  "status": "ok",
  "version": "7.0.0",
  "supabase_configured": true,
  "auth_provider": "supabase",
  "database": "supabase-postgres"
}
```

## 7. Start the frontend

In a second PowerShell window:

```powershell
cd mihimura-web
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://localhost:5173
```

## 8. Test registration and onboarding

Use a new email address and verify this sequence:

1. Register.
2. If email confirmation is enabled in Supabase, confirm the email and return to login.
3. Sign in.
4. Complete onboarding.
5. Open the dashboard.
6. Sign out.
7. Sign in again.
8. Confirm onboarding does **not** repeat.

Then verify in Supabase:

```text
Authentication → Users
```

and:

```text
Table Editor → profiles
```

The `profiles.id` value for the real user should match the Supabase Auth user UUID.

## 9. Bootstrap your first administrator

Do not add a separate hard-coded admin password.

1. Register your normal Supabase account through MihiMura.
2. In **Table Editor → profiles**, locate your UUID.
3. Set:

```text
role = admin
professional_verified = true
status = active
```

4. Sign out and sign in again.
5. Open `/app/admin`.

Admin operations still go through FastAPI. The browser never receives the backend secret key.

## 10. Test the stateful AI regression scenario

Start **New chat** in MihiMura AI and type:

```text
i want to plant padddy in polannaruwa areaa. can you make full report about this. initial land about 1 accr and i need whole report
```

Expected working memory:

```text
Crop: Paddy
Location: Polonnaruwa
Area: 1 acre
Intent: cultivation report
```

The assistant should request only material missing information such as season and water source.

Next type:

```text
now list what are the details you need
```

It must remain in the **same Polonnaruwa / Paddy / 1-acre conversation** and show the clarification UI rather than switching to the profile district.

After completing the required fields, ask a side question such as:

```text
what is the weather risk for this plan?
```

The side question should be answered using the active planning scenario without erasing the unfinished report workflow.

## 11. Test PDF report generation

When the required planning facts are complete, MihiMura should expose **Generate full PDF report**.

Verify:

1. The report opens from the chat.
2. It appears under **Reports & Impact → AI cultivation reports**.
3. A row appears in `public.reports`.
4. The PDF object appears in the private `mihimura-reports` Storage bucket under the user's UUID folder.

The current PDF renderer is reliable for English text. Sinhala/Tamil conversational chat is supported, but full Sinhala/Tamil PDF typography should be validated with an appropriate Unicode font before claiming multilingual PDF parity.

## 12. Test admin controls

As the bootstrapped admin:

- view profiles
- verify/revoke professional status
- suspend a test account
- confirm the suspended account is rejected at the MihiMura API boundary
- restore the account
- inspect agent-run and audit records

For now, suspension is an application authorization status. It is intentionally not a browser-side role toggle.

## 13. Local validation commands

Backend:

```powershell
cd mihimura-backend
python -m compileall -q app
python tests/context_memory_test.py
```

After Supabase is configured:

```powershell
python tests/smoke_test.py
```

Frontend:

```powershell
cd mihimura-web
npm.cmd install
npm.cmd run build
```

## 14. Do not deploy yet

Complete the local regression tests first. Deployment variables for Vercel/Render should be changed only after login, onboarding, admin access, persistent AI conversations and PDF reports all work locally.


## v7 Phase 2 knowledge migration

After the base migration, run `supabase/migrations/20260812_0002_mihimura_rag.sql`. Then follow `PHASE2_RAG_SETUP.md` to ingest trusted agricultural documents.
