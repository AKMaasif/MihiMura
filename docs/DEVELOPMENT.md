# Develop and verify MihiMura

## Run locally

Use Python 3.11, Node.js 22 or later, and Noto Sans Sinhala and Tamil fonts for multilingual PDFs. From the repository root:

```bash
cd mihimura-backend
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp -n .env.example .env
.venv/bin/python -m uvicorn app.main:app --port 8000
```

In another shell:

```bash
cd mihimura-web
npm ci
cp -n .env.example .env
npm run dev
```

Vite proxies `/api` to port 8000. For a production deployment, route `/api/v1` to FastAPI at the site's reverse proxy or set the public `VITE_API_URL` at build time to the HTTPS API base. Include the exact frontend origins in backend `ALLOWED_ORIGINS`. The bundled static nginx configuration needs a proxy rule or the build-time absolute API base.

## Configure xAI and Meta

Enter server-side values using the environment's secret settings or the ignored backend `.env`. Use the exact chat model IDs enabled in the corresponding account. An xAI API key and a Meta Llama API key are required for their respective endpoints. A Meta Graph, Instagram, or WhatsApp token is a separate credential.

| Backend setting | Value |
| --- | --- |
| `XAI_API_KEY`, `XAI_MODEL` | xAI key and chat model ID from the xAI console |
| `META_API_KEY`, `META_MODEL` | Meta Llama API key and chat model ID from the Meta console |
| `XAI_VISION_MODEL`, `META_VISION_MODEL` | Optional image-capable model IDs. Configure only for accounts allowed to process uploaded images. |
| `GEMINI_API_KEY` | Optional. Enables legacy Gemini generation fallback, Gemini vector ingestion and server speech. |

Allow HTTPS egress to `api.x.ai` and `api.llama.com`. Structured text requests try xAI, then Meta, then Gemini when configured. Failures can trigger deterministic workflow fallbacks. The answer trace records the provider and model that returned a valid response. Provider names in `/api/v1/health` represent configuration. A real authenticated test turn establishes API access.

Content sent to a provider can include the question, selected farm context, retrieved excerpts, recent conversation, and any submitted crop images. Use approved accounts and test data when verifying provider setup.

Without Gemini, browser speech recognition transcribes the question, FastAPI runs the shared text workflow, and browser speech can read its answer. Availability of Sinhala and Tamil voices depends on the browser and system. Knowledge search can use keyword matches from existing published, geographically unrestricted chunks for the selected crop. These matches are weak evidence. Uploading and embedding new documents still requires an embedding service. Keep existing vectors with their original embedding model and reindex separately if the model changes.

## Supabase and Google OAuth

Configure the backend with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. Configure Vite with the same project URL in `VITE_SUPABASE_URL` and its browser-safe key in `VITE_SUPABASE_PUBLISHABLE_KEY`. Keep the service-role and provider keys on the backend. Use a project with the MihiMura application tables, storage buckets and knowledge RPC already provisioned. This repository has no complete database bootstrap schema.

1. In Google Cloud, create a **Web application** OAuth client. Register the callback `https://<project-ref>.supabase.co/auth/v1/callback` as an authorized redirect URI. Use the exact callback displayed by Supabase when using a custom domain. Configure the consent screen and add test users if Google keeps the app in testing.
2. In Supabase **Authentication → Providers → Google**, enable Google and enter the OAuth client ID and secret.
3. In Supabase **Authentication → URL Configuration**, set the Site URL to the deployed frontend origin. Add `http://localhost:5173/?flow=oauth#/auth` for local sign-in and the same path and query on the deployed origin. Add the exact `/?flow=signup#/auth` and `/?flow=recovery#/auth?mode=recovery` URLs on each permitted origin if those flows are enabled. Add the loopback-IP versions only when developing on that separate origin. Test from the same origin that starts sign-in because PKCE stores the verifier in that origin's browser storage.
4. Use a new test user to sign in, finish onboarding, refresh the tab and sign out. Also cancel at Google, try a disallowed redirect on a disposable test deployment, and simulate an unavailable profile API. A successful Google callback and a successful FastAPI profile load are separate checks.

Use `DEMO_MODE=true` and `VITE_DEMO_AUTH=true` together only on an isolated demo deployment with disposable Supabase data. The shared demo identity still needs Supabase and can modify its own records. Leave both false in production.

## Verification and demo

Run the commands in `.github/workflows/ci.yml` for the offline suite, lint and build. Run `cd mihimura-backend && .venv/bin/python tests/smoke_test.py` only against a disposable, configured Supabase project. It exercises live persistence. Check provider calls through authenticated test turns and voice from a microphone-enabled browser.

| User action | Expected result and verification |
| --- | --- |
| Enter demo on the isolated project or sign in with a test Google account | Verify the authenticated profile request and onboarding or dashboard route. |
| Create or select a farm and project | Confirm the project crop, stage and location in the assistant context and trace. Use disposable records. |
| Ask a general question in English, Sinhala and Tamil | Check the selected response language, conversation history, bounded route and returned provider. |
| Ask whether to irrigate today | Check selected location, weather freshness and evidence validation in the Decision Support trace. Missing live data should leave uncertainty visible. |
| Ask for approved paddy guidance | Inspect the source title, excerpt and page. Repeat with an unrelated phrase and verify that it does not produce an invented citation. |
| Submit a test crop photo | Check the configured vision model in the response and verify that uncertain results request further evidence or expert review. Requires an image-capable model. |
| Start voice and ask the same question | Verify the authenticated `/ask-ai` request and resulting transcript. Deny microphone access, then send the question by typing. |
| Request a full report | Confirm the selected language, sections, evidence and PDF download. Requires Supabase Storage and a configured text model for native-language reports. |
| Disable a provider on a disposable deployment or stop FastAPI locally | Verify that the trace attributes the fallback correctly, or that the frontend displays a useful connection error and retry. |

Rollback code changes by reverting the relevant commits. This work does not migrate Supabase data or re-embed the corpus. Remaining deployment checks include validating the hosted knowledge schema and ingestion, confirming browser speech quality across languages, and testing the authenticated flows on representative physical devices.
