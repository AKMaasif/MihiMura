# MihiMura rebuild plan

Audit date: 23 November 2026. Baseline on `main` before these changes: all offline backend tests passed, `npm run lint` passed with existing warnings, and `npm run build` passed. `tests/smoke_test.py` was not run because it needs a live Supabase project.

## Current architecture

- Web app: React 19, TypeScript, Vite, HashRouter (`mihimura-web`).
- API: FastAPI (`mihimura-backend`), prefix `/api/v1`.
- Identity and data: Supabase Auth plus a service-role client. The browser only receives the publishable key.
- Advisor: one orchestrator per turn. It routes to Simple Chat, Decision Support, or Full Report. Decision Support runs a fixed specialist list, then a safety and evidence check.
- Voice in the app: browser speech recognition, then `POST /ask-ai`, then Gemini TTS of that answer. A Gemini Live token endpoint exists and is not used by the button.
- Knowledge: hybrid pgvector + full-text search, with an approved-source registry when the index is empty. Registry rows are pointers, not retrieved text.

## Confirmed defects

| Severity | Evidence | What was wrong |
| --- | --- | --- |
| High | `workflows/decision.py` + `weather.py` `DEMO` rain of 82% | A fertilizer fallback treated demo rain as a forecast. |
| High | `workflows/chat.py`, `workflows/decision.py` | A model-written `sources` list could be shown when retrieval did not return that document. |
| High | `workflows/chat.py` | Simple Chat did not strip unsupported rates. |
| High | `soil_water.py` | Water budget returned `success` and summed demo rainfall. |
| High | `vision.py` | Vision failure returned a confident demo diagnosis with `expert_review: false`. |
| High | `api.ts` `fetchDashboard` | A failed national overview was replaced with mock province scores. |
| High | `CommunityPage.tsx` | A failed community load was replaced with a fake Ampara cluster. |
| High | `LocalSituationPage.tsx`, `SatellitePage.tsx`, `VoiceAgent.tsx` | Missing coordinates fell back to Ampara (`7.291, 81.674`) or invented percentages. |
| Medium | `AuthContext.tsx` redirect `/?flow=oauth#/auth` | Hash and query were mixed, which is a fragile PKCE return on HashRouter. Profile failure left `profile` null and onboarding could spin. |
| Medium | `evidence_validation.py` | An illustrative economics estimate counted as satisfied evidence. |
| Medium | `prompts.py` `voice_system_prompt` | The unused Live prompt told the model to call `consult_mihimura`, which is not implemented. |
| Medium | Shell CSS | Navigation and card text sat at 6–9px, Sinhala/Tamil fell through Inter, and the mobile drawer had no scrim. |
| Low | `platform.py` `_privileged` | Demo mode could open admin tools with no separate switch. |

Items that still need the owner's accounts, not a code change: Supabase redirect URLs, Google OAuth client, Gemini key, Sentinel Hub, and the knowledge SQL functions. See `docs/OPERATOR_SETUP.md`.

## Target flow

1. The browser sends the Supabase access token, or no token in demo mode. It never sends a user id the server trusts.
2. `/ask-ai` loads the conversation, routes once, runs only the tools for that route, and returns `agent_trace` plus `workflow_trace` (route, agents, evidence level, elapsed time, outcome).
3. Citations are built from retrieved chunks or an explicitly labeled registry pointer.
4. If live weather, approved text, or a vision result is missing, the answer says so and does not fill the gap with demo numbers.
5. Voice speaks the `/ask-ai` answer. The Live token response is marked `grounded: false` and its instruction refuses field advice.

## Phases in this change

1. Stop demo weather, demo rain, invented citations, and unsanitized vision placeholders from looking like decisions.
2. Make the API client report timeouts and HTTP errors, and stop the overview, community, local, and satellite screens from inventing data.
3. Straighten Google return handling and profile-load failure.
4. Lift type size, Noto fallbacks, tap targets, and the mobile drawer scrim.
5. Add `tests/reliability_regression_test.py` and frontend unit tests. Keep the live smoke test out of CI.

## Test matrix

| Check | Expected |
| --- | --- |
| Offline `tests/*_test.py` except `smoke_test.py` | Pass without secrets |
| Demo weather + fertilizer question | Does not quote the 82% demo probability |
| Live weather + rain at least 60% | May still advise delaying exposed fertilizer |
| Model `sources` name that was not retrieved | Absent from the response |
| Unsupported `2.5 g per litre` in Simple Chat | Removed, expert escalation set |
| Vision with no model | `expert_review` true and confidence at most 0.55 |
| Romanized `pohora` / `vaanilai` | Decision Support, not a keyword miss |
| `npm test`, `npm run lint`, `npm run build` | Pass |
| `python tests/smoke_test.py` | Only with a configured Supabase project |

## Risks and rollback

- `DEMO_PRIVILEGED` now defaults to false. Copy `.env.example` for a local demo that still opens admin tools. A public server should set `DEMO_MODE=false`.
- No database migration is included. Knowledge status filtering only drops rows that already carry `approval_status` or `document_status` of draft, rejected, revoked, unapproved, or archived.
- Rollback is reverting this branch. It does not delete stored profiles, documents, or conversations.

## Still open

- Supabase and Google console URLs must be set by the owner. This repo cannot verify them.
- Gemini model names in `.env.example` are preferences. If a name is unavailable for the key, the backend already tries the next model.
- Economics figures remain planning assumptions until a verified price source exists. They no longer count as confirmed evidence.
