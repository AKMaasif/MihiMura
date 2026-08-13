-- MihiMura v4 - Supabase Auth + PostgreSQL + Storage
-- Run this in a NEW Supabase project using SQL Editor, or with the Supabase CLI migration workflow.

create extension if not exists pgcrypto;

-- -----------------------------------------------------------------------------
-- Identity profile. Real auth users are mirrored here by trigger.
-- The FK to auth.users is intentionally omitted so the fixed demo UUID can exist
-- without creating a real authentication account. Real application identities still
-- use the exact auth.users UUID as profiles.id.
-- -----------------------------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key,
  email text,
  name text not null default 'Farmer',
  phone text,
  role text not null default 'farmer' check (role in ('farmer','manager','agronomist','supplier','analyst','admin','expert')),
  language text not null default 'English',
  district text,
  ds_division text,
  gn_division text,
  provider text not null default 'supabase',
  onboarding_complete boolean not null default false,
  location_consent boolean not null default false,
  lat double precision,
  lon double precision,
  guidance_mode text,
  irrigation text,
  experience text,
  notification_channels text,
  accessibility_json jsonb not null default '{}'::jsonb,
  primary_crops_json jsonb not null default '[]'::jsonb,
  farm_type text,
  professional_verified boolean not null default false,
  status text not null default 'active' check (status in ('active','suspended','deletion_requested','deleted')),
  deletion_requested_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (id,email,name,provider,created_at,updated_at)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name', 'Farmer'),
    coalesce(new.raw_app_meta_data ->> 'provider', 'supabase'),
    now(),
    now()
  )
  on conflict (id) do update set
    email = excluded.email,
    name = case when public.profiles.name = 'Farmer' then excluded.name else public.profiles.name end,
    provider = excluded.provider,
    updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert or update of email, raw_user_meta_data, raw_app_meta_data on auth.users
for each row execute procedure public.handle_new_auth_user();

-- -----------------------------------------------------------------------------
-- Farm digital twin
-- -----------------------------------------------------------------------------
create table if not exists public.farms (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  name text not null,
  district text not null,
  province text not null,
  area numeric not null default 0,
  water_source text,
  soil_type text,
  land_type text,
  crop text,
  lat double precision,
  lon double precision,
  boundary jsonb,
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create table if not exists public.projects (
  id text primary key,
  farm_id text not null references public.farms(id) on delete cascade,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  crop text not null,
  variety text,
  purpose text,
  season text,
  stage text,
  start_date date,
  actual_start_date date,
  target_harvest date,
  irrigation_mode text,
  seed_source text,
  health_score integer,
  risk_score integer,
  budget numeric,
  status text not null default 'active',
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists public.tasks (
  id text primary key,
  project_id text not null references public.projects(id) on delete cascade,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  task_type text,
  due_at timestamptz not null,
  priority text not null default 'medium',
  weather_dependency text,
  status text not null default 'pending',
  instructions text,
  materials text,
  assigned_to text,
  completion_note text,
  schedule_reason text,
  created_at timestamptz not null default now()
);

create table if not exists public.observations (
  id text primary key,
  project_id text not null references public.projects(id) on delete cascade,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  type text not null,
  note text not null,
  growth_stage text,
  rainfall text,
  irrigation text,
  pest_count integer not null default 0,
  symptoms text,
  action_taken text
);

create table if not exists public.expenses (
  id text primary key,
  project_id text not null references public.projects(id) on delete cascade,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  category text,
  amount numeric not null default 0,
  note text
);

create table if not exists public.harvests (
  id text primary key,
  project_id text not null references public.projects(id) on delete cascade,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  harvest_date date,
  yield_value numeric,
  yield_unit text,
  quality text,
  revenue numeric,
  note text,
  created_at timestamptz not null default now()
);

create table if not exists public.orders (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  project_id text not null references public.projects(id) on delete cascade,
  created_at timestamptz not null default now(),
  total numeric not null default 0,
  status text not null,
  items jsonb not null default '[]'::jsonb,
  delivery_address text,
  payment_method text,
  delivery_method text,
  consent boolean not null default false
);

create table if not exists public.expert_cases (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  project_id text not null references public.projects(id) on delete cascade,
  created_at timestamptz not null default now(),
  urgency text not null,
  reason text not null,
  status text not null,
  evidence text,
  preferred_language text,
  availability text,
  expert_decision text
);

create table if not exists public.notifications (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  scheduled_at timestamptz,
  channel text,
  title text,
  body text,
  status text,
  acknowledged boolean not null default false
);

create table if not exists public.recommendations (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  project_id text references public.projects(id) on delete set null,
  created_at timestamptz not null default now(),
  action text,
  rationale text,
  confidence double precision,
  sources jsonb not null default '[]'::jsonb,
  alternatives jsonb not null default '[]'::jsonb,
  safety jsonb not null default '{}'::jsonb,
  expiry timestamptz,
  status text
);

create table if not exists public.community_reports (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  district text,
  crop text,
  report_type text,
  severity text,
  note text,
  lat double precision,
  lon double precision,
  anonymized boolean not null default true
);

create table if not exists public.device_tokens (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  token text not null unique,
  platform text,
  created_at timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- Stateful AI memory
-- -----------------------------------------------------------------------------
create table if not exists public.conversations (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  project_id text references public.projects(id) on delete set null,
  title text not null default 'New farm conversation',
  status text not null default 'active' check (status in ('active','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id text primary key,
  conversation_id text not null references public.conversations(id) on delete cascade,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  role text not null check (role in ('user','assistant','system','tool')),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.conversation_memory (
  conversation_id text primary key references public.conversations(id) on delete cascade,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  summary text not null default '',
  active_intent text not null default 'general',
  known_facts jsonb not null default '{}'::jsonb,
  missing_fields jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.agent_runs (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  conversation_id text references public.conversations(id) on delete set null,
  message_id text references public.messages(id) on delete set null,
  created_at timestamptz not null default now(),
  request text,
  tools jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  provider text,
  model text,
  policy_decision text,
  latency_ms integer,
  output jsonb not null default '{}'::jsonb
);

create table if not exists public.tool_calls (
  id text primary key default ('tool_' || encode(gen_random_bytes(8),'hex')),
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  conversation_id text references public.conversations(id) on delete cascade,
  agent_run_id text references public.agent_runs(id) on delete cascade,
  tool_name text not null,
  input jsonb not null default '{}'::jsonb,
  output jsonb not null default '{}'::jsonb,
  status text not null default 'complete',
  created_at timestamptz not null default now()
);

create table if not exists public.reports (
  id text primary key,
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  conversation_id text references public.conversations(id) on delete set null,
  project_id text references public.projects(id) on delete set null,
  report_type text not null,
  title text not null,
  status text not null default 'ready',
  parameters jsonb not null default '{}'::jsonb,
  summary text,
  storage_path text,
  created_at timestamptz not null default now()
);

create table if not exists public.attachments (
  id text primary key default ('att_' || encode(gen_random_bytes(8),'hex')),
  owner_uid uuid not null references public.profiles(id) on delete cascade,
  conversation_id text references public.conversations(id) on delete cascade,
  project_id text references public.projects(id) on delete set null,
  kind text,
  file_name text,
  mime_type text,
  storage_path text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_events (
  id bigint generated by default as identity primary key,
  created_at timestamptz not null default now(),
  actor uuid not null references public.profiles(id) on delete cascade,
  action text not null,
  entity text not null,
  details jsonb not null default '{}'::jsonb
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
create index if not exists idx_farms_owner on public.farms(owner_uid);
create index if not exists idx_projects_owner on public.projects(owner_uid);
create index if not exists idx_tasks_owner_due on public.tasks(owner_uid, due_at);
create index if not exists idx_observations_owner on public.observations(owner_uid, created_at desc);
create index if not exists idx_conversations_owner_updated on public.conversations(owner_uid, updated_at desc);
create index if not exists idx_messages_conversation_created on public.messages(conversation_id, created_at);
create index if not exists idx_agent_runs_owner_created on public.agent_runs(owner_uid, created_at desc);
create index if not exists idx_reports_owner_created on public.reports(owner_uid, created_at desc);
create index if not exists idx_audit_actor_created on public.audit_events(actor, created_at desc);

-- -----------------------------------------------------------------------------
-- RLS defense-in-depth. The React application uses Supabase directly only for Auth.
-- Domain writes go through FastAPI, which uses the backend-only service role.
-- Authenticated clients may read only their own records; no direct write policies are
-- granted here for consequential domain data.
-- -----------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array[
    'profiles','farms','projects','tasks','observations','expenses','harvests','orders',
    'expert_cases','notifications','recommendations','community_reports','device_tokens',
    'conversations','messages','conversation_memory','agent_runs','tool_calls','reports','attachments','audit_events'
  ] loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

-- Re-running migration safely replaces policies.
drop policy if exists "read own profile" on public.profiles;
create policy "read own profile" on public.profiles for select to authenticated
using ((select auth.uid()) = id);

-- Owner tables with owner_uid.
do $$
declare
  t text;
  owner_col text;
begin
  foreach t in array array[
    'farms','projects','tasks','observations','expenses','harvests','orders','expert_cases',
    'notifications','recommendations','device_tokens','conversations','messages','conversation_memory',
    'agent_runs','tool_calls','reports','attachments','audit_events'
  ] loop
    owner_col := case when t = 'audit_events' then 'actor' else 'owner_uid' end;
    execute format('drop policy if exists "read own rows" on public.%I', t);
    execute format('create policy "read own rows" on public.%I for select to authenticated using ((select auth.uid()) = %I)', t, owner_col);
  end loop;
end $$;

-- community_reports intentionally has no direct select policy because exact locations
-- must not be exposed. FastAPI returns only privacy-threshold aggregate clusters.

-- -----------------------------------------------------------------------------
-- Storage
-- -----------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('mihimura-reports', 'mihimura-reports', false)
on conflict (id) do update set public = false;

insert into storage.buckets (id, name, public)
values ('mihimura-attachments', 'mihimura-attachments', false)
on conflict (id) do update set public = false;

-- Users may read files in their own UUID folder. Backend service role performs uploads.
drop policy if exists "read own reports" on storage.objects;
create policy "read own reports" on storage.objects for select to authenticated
using (bucket_id = 'mihimura-reports' and (storage.foldername(name))[1] = (select auth.uid())::text);

drop policy if exists "read own attachments" on storage.objects;
create policy "read own attachments" on storage.objects for select to authenticated
using (bucket_id = 'mihimura-attachments' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- -----------------------------------------------------------------------------
-- Demo seed (service-role/backend demo only)
-- -----------------------------------------------------------------------------
insert into public.profiles (id,email,name,role,language,district,provider,onboarding_complete,location_consent,lat,lon,professional_verified,status)
values ('00000000-0000-0000-0000-000000000001','demo@mihimura.lk','Demo Farmer','farmer','English','Ampara','demo',true,true,7.291,81.674,true,'active')
on conflict (id) do nothing;

insert into public.farms (id,owner_uid,name,district,province,area,water_source,soil_type,land_type,crop,lat,lon,boundary,status)
values
('farm_ampara_01','00000000-0000-0000-0000-000000000001','Ampara Paddy Block','Ampara','Eastern',42.5,'Irrigation canal','Alluvial clay','Lowland paddy','Paddy',7.291,81.674,'[[81.669,7.286],[81.679,7.286],[81.679,7.296],[81.669,7.296],[81.669,7.286]]'::jsonb,'active'),
('farm_ampara_02','00000000-0000-0000-0000-000000000001','East Chilli Plot','Ampara','Eastern',15.2,'Tube well','Sandy loam','Upland','Chilli',7.245,81.755,null,'active')
on conflict (id) do nothing;

insert into public.projects (id,farm_id,owner_uid,crop,variety,purpose,season,stage,start_date,actual_start_date,target_harvest,irrigation_mode,seed_source,health_score,risk_score,budget,status,notes)
values
('proj_paddy_2026','farm_ampara_01','00000000-0000-0000-0000-000000000001','Paddy','Bg 352','Grain production','Yala','Tillering','2026-07-02','2026-07-02','2026-10-18','Canal','Certified seed',68,62,145000,'active','Demo digital twin'),
('proj_chilli_2026','farm_ampara_02','00000000-0000-0000-0000-000000000001','Chilli','MI-2','Fresh market','Yala','Flowering','2026-06-18','2026-06-18','2026-10-05','Drip','Certified seed',84,38,98000,'active','Demo chilli project')
on conflict (id) do nothing;

insert into public.tasks (id,project_id,owner_uid,title,task_type,due_at,priority,weather_dependency,status,instructions,assigned_to,schedule_reason)
values
('task_01','proj_paddy_2026','00000000-0000-0000-0000-000000000001','Inspect western edge for leaf stress','Scouting','2026-08-12T16:30:00+05:30','high','Before next rainfall','pending','Inspect 5 representative locations and attach photos.','Self','Demo stage task'),
('task_02','proj_paddy_2026','00000000-0000-0000-0000-000000000001','Review fertilizer timing','Nutrition','2026-08-13T07:00:00+05:30','high','Delay if heavy-rain probability exceeds safety threshold','pending','Check current forecast and approved protocol before any application.','Self','Weather-sensitive demo task'),
('task_03','proj_chilli_2026','00000000-0000-0000-0000-000000000001','Potassium nutrition check','Nutrition','2026-08-14T08:00:00+05:30','medium','Avoid during strong rain','pending','Review flowering-stage condition; do not invent rates.','Self','Demo stage task')
on conflict (id) do nothing;
