-- MihiMura Phase 4A - AI evaluation and validation framework
-- Run AFTER the existing MihiMura migrations.

create table if not exists public.evaluation_runs (
  id text primary key,
  created_by uuid references public.profiles(id) on delete set null,
  mode text not null check (mode in ('policy','live')),
  framework text not null,
  status text not null check (status in ('passed','needs_review','failed')),
  case_count integer not null default 0,
  passed_count integer not null default 0,
  failed_count integer not null default 0,
  pass_rate double precision not null default 0,
  average_score double precision not null default 0,
  duration_ms integer not null default 0,
  summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.evaluation_case_results (
  id text primary key,
  run_id text not null references public.evaluation_runs(id) on delete cascade,
  case_id text not null,
  name text,
  category text,
  passed boolean not null default false,
  score double precision not null default 0,
  metrics jsonb not null default '{}'::jsonb,
  issues jsonb not null default '[]'::jsonb,
  observed jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_evaluation_runs_created
  on public.evaluation_runs(created_at desc);
create index if not exists idx_evaluation_case_results_run
  on public.evaluation_case_results(run_id, created_at asc);
create index if not exists idx_evaluation_case_results_case
  on public.evaluation_case_results(case_id, created_at desc);

alter table public.evaluation_runs enable row level security;
alter table public.evaluation_case_results enable row level security;

-- Evaluation data is intentionally server-side only. The FastAPI service role
-- performs writes/reads after enforcing the MihiMura administrator gate.
