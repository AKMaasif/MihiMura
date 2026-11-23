# Operator setup

These values are not stored in the repo. Nothing in this change created a Supabase project, a Google client, or a Gemini key.

## Backend `mihimura-backend/.env`

Copy `.env.example`.

- `DEMO_MODE=true` only on a machine you control. Any request without a bearer token then uses the single demo farmer.
- `DEMO_PRIVILEGED=true` only for that same local demo. It lets the demo farmer open admin, evaluation, and knowledge-editor routes. Leave it false on a shared server.
- `ALLOWED_ORIGINS` must include the exact web origin, for example `http://localhost:5173`.
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` stay on the server. Do not put the service-role key in Vite.
- `GEMINI_API_KEY` stays on the server. Voice TTS and embeddings use it there.
- Sentinel Hub keys are optional. Without them the satellite route says it is not configured.

## Web `mihimura-web/.env`

- `VITE_API_URL` is the backend, usually `http://127.0.0.1:8000/api/v1`.
- `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` are the browser-safe Supabase values.
- `VITE_DEMO_AUTH=false` hides the demo button. It does not turn off `DEMO_MODE` on the API.
- `VITE_GUIDED_AUTH_ENABLED=true` shows email and phone forms. They stay hidden until you set that.

## Supabase Auth

Authentication → URL configuration:

- Site URL: `http://localhost:5173` for local work, plus the production origin when you have one.
- Redirect URLs, each as its own entry:
  - `http://localhost:5173`
  - `http://localhost:5173/`
  - `http://127.0.0.1:5173`
  - `http://127.0.0.1:5173/`
  - the production origin and the production origin with a trailing slash

The app sends Google, email confirmation, and password recovery back to `{origin}/`. The hash router then continues. Do not add `#/auth` to the allow list; Supabase does not treat the fragment as part of the redirect.

Google provider in Supabase: enable Google and paste the client id and secret from Google Cloud. This repository does not contain those.

## Google Cloud OAuth client

Authorized JavaScript origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- the production origin

Authorized redirect URI (this is Supabase, not the Vite app):

- `https://<project-ref>.supabase.co/auth/v1/callback`

If Google shows “redirect_uri_mismatch”, the URI above is the one that must match.

## What the app does when this is missing

- No Supabase browser keys: Google stays disabled and the button says setup is required.
- Google cancelled: the auth screen says the sign-in was cancelled.
- Valid Google session but the API profile call fails: the app stays on an error screen with retry and sign-out. It does not loop through onboarding.
- No Gemini key: chat and decisions use the deterministic fallback, and voice playback says the cloud voice is unavailable. The written answer remains.
- No live weather: decisions do not use the demo rain series.

## Smoke test

From `mihimura-backend`, with `.env` filled in:

```bash
python tests/smoke_test.py
```

CI does not run this file.
