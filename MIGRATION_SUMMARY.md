# MihiMura v4 Migration Summary

## Platform

- Identity: Supabase Auth
- Application database: Supabase PostgreSQL
- Private generated files: Supabase Storage
- Trusted API / agent boundary: FastAPI
- Frontend: React + Vite
- AI provider: Gemini through the backend, with deterministic safety fallbacks where defined

## Authentication

- Email/password
- Google OAuth support
- Optional phone OTP
- Password recovery
- Persistent session handling
- Backend bearer-token validation
- Persistent profile/onboarding state
- Admin role and professional verification in the application profile

## Stateful MihiMura AI

- Persistent conversations and messages
- Structured working memory
- Current-message > conversation > project > profile context precedence
- Typo-tolerant extraction for the demonstrated `padddy / polannaruwa / 1 accr` scenario
- Dynamic clarification forms
- Side questions do not erase an active cultivation-report workflow
- Same conversation ID for text and voice
- Auditable Decision Contract and high-level Agent Trace
- Private PDF cultivation reports

## UI

- Larger MihiMura AI title/subtitle
- Larger chat messages
- Larger typing box and placeholder
- Larger Decision Contract evidence/limitations text
- Larger Agent Trace text
- Conversation sidebar and report cards

## Deliberately retained safety boundaries

- No automatic consequential farm action without confirmation
- No fabricated fertilizer/pesticide rates
- No fabricated prices or guaranteed yield in generated reports
- Evidence and uncertainty remain visible
- Expert escalation remains available
- Admin/service credentials remain backend-only

## v5 Agent-router upgrade

The local v5 branch adds Auto / Simple Chat / Decision Support / Full Report workflows, high-confidence wrong-mode guidance, minimal blocking clarification, a deterministic economics engine, resource/equipment planning, market-channel planning, comprehensive PDF composition, and report follow-up handling that reuses conversation memory instead of regenerating a PDF for every short follow-up. See `AGENT_ROUTER_V5.md`.


## v6 Multilingual agent + Unicode reports

The v6 local build adds end-to-end English/Sinhala/Tamil language detection and response routing for MihiMura AI. Auto language mode detects each new message, updates the chat language without rewriting the user's stored profile preference, and sends the resolved language to FastAPI. The intent router, district/crop/area extraction, decision-tool planner, safety precheck, clarification UI, deterministic fallbacks, report-ready responses and PDF generation now handle Sinhala and Tamil alongside English.

Full reports are composed in the active conversation language. Sinhala/Tamil PDFs use a Unicode TrueType font and ReportLab shaping; the Docker image installs Noto fonts and Windows development falls back to Nirmala UI. The report pipeline validates target-language output and will not silently substitute an English PDF when a Sinhala/Tamil report was requested.


## v7 Hybrid agricultural RAG

Phase 2 adds Supabase pgvector + PostgreSQL full-text search, authority-ranked agricultural knowledge documents/chunks, Gemini multilingual retrieval embeddings, admin/verified-expert ingestion APIs, an admin upload panel, hybrid RAG grounding in Simple Chat agriculture explanations, Decision Support and Full Reports, evidence-quality metadata, and safe fallback to the previous approved-source registry when indexed evidence is unavailable.
