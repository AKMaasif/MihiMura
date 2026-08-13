# MihiMura v7.1 — RAG ingestion progress patch

This patch changes only the RAG ingestion path. It does not change authentication, chat, multilingual routing, reports, farms, weather, or the hybrid retrieval query.

## What changes

Old v7 flow:

`Upload -> extract -> chunk -> embed every chunk -> insert -> return HTTP response`

New v7.1 flow:

`Upload -> create document + ingestion job -> return quickly -> FastAPI background task -> progress persisted to Supabase`

Each Gemini embedding request also has a finite timeout (45 seconds by default) plus retry/backoff, so one network/provider call cannot remain pending forever.

The Administration page polls job progress every 2 seconds and shows:

- queued / processing / completed / failed
- extraction / chunking / embedding / finalizing stage
- processed chunks / total chunks
- current batch / total batches
- percentage
- last heartbeat
- stalled warning after ~90 seconds without a heartbeat
- Retry for failed jobs
- Cancel request for active jobs

Documents remain `draft` while indexing. They become `published` only after all embeddings are stored, so partial documents are not used by normal RAG retrieval.

## Required Supabase migration

Run this file in **Supabase Dashboard -> SQL Editor**:

`supabase/migrations/20260813_0003_rag_ingestion_jobs.sql`

Then confirm:

```sql
select * from public.knowledge_ingestion_jobs order by created_at desc limit 5;
```

It is normal for the result to be empty before your first new upload.

## Existing v7 document stuck at chunk 20

1. Stop the old v7 backend with `Ctrl + C`. This terminates the old synchronous request.
2. Apply this patch and run the `0003` migration.
3. Restart backend and frontend.
4. Re-upload the **same source file** from Administration.

The v7.1 backend recognizes a legacy/partial document with the same checksum, reuses its document record, clears the incomplete chunks, puts the document into `draft`, and starts a new tracked ingestion job.

Do not manually continue from chunk 20; rebuilding the chunk set avoids gaps/duplicate chunk indexes.

## Backend

No new Python package is required for this patch.

Optional `.env` tuning (defaults already exist in code):

```env
RAG_EMBED_BATCH_SIZE=16
RAG_EMBED_TIMEOUT_MS=45000
RAG_EMBED_MAX_RETRIES=3
RAG_EMBED_RETRY_BASE_SECONDS=1.5
```

Start:

```powershell
cd mihimura-backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Check:

`http://127.0.0.1:8000/api/v1/health`

Expected new field:

```json
"rag_ingestion_jobs_ready": true
```

## Frontend

```powershell
cd mihimura-web
npm.cmd run dev
```

Open **Administration -> RAG ingestion jobs**.

Typical progress:

`queued -> extracting text -> chunking -> embedding 16/112 -> embedding 32/112 -> ... -> finalizing index -> completed`

## Important production note

This v7.1 patch uses FastAPI `BackgroundTasks`, which is appropriate for the current local/single-service implementation and fixes the long blocking browser request. The job state is durable in Supabase, but the Python task itself is not a distributed durable worker. If the backend process is killed during indexing, the UI can reveal the stale heartbeat; after restart you should retry the job.

Before high-scale production deployment, the same job table/API/UI can be retained while the executor is replaced by a durable worker/queue. That does not require redesigning the frontend again.
