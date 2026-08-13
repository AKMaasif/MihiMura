# MihiMura v7 — Hybrid Agricultural RAG

This build implements Phase 2 of the production AI upgrade.

Core flow:

```text
English / Sinhala / Tamil question
        ↓
Intent router + conversation memory
        ↓
Gemini multilingual query embedding
        ↓
Supabase PostgreSQL
  ├─ pgvector semantic search
  └─ PostgreSQL FTS keyword search
        ↓
Reciprocal-rank fusion + authority weighting
        ↓
Curated excerpts + page/source metadata
        ↓
Simple Chat / Decision Support / Full Report
        ↓
Safety validation + visible sources
```

See `PHASE2_RAG_SETUP.md` for the exact local setup and ingestion steps.
