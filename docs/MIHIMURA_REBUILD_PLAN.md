# MihiMura reliability plan

## Baseline

The cloud checkout at fdf2494 was clean. Python compilation, all 19 offline regression scripts, frontend lint, and the TypeScript/Vite build passed. Lint and Vite reported existing warnings. The earlier onboarding smoke check verified the Vite proxy and API health. The repository contains no Supabase schema migrations, so deployed constraints and RPCs still need verification against a test project.

React uses Supabase PKCE for identity and a shared FastAPI client for application calls. FastAPI validates identity, loads profiles and farm data from Supabase, and routes AI turns through context, tools, specialist generation, evidence validation, and persistence. Browser voice already sends transcribed questions through that same route. Knowledge retrieval uses a Supabase hybrid-vector RPC, and ingestion records jobs and stores chunks with Gemini vectors.

| Finding | Impact | First change |
| --- | --- | --- |
| Demo mode accepts requests without an explicit demo session and allows shared knowledge and evaluation administration | High | Require an explicit demo session and enforce administrator/editor permissions |
| Structured generation, localization, health and provider labels assume Gemini | High | Add xAI and Meta behind the existing structured generation boundary and preserve schema validation |
| Google PKCE bootstrap can load profiles twice and overwrite newer session state | Medium | Use the initial auth event and guard profile updates against stale requests |
| Frontend assumes the user's computer can reach port 8000 and lacks a request deadline | Medium | Default to a same-origin API, provide typed failures and use an abortable deadline |
| Voice attempts Gemini TTS even when it is unconfigured | Medium | Use browser speech when no server voice is configured and keep the grounded transcript |
| Vector retrieval needs an embedding key and a deployed matching index | High | Add a clearly labeled weak-evidence keyword path for existing published chunks and preserve the current index |

## Implementation order

1. Add bounded xAI and Meta requests for structured text. Use xAI first, Meta second, and optional Gemini as the existing fallback. Configure image-capable models explicitly. Preserve context, evidence checks, and deterministic failover.
2. Harden demo access and Google session restoration. Keep Supabase console changes and hosted authentication verification separate.
3. Route voice through the existing authenticated agent and use browser speech for playback without Gemini. Surface API and provider failures. Preserve session cleanup and the text transcript.
4. Validate offline, smoke-test both dev servers, and document live checks and the demo walkthrough. Keep existing Git history and commit each coherent change.

## Verification and rollback

| Check | Expected outcome |
| --- | --- |
| Mocked xAI and Meta responses | Valid schema, traceable provider, bounded fallback, no key in errors |
| Crop image request | Only an explicitly configured vision model receives the image |
| Missing or failed embeddings | Approved keyword excerpts stay weak evidence. No generated citations or vector migration |
| No session, explicit demo, valid authenticated session | Unauthorized requests fail, demo stays scoped, valid users load their profile |
| Google OAuth on a configured test project | Sign-in, cancellation, refresh, onboarding and logout work without loops |
| Browser STT and playback | Voice uses the same assistant response and maintains a readable transcript |
| Mobile and multilingual view | Labels wrap, controls remain reachable, and text remains visible |
| Regression suite and frontend build | Existing offline scripts and production build pass |

Use test data for live integration. Any replacement embedding model requires a matching schema and a deliberate reindex of the corpus. No database migration is needed for the first changes. Roll back with Git revert, and preserve existing provider settings and indexed data.
