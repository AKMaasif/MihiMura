-- MihiMura v7 - Phase 2: hybrid agricultural knowledge retrieval (RAG)
-- Run AFTER 20260812_0001_mihimura_supabase.sql.
--
-- Design:
--   * pgvector stores multilingual Gemini embeddings.
--   * PostgreSQL full-text search provides exact/keyword retrieval.
--   * Hybrid RPC combines semantic + keyword rank using reciprocal-rank fusion.
--   * Authority metadata allows MihiMura to prefer official / research sources.
--   * Domain writes still go through FastAPI service-role credentials.

create extension if not exists vector;

create table if not exists public.knowledge_documents (
  id text primary key,
  title text not null,
  authority text not null,
  authority_tier integer not null default 4 check (authority_tier between 1 and 4),
  document_type text not null default 'guidance',
  crop text,
  language text not null default 'English',
  region text,
  district text,
  source_url text,
  version_label text,
  published_at date,
  mime_type text,
  original_file_name text,
  storage_path text,
  checksum_sha256 text not null unique,
  status text not null default 'published' check (status in ('draft','published','archived')),
  metadata jsonb not null default '{}'::jsonb,
  uploaded_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.knowledge_chunks (
  id text primary key,
  document_id text not null references public.knowledge_documents(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  page_start integer,
  page_end integer,
  token_estimate integer,
  embedding vector(768),
  metadata jsonb not null default '{}'::jsonb,
  fts tsvector generated always as (
    to_tsvector('simple', coalesce(content, ''))
  ) stored,
  created_at timestamptz not null default now(),
  unique(document_id, chunk_index)
);

create index if not exists idx_knowledge_documents_status_crop
  on public.knowledge_documents(status, crop, authority_tier);
create index if not exists idx_knowledge_documents_language
  on public.knowledge_documents(language);
create index if not exists idx_knowledge_chunks_document
  on public.knowledge_chunks(document_id, chunk_index);
create index if not exists idx_knowledge_chunks_fts
  on public.knowledge_chunks using gin(fts);
create index if not exists idx_knowledge_chunks_embedding_hnsw
  on public.knowledge_chunks using hnsw (embedding vector_cosine_ops);

-- Hybrid semantic + keyword search.  The 'simple' text-search configuration is used
-- intentionally so exact scientific/product names and multilingual tokens are not
-- stemmed with English-specific rules.  Semantic search provides the cross-language
-- retrieval signal; keyword rank boosts exact terms.
create or replace function public.search_knowledge_hybrid(
  query_text text,
  query_embedding vector(768),
  match_count integer default 8,
  filter_crop text default null,
  filter_language text default null,
  max_authority_tier integer default 4,
  filter_document_type text default null
)
returns table (
  chunk_id text,
  document_id text,
  title text,
  authority text,
  authority_tier integer,
  document_type text,
  crop text,
  language text,
  source_url text,
  version_label text,
  published_at date,
  page_start integer,
  page_end integer,
  content text,
  semantic_similarity double precision,
  keyword_rank double precision,
  hybrid_score double precision
)
language sql
stable
as $$
with eligible as (
  select
    c.id as chunk_id,
    c.document_id,
    c.content,
    c.page_start,
    c.page_end,
    c.embedding,
    c.fts,
    d.title,
    d.authority,
    d.authority_tier,
    d.document_type,
    d.crop,
    d.language,
    d.source_url,
    d.version_label,
    d.published_at
  from public.knowledge_chunks c
  join public.knowledge_documents d on d.id = c.document_id
  where d.status = 'published'
    and d.authority_tier <= greatest(1, least(coalesce(max_authority_tier, 4), 4))
    and (
      filter_crop is null
      or d.crop is null
      or lower(d.crop) = lower(filter_crop)
      or lower(d.crop) = 'general'
    )
    and (filter_language is null or lower(d.language) = lower(filter_language))
    and (filter_document_type is null or lower(d.document_type) = lower(filter_document_type))
),
semantic as (
  select
    e.chunk_id,
    row_number() over (order by e.embedding <=> query_embedding) as semantic_rank,
    greatest(-1.0, least(1.0, 1.0 - (e.embedding <=> query_embedding)))::double precision as semantic_similarity
  from eligible e
  where e.embedding is not null
  order by e.embedding <=> query_embedding
  limit greatest(coalesce(match_count, 8) * 5, 25)
),
keyword as (
  select
    e.chunk_id,
    row_number() over (
      order by ts_rank_cd(e.fts, websearch_to_tsquery('simple', coalesce(query_text, ''))) desc
    ) as keyword_position,
    ts_rank_cd(e.fts, websearch_to_tsquery('simple', coalesce(query_text, '')))::double precision as keyword_rank
  from eligible e
  where nullif(btrim(coalesce(query_text, '')), '') is not null
    and e.fts @@ websearch_to_tsquery('simple', coalesce(query_text, ''))
  order by keyword_rank desc
  limit greatest(coalesce(match_count, 8) * 5, 25)
),
combined as (
  select
    coalesce(s.chunk_id, k.chunk_id) as chunk_id,
    s.semantic_rank,
    s.semantic_similarity,
    k.keyword_position,
    k.keyword_rank
  from semantic s
  full outer join keyword k on k.chunk_id = s.chunk_id
),
scored as (
  select
    c.chunk_id,
    c.semantic_similarity,
    coalesce(c.keyword_rank, 0)::double precision as keyword_rank,
    (
      coalesce(1.0 / (60.0 + c.semantic_rank), 0.0)
      + coalesce(1.0 / (60.0 + c.keyword_position), 0.0)
    )::double precision as rrf_score
  from combined c
)
select
  e.chunk_id,
  e.document_id,
  e.title,
  e.authority,
  e.authority_tier,
  e.document_type,
  e.crop,
  e.language,
  e.source_url,
  e.version_label,
  e.published_at,
  e.page_start,
  e.page_end,
  e.content,
  coalesce(s.semantic_similarity, 0)::double precision,
  coalesce(s.keyword_rank, 0)::double precision,
  (
    s.rrf_score
    * case e.authority_tier
        when 1 then 1.16
        when 2 then 1.10
        when 3 then 1.05
        else 1.00
      end
  )::double precision as hybrid_score
from scored s
join eligible e on e.chunk_id = s.chunk_id
order by hybrid_score desc, semantic_similarity desc
limit greatest(1, least(coalesce(match_count, 8), 30));
$$;

-- RLS: knowledge is curated by the backend. Published knowledge can be read by
-- authenticated users for transparency, while draft/archived material remains hidden.
alter table public.knowledge_documents enable row level security;
alter table public.knowledge_chunks enable row level security;

drop policy if exists "read published knowledge documents" on public.knowledge_documents;
create policy "read published knowledge documents" on public.knowledge_documents
for select to authenticated
using (status = 'published');

drop policy if exists "read published knowledge chunks" on public.knowledge_chunks;
create policy "read published knowledge chunks" on public.knowledge_chunks
for select to authenticated
using (
  exists (
    select 1
    from public.knowledge_documents d
    where d.id = knowledge_chunks.document_id
      and d.status = 'published'
  )
);

-- Private originals; FastAPI service role performs ingestion.
insert into storage.buckets (id, name, public)
values ('mihimura-knowledge', 'mihimura-knowledge', false)
on conflict (id) do update set public = false;
