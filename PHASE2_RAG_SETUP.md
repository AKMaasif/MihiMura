# MihiMura v7 — Phase 2 RAG setup

This phase adds a curated agricultural knowledge layer using **Supabase PostgreSQL + pgvector + PostgreSQL full-text search**. It does not fine-tune the LLM.

## 1. Run the new Supabase migration

Open your Supabase project → **SQL Editor** and run:

```text
supabase/migrations/20260812_0002_mihimura_rag.sql
```

Run the existing v4/v6 base migration first if this is a brand-new database.

The migration creates:

- `knowledge_documents`
- `knowledge_chunks`
- `vector(768)` embeddings
- GIN full-text index
- HNSW cosine vector index
- `search_knowledge_hybrid(...)` RPC
- private `mihimura-knowledge` Storage bucket

## 2. Backend environment

Keep your existing v6 `.env` and add/confirm:

```env
SUPABASE_KNOWLEDGE_BUCKET=mihimura-knowledge
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768
RAG_TOP_K=8
RAG_CHUNK_CHARS=1800
RAG_CHUNK_OVERLAP_CHARS=220
RAG_EMBED_BATCH_SIZE=16
RAG_MAX_EXCERPT_CHARS=1200
```

`GEMINI_API_KEY` is reused for embeddings. Never place the Supabase secret/service-role key in the React frontend.

## 3. Install backend dependency

```powershell
cd mihimura-backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`pypdf` is used only for text-based PDFs. Image-only/scanned PDFs are intentionally rejected rather than silently creating an empty index. OCR can be added later.

## 4. Ingest a trusted agriculture PDF

From the backend folder:

```powershell
python scripts\ingest_knowledge.py "D:\Docs\rice-guide.pdf" `
  --title "Rice cultivation guidance" `
  --authority "Sri Lanka Department of Agriculture" `
  --authority-tier 1 `
  --document-type guidance `
  --crop Paddy `
  --language English `
  --source-url "https://official-source.example/..."
```

Authority tiers:

- `1` — official government / regulator / official crop institute
- `2` — university / peer-reviewed research / recognized research institute
- `3` — verified industry / extension partner
- `4` — general curated source

Only upload documents you are allowed to use and index.

## 5. API ingestion option

Swagger is available at:

```text
http://127.0.0.1:8000/docs
```

Use:

```text
POST /api/v1/knowledge/documents
```

Only an admin, demo administrator, or a verified agronomist/expert can ingest/update/delete knowledge.

## 6. Test hybrid retrieval

```text
POST /api/v1/knowledge/search
```

Example body:

```json
{
  "data": {
    "query": "What should be checked before fertilizer application in paddy?",
    "crop": "Paddy",
    "top_k": 6,
    "max_authority_tier": 2
  }
}
```

The response contains semantic similarity, keyword rank, hybrid score, source metadata, page numbers and excerpts.

## 7. Agent behavior after ingestion

Decision Support and Full Report now try:

```text
question
  → Gemini retrieval-query embedding
  → Supabase hybrid semantic + keyword search
  → authority-weighted ranked excerpts
  → LLM answer/report
  → deterministic safety layer
```

Simple Chat also uses RAG for general agriculture/explanation intents when matching curated knowledge exists.

If the RAG index is empty or unavailable, MihiMura falls back to the existing `approved_sources.json` registry. Those registry items are explicitly treated as **source pointers only**, not retrieved evidence.

## 8. Multilingual behavior

The query embedding is multilingual. Sinhala and Tamil questions are allowed to retrieve an authoritative English document. The final response still follows the conversation language selected/detected by MihiMura.

Do not set `strict_language=true` unless you specifically want to search only documents stored in the same language.

## 9. Safe chemical/fertilizer behavior

RAG improves grounding but does not remove the safety gate. A retrieved source must explicitly support any rate-sensitive recommendation. If an exact current rate, label claim, interval or product approval is not present in the retrieved evidence, MihiMura must not invent it.

## 10. Recommended initial corpus

Start small and authoritative. For the first demo, ingest roughly 10–30 high-value documents covering:

- Paddy production guidance
- Paddy fertilizer recommendations
- Common paddy pest/disease guidance
- Chilli production guidance
- Irrigation/water management
- Post-harvest handling
- Disaster/flood/drought preparedness

Do not dump hundreds of mixed-quality documents into the index before retrieval evaluation.
