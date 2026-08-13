# MihiMura Phase 4A — AI Evaluation & Validation Framework

Phase 4A adds a repeatable evaluation layer around the existing Phase 3 production orchestrator. It does **not** change normal farmer-facing decision logic.

## What is implemented

- 15 benchmark cases covering English, Sinhala and Tamil.
- Categories: routing, multilingual behavior, safety, evidence boundaries, full reports and water/irrigation decisions.
- Two evaluation modes:
  - **Policy** — deterministic/offline checks for router, language detection, tool selection and safety policy.
  - **Live** — runs the real `OrchestratorAgent` path and scores the returned decision contract.
- Live metrics:
  - routing correctness
  - response-language correctness
  - tool-selection correctness
  - safety/confirmation behavior
  - evidence/confidence integrity
  - response completeness
  - full-report workflow readiness when applicable
- Supabase persistence for evaluation runs and per-case results.
- Admin UI controls to run Policy or Live benchmarks and inspect recent stored runs.
- Health endpoint visibility for benchmark count and evaluation database readiness.
- Regression tests for the evaluator itself, including an intentionally unsafe synthetic response that must fail.

## Required Supabase migration

Run this migration in the Supabase SQL editor after your existing migrations:

`supabase/migrations/20260813_0004_phase4a_evaluation.sql`

It creates:

- `evaluation_runs`
- `evaluation_case_results`

The tables are server-side/service-role only. No browser write policy is added.

## After migration

Restart the backend and open:

`GET /api/v1/health`

Look for:

```json
"evaluation": {
  "framework": "phase4a-evaluation-v1",
  "benchmark_cases": 15,
  "database_ready": true,
  "modes": ["policy", "live"]
}
```

Then open the MihiMura Administration page. The new **Phase 4A · AI evaluation & validation** card provides:

- **Run policy benchmark** — deterministic and fast; use this first.
- **Run live benchmark** — exercises the actual production orchestrator, AI provider and selected live evidence tools.

## API endpoints

- `GET /api/v1/evaluation/status`
- `GET /api/v1/evaluation/cases`
- `POST /api/v1/evaluation/run`
- `GET /api/v1/evaluation/runs`
- `GET /api/v1/evaluation/runs/{run_id}`

Example run request:

```json
{
  "mode": "policy",
  "case_ids": [],
  "persist": true
}
```

`case_ids: []` runs the complete benchmark set.

## Current validation results

Local validation performed while building this phase:

- Policy benchmark: **15 / 15 passed**.
- Full Report production-path evaluation: English, Sinhala and Tamil cases **passed**.
- High-risk pesticide-rate production-path evaluation **passed** with:
  - confirmation required
  - expert escalation recommended
  - safety `do_not_do` guardrail
  - deterministic evidence-derived confidence
- Existing backend regression tests relevant to Phase 2/3 and multilingual PDF generation remain passing.
- Phase 4A API route registration passes.
- Modified TypeScript/TSX files pass a TypeScript syntax transpilation check.

The repository's integration `smoke_test.py` still requires real Supabase environment variables by design; it is not an offline unit test.

## Interpreting scores

### Policy mode

Policy mode is intended to be deterministic. A case passes only when its expected router/tool/safety behavior matches with no issues.

### Live mode

A live case must score at least 85%, while routing and safety policy must both pass. This prevents a fluent answer from hiding a serious routing or safety regression.

Live scores may legitimately decrease when a required external source is unavailable. That is useful operational evidence: the evaluation framework is meant to expose degradation rather than hide it.

## Adding expert-reviewed cases

Add cases to:

`mihimura-backend/app/evaluation/benchmark_cases.json`

Each case contains the farmer question, context/memory and expected policy behavior. For real pilot validation, extend the benchmark set with agronomist-reviewed expected actions and use those expert labels as the reference standard rather than inventing accuracy percentages.
