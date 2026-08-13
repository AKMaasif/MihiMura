-- MihiMura v7.1 - asynchronous RAG ingestion jobs with progress tracking
-- Run AFTER 20260812_0002_mihimura_rag.sql.

create table if not exists public.knowledge_ingestion_jobs (
  id text primary key,
  document_id text not null references public.knowledge_documents(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued','processing','completed','failed','cancel_requested','cancelled')),
  stage text not null default 'queued',
  progress_percent integer not null default 0 check (progress_percent between 0 and 100),
  total_chunks integer not null default 0,
  processed_chunks integer not null default 0,
  current_batch integer not null default 0,
  total_batches integer not null default 0,
  requested_document_status text not null default 'published' check (requested_document_status in ('draft','published','archived')),
  error_message text,
  details jsonb not null default '{}'::jsonb,
  created_by uuid references public.profiles(id) on delete set null,
  started_at timestamptz,
  heartbeat_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_knowledge_ingestion_jobs_document
  on public.knowledge_ingestion_jobs(document_id, created_at desc);
create index if not exists idx_knowledge_ingestion_jobs_status
  on public.knowledge_ingestion_jobs(status, updated_at desc);

alter table public.knowledge_ingestion_jobs enable row level security;

-- The application reads/writes this table through FastAPI service-role credentials.
-- No direct browser write policy is intentionally created.
