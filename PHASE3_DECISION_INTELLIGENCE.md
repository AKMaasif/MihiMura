# MihiMura Phase 3 — Decision Intelligence & Tool Layer (v8.0.0)

This release builds on the working multilingual + RAG v7/v7.1/v7.2 codebase. No Supabase migration is required for Phase 3.

## What changed

### 1. Deterministic Tool Planner
`app/services/tool_planner.py`

Every Decision Support request receives an auditable plan describing which tools are enabled, why they were selected, whether they are required, and the consequence level.

Tools covered:
- farm context
- weather
- climate
- agronomy RAG
- water context
- market intelligence
- economics
- resource/equipment planning
- safety

Only relevant tools are executed.

### 2. Tool Runtime / Failure Handling
`app/services/tool_runtime.py`

Each selected tool now records:
- success / unavailable / error
- latency in milliseconds
- safe error information

A failed tool no longer implies that it was successfully checked.

### 3. Weather Decision Engine
`app/services/weather_decision.py`

Weather is converted into structured operational evidence:
- detected field operation
- target day
- rain probability
- rainfall amount
- current wind / humidity / temperature
- operational risk flags

Examples include fertilizer timing, spray conditions, irrigation, harvest and planting.

The engine is deliberately non-prescriptive: product-label and crop-specific rules remain authoritative.

### 4. Production-safe weather fallback
`app/services/weather.py`

If Open-Meteo fails, demo data is explicitly marked:
- `live=false`
- `status=fallback_demo`
- `decision_usable=false`

The agent is instructed not to present fallback values as current weather or use them for a consequential field recommendation.

### 5. Deterministic Economics Engine improvements
`app/services/economics.py`

Planning scenarios now calculate:
- total cost
- revenue
- profit
- profit margin
- ROI
- cost per kg
- break-even selling price
- break-even yield

The original configurable planning assumptions remain clearly labelled as estimates rather than live quotations.

A second deterministic calculator is available for future verified/user-entered cost, yield and price values.

### 6. Resource / Equipment Planner improvements
`app/services/resource_planning.py`

Resource items now carry:
- stage
- priority
- hire/share/own strategy
- verification notes
- costing guidance

Paddy planning includes machinery, field tools, irrigation, crop-protection equipment, harvesting, post-harvest and PPE considerations.

### 7. Market Intelligence interface hardened
`app/services/market_intelligence.py`

The current local build provides a structured selling-channel registry and quotation checklist, while explicitly stating:
- live price feed is not connected
- live buyer feed is not connected
- current buyer/price claims must be verified

This prevents the model from inventing a current market price.

### 8. Evidence Validator + Confidence Engine
`app/services/evidence_validation.py`

Confidence is no longer trusted as an LLM self-rating in Decision Support.

MihiMura evaluates actual evidence such as:
- resolved location
- crop context
- live weather availability
- RAG agronomy evidence
- market channel/price availability
- economics status
- water context
- treatment-safety evidence

The final confidence displayed in Decision Support is derived from this evidence state. The original model confidence is preserved separately as `model_confidence` for debugging.

Evidence levels:
- high
- moderate
- low
- insufficient

### 9. Better Agent Trace
Decision Support now records:
- Intent Router
- Tool Planner
- selected evidence tools
- tool status and latency
- Evidence Validator
- Confidence Engine
- Safety validation

### 10. Full Report planning snapshot
Full Report mode now exposes the enhanced:
- economics plan
- market plan
- resource/equipment plan
- tool-plan details

The comprehensive report composer remains the existing multilingual report workflow; Phase 4 will make the report engine itself fully planner/parallel-tool driven.

## No new database migration

Phase 3 does **not** add new database tables. Keep all migrations already used for v7/v7.1.

## Local upgrade

Copy your existing working `.env` files into this v8 project:
- `mihimura-backend/.env`
- `mihimura-web/.env`

Do not put secrets in source control.

### Backend

```powershell
cd mihimura-backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health endpoint:

`http://127.0.0.1:8000/api/v1/health`

Expected additions:

```json
{
  "version": "8.0.0",
  "decision_intelligence": "phase3-v1",
  "confidence_engine": "deterministic-evidence-weighting-v1",
  "market_live_price_feed": false
}
```

### Frontend

```powershell
cd mihimura-web
npm.cmd install
npm.cmd run dev
```

The AI Decision Contract now shows the evidence-quality label beside confidence.

## Recommended manual tests

### Weather + fertilizer decision
Ask in Decision Support or Auto:

`Should I apply fertilizer tomorrow in Galle if heavy rain is expected?`

Check Agent Trace for:
- Tool Planner
- Tool · weather
- Tool · agronomy
- Evidence Validator
- Confidence Engine

### Sinhala

`ගාල්ලේ හෙට වැසි වැඩි නම් වී වගාවට පොහොර දාන්න හොඳද?`

### Tamil

`காலியில் நாளை அதிக மழை இருந்தால் நெல் வயலில் உரம் போடலாமா?`

### Market decision

`Where can I sell my paddy and what is the current market price?`

Expected behavior:
- market tool selected
- channel guidance available
- current price is **not invented** because the live price feed is not connected
- evidence confidence reflects that limitation

### Full report

`Give me a complete 1 acre paddy cultivation report for Polonnaruwa including machinery, tools, cost, ROI, break-even and marketing.`

The planning snapshot should contain economics, market and resources.

## Offline regression tests added

- `tests/phase3_tool_planner_test.py`
- `tests/phase3_weather_decision_test.py`
- `tests/phase3_evidence_test.py`
- `tests/phase3_economics_test.py`

Run:

```powershell
$env:PYTHONPATH="."
python tests/phase3_tool_planner_test.py
python tests/phase3_weather_decision_test.py
python tests/phase3_evidence_test.py
python tests/phase3_economics_test.py
```

## Phase 4 next

Phase 4 will turn Full Report into a dedicated multi-step report execution pipeline with parallel tool execution, report progress, stronger market/current-cost connectors, structured report JSON and final multilingual web/PDF rendering.
