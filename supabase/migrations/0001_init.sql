-- Voice-AI legal-intake schema: profiles (staff), callers (returning-caller key),
-- calls (one per session), model_events (AWS/NVIDIA tool outputs), queue_tasks.
-- Apply order: 0001_init -> 0002_record_call -> 0003_rls.

create extension if not exists "pgcrypto";   -- gen_random_uuid()

-- Shared updated_at trigger.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ============================================================ profiles (staff)
create type public.staff_role as enum ('admin', 'attorney', 'intake_staff', 'viewer');

create table public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  role         public.staff_role not null default 'viewer',
  firm_name    text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create trigger trg_profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Auto-create a profile when a new auth user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, display_name, role)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)),
    'viewer'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================ callers
-- Returning-caller dimension keyed by E.164 phone.
create table public.callers (
  id            uuid primary key default gen_random_uuid(),
  phone         text not null,
  name          text,
  email         text,
  call_count    integer not null default 0,
  first_seen_at timestamptz not null default now(),
  last_seen_at  timestamptz not null default now(),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  constraint callers_phone_key unique (phone)
);

create trigger trg_callers_updated_at
  before update on public.callers
  for each row execute function public.set_updated_at();

-- ============================================================ calls
create type public.call_decision as enum ('qualified', 'declined');
create type public.call_urgency  as enum ('immediate', 'standard', 'low');

create table public.calls (
  id                       uuid primary key default gen_random_uuid(),
  session_id               text not null,                 -- Twilio call SID or uuid hex
  caller_id                uuid references public.callers(id) on delete set null,

  -- denormalized summary (dashboard filters/sorts on these)
  caller_phone             text,
  caller_name              text,
  caller_email             text,
  case_type                text,
  state                    text,
  accident_date            date,
  sol_viable               boolean,
  sol_deadline             date,
  sol_days_remaining       integer,
  severity_tier            text,
  red_flags                text[] not null default '{}',
  urgency                  public.call_urgency,
  decision                 public.call_decision,
  attorney_tier            text,
  emotional_state          text,
  appointment_slot         text,
  defendant_type           text,
  has_prior_representation boolean,

  -- full fidelity + transcript + provenance
  intake_json              jsonb not null,
  transcript               text not null default '',
  call_ended_reason        text,
  s3_intake_key            text,
  s3_transcript_key        text,
  s3_queue_key             text,

  started_at               timestamptz,
  ended_at                 timestamptz not null default now(),
  created_at               timestamptz not null default now(),

  constraint calls_session_id_key unique (session_id)      -- idempotency key
);

create index calls_caller_id_idx on public.calls (caller_id);
create index calls_ended_at_idx  on public.calls (ended_at desc);
create index calls_decision_idx  on public.calls (decision);
create index calls_case_type_idx on public.calls (case_type);
create index calls_phone_idx     on public.calls (caller_phone);

-- ============================================================ model_events
-- AWS/NVIDIA tool-call provenance (from runtime/tool_events.jsonl).
create table public.model_events (
  id          bigint generated always as identity primary key,
  call_id     uuid not null references public.calls(id) on delete cascade,
  session_id  text not null,
  tool_name   text not null,                  -- check_sol/classify_treatment/route_case/end_call
  phase       text not null,                  -- start/end
  arguments   jsonb not null default '{}',
  result      jsonb,
  note        text,
  event_ts    timestamptz not null,
  created_at  timestamptz not null default now()
);

create index model_events_call_id_idx on public.model_events (call_id);
create index model_events_tool_idx    on public.model_events (call_id, tool_name);

-- ============================================================ queue_tasks
create type public.task_priority as enum ('high', 'medium', 'low');
create type public.task_status   as enum ('pending', 'in_progress', 'done', 'cancelled');

create table public.queue_tasks (
  id          bigint generated always as identity primary key,
  call_id     uuid not null references public.calls(id) on delete cascade,
  task_type   text not null,
  priority    public.task_priority not null,
  payload     jsonb not null default '{}',
  status      public.task_status not null default 'pending',
  added_at    timestamptz not null,
  created_at  timestamptz not null default now()
);

create index queue_tasks_call_id_idx on public.queue_tasks (call_id);
create index queue_tasks_status_idx  on public.queue_tasks (status, priority);
