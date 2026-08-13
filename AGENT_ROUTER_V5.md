# MihiMura v5 — Intent-Routed Production-Oriented Agent Layer

This local build replaces the previous one-size-fits-all `/ask-ai` behavior with three explicit workflows plus an **Auto** router.

## User-facing modes

- **Auto (recommended):** MihiMura detects the request type and runs the appropriate workflow without interrupting the farmer.
- **Simple Chat:** explanations, normal conversation, navigation and general agriculture questions. It deliberately avoids pretending that live farm/weather/market tools were checked.
- **Decision Support:** current or consequential farm decisions such as weather-sensitive irrigation/fertilizer actions, crop-risk questions and other operational decisions. This route is allowed to use live evidence and the safety layer.
- **Full Report:** comprehensive cultivation + farm-business planning with agronomy, equipment/tools, resources, economics, harvest/post-harvest and marketing sections.

## Wrong-mode guidance

When the user manually selects a mode and asks a high-confidence question that belongs in another workflow, the router pauses before running the wrong tools and returns a `mode_switch` response.

Example:

```text
Selected mode: Simple Chat
User: Will rain tomorrow affect fertilizer application?

MihiMura:
Better workflow detected → Decision Support
[Switch & continue] [Stay in Simple Chat]
```

Auto mode does not show this interruption; it routes internally.

## Clarification policy

Full reports are blocked only when MihiMura is missing a fact that defines the basic scenario:

1. crop
2. cultivation location
3. land area

Season, irrigation, variety and planting date are useful refinements but no longer force a popup. If unknown, the report labels them as assumptions/scenarios and lets the farmer refine them later.

## Full Report pipeline

```text
Conversation memory
  → report planner
  → resource/equipment planner
  → agronomy knowledge registry
  → weather/climate context where location coordinates are available
  → deterministic economics engine
  → market-channel planner
  → chemical/rate safety gates
  → structured report composer
  → PDF renderer
  → private Supabase Storage
```

The fallback PDF remains usable if the LLM returns malformed output or is temporarily unavailable.

## Financial-data status

`app/knowledge/planning_assumptions.json` currently contains **illustrative local planning ranges** for the paddy demo. They are intentionally labelled as estimates and are not current market quotations. A production deployment should replace/refresh them using current farmer-entered quotations or a verified price/data connector.

The economics engine calculates:

- low/base/high cultivation cost
- conservative/planning-base/favourable yield and selling-price scenarios
- revenue
- estimated profit
- break-even selling price
- break-even yield

The LLM explains those calculations but does not perform the arithmetic itself.

## Chemicals and fertilizer

The report can define the required input categories and crop-protection decision process, but exact fertilizer/pesticide product/rate/interval claims remain verification-gated. MihiMura must not fabricate those values. Production deployment should connect current approved Department of Agriculture / label knowledge through the RAG layer.

## Market intelligence

The local v5 build provides selling-channel categories and a quotation-comparison strategy. Specific buyer availability, procurement programmes and prices are time-sensitive and are deliberately marked for current verification. The next production connector should provide verified live/current market and buyer data.

## Regression tests

From `mihimura-backend`:

```powershell
python tests/context_memory_test.py
python tests/router_test.py
python tests/economics_test.py
python tests/report_workflow_test.py
python tests/pdf_fallback_test.py
```

`tests/smoke_test.py` is the configured Supabase integration test and requires working Supabase environment variables plus the demo seed.

## Recommended local UX test

1. Select **Simple Chat**.
2. Ask: `Will heavy rain affect fertilizer application tomorrow?`
3. Confirm that MihiMura suggests **Decision Support** without losing the conversation.
4. Select **Simple Chat** again and ask: `Prepare a complete 1 acre paddy report for Polonnaruwa with cost, profit and marketing.`
5. Confirm that MihiMura suggests **Full Report**.
6. Use **Auto** and repeat the report request. It should route automatically and generate the report once crop/location/area are known.
7. Ask `What other details do you need?` in the same report conversation. It should list optional refinements rather than showing an unnecessary mandatory form or regenerating the PDF.
