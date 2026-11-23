# Demo walkthrough

Local demo data is labeled. It is not a substitute for live weather, a retrieved document, or a vision result.

## Run it

```bash
# API
cd mihimura-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill Supabase and, if you have it, GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000

# Web
cd mihimura-web
npm ci
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`. For the admin screens in a local demo, keep `DEMO_PRIVILEGED=true`. For a public server, set `DEMO_MODE=false`.

Offline checks, with no secrets:

```bash
cd mihimura-backend
python -m compileall -q app
for t in tests/*_test.py; do
  [ "$t" = tests/smoke_test.py ] && continue
  python "$t"
done
cd ../mihimura-web
npm test && npm run lint && npm run build
```

## Steps

1. **Sign in or demo mode.** Action: choose “Continue with Google”, or the demo farmer if `VITE_DEMO_AUTH` is not `false`. Expected: Google returns to the site origin, then the app opens the dashboard or onboarding. A cancelled Google login stays on the auth screen with a cancellation message. A profile API failure shows retry, not a spinner. Verify: backend log for `GET /api/v1/users/me` returns 200, or a visible error if it does not. Google itself needs the console settings in `docs/OPERATOR_SETUP.md`.

2. **Farm context.** Action: open Farms, create or select a project, and confirm crop, stage, and district. Expected: later questions use that project. If latitude and longitude were never saved, local weather and voice do not assume Ampara. Verify: the project payload from `GET /api/v1/projects` contains the crop and district you entered.

3. **Simple agriculture question.** Action: in MihiMura AI, ask “explain why paddy fields are levelled” in English, Sinhala, or Tamil. Expected: Simple Chat. The trace lists Intent Router and, when the index is down, a watch step that only official source links were available. Verify: the “How this answer was made” panel and `workflow_trace.route` equal `simple_chat`.

4. **Time-sensitive question.** Action: ask “can I apply fertilizer tomorrow?” with a saved location. Expected: Decision Support. If Open-Meteo is reachable, the trace includes Micro-Climate Prediction as live and Evidence Validator records whether a current decision is allowed. If the forecast fails, the answer must not quote the demo 82% rain figure. Verify: `workflow_trace.intent` is `input_safety_decision` or `weather_decision`, and `evidence_quality.can_make_current_decision` matches whether weather was live.

5. **Knowledge search.** Action: ask for the indexed rice guidance and the document name, or use Knowledge search in the admin tools when `DEMO_PRIVILEGED=true`. Expected: citations are retrieved chunk labels, or the reply says the index did not return text and only lists registry pointers. An empty or failed search does not invent a bulletin title. Verify: each source `freshness` says “indexed evidence” or “source text not retrieved”.

6. **Crop image.** Action: on Scan, submit a photo if Gemini is configured. Expected: the result is a differential with a disclaimer. If the model is missing or errors, `expert_review` is true, confidence stays at or below 0.55, and the text says no diagnosis was completed. Verify: the JSON `provider` is `gemini` only when a model actually answered; otherwise `demo` or `demo-fallback`.

7. **Voice, then text.** Action: in a Chromium browser, start Voice conversation and ask a short farm question. Expected: the transcript is sent to `/ask-ai`, and speech is that answer. The panel says it speaks only after the verified advisor finishes. In Firefox or without a microphone, the control explains that voice is unavailable and the text box remains. If TTS fails, the same written answer stays on screen. Verify: network shows `POST /api/v1/ask-ai` before `POST /api/v1/voice/tts`. The Live token endpoint is not part of this path. It returns `grounded: false`.

8. **Report.** Action: ask for a complete cultivation report and supply crop, location, and area when asked. Expected: the report is in the language of the conversation, lists assumptions, and offers a download only after `report_ready`. Verify: `workflow_trace.route` is `full_report`, and the PDF request is `POST /api/v1/conversations/{id}/reports`. Sinhala and Tamil PDFs need the Noto fonts installed, as CI does.

9. **Provider failure.** Action: stop the API, or remove `GEMINI_API_KEY`, and ask again. Expected: the screen shows the API or provider error, or a deterministic answer that says the model was not used. The national overview shows “unavailable” and a retry, not mock province scores. Verify: `workflow_trace.provider` contains `fallback` or `deterministic` when Gemini did not answer, and the overview response has `_connection: "offline"` when the API is down.

## Phone check

At about 360px width, open Welcome, Auth, Dashboard, AI, and Farms. Navigation text should be at least 14px, the menu should close from the dimmed backdrop, and Sinhala or Tamil in the AI thread should use Noto. There is no separate browser automation in CI; confirm this in a browser before a release.
