-- Track which law-firm number each call came in on (firm_phone) + a real-time
-- tool-event stream the deployed web app reads live. Idempotent: safe to re-run.

-- ============================================================ firm_phone on calls
alter table public.calls add column if not exists firm_phone text;
create index if not exists calls_firm_phone_idx on public.calls (firm_phone);

-- ============================================================ record_call (+ p_firm_phone)
-- Drop the old signature, then recreate with firm_phone wired in.
drop function if exists public.record_call(text, text, jsonb, text, jsonb, jsonb, text, jsonb);

create or replace function public.record_call(
  p_session_id        text,
  p_caller_phone      text,
  p_intake            jsonb,
  p_transcript        text,
  p_events            jsonb default '[]'::jsonb,
  p_tasks             jsonb default '[]'::jsonb,
  p_call_ended_reason text default 'completed',
  p_s3                jsonb default '{}'::jsonb,
  p_firm_phone        text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_caller_id uuid;
  v_call_id   uuid;
begin
  if p_caller_phone is not null and length(trim(p_caller_phone)) > 0 then
    insert into public.callers (phone, name, email, call_count, last_seen_at)
    values (
      p_caller_phone,
      nullif(p_intake->>'caller_name', ''),
      nullif(p_intake->>'caller_email', ''),
      1,
      now()
    )
    on conflict (phone) do update set
      name         = coalesce(public.callers.name,  excluded.name),
      email        = coalesce(public.callers.email, excluded.email),
      call_count   = public.callers.call_count + 1,
      last_seen_at = now()
    returning id into v_caller_id;
  end if;

  insert into public.calls (
    session_id, caller_id, caller_phone, firm_phone, caller_name, caller_email,
    case_type, state, accident_date, sol_viable, sol_deadline, sol_days_remaining,
    severity_tier, red_flags, urgency, decision, attorney_tier, emotional_state,
    appointment_slot, defendant_type, has_prior_representation,
    intake_json, transcript, call_ended_reason,
    s3_intake_key, s3_transcript_key, s3_queue_key, ended_at
  )
  values (
    p_session_id, v_caller_id, p_caller_phone, p_firm_phone,
    nullif(p_intake->>'caller_name', ''), nullif(p_intake->>'caller_email', ''),
    nullif(p_intake->>'case_type', ''), nullif(p_intake->>'state', ''),
    (nullif(p_intake->>'accident_date', ''))::date,
    (p_intake->>'sol_viable')::boolean,
    (nullif(p_intake->>'sol_deadline', ''))::date,
    (p_intake->>'sol_days_remaining')::int,
    nullif(p_intake->>'severity_tier', ''),
    coalesce(
      (select array_agg(x) from jsonb_array_elements_text(p_intake->'red_flags') x),
      '{}'
    ),
    (nullif(p_intake->>'urgency', ''))::public.call_urgency,
    (nullif(p_intake->>'decision', ''))::public.call_decision,
    nullif(p_intake->>'attorney_tier', ''), nullif(p_intake->>'emotional_state', ''),
    nullif(p_intake->>'appointment_slot', ''), nullif(p_intake->>'defendant_type', ''),
    (p_intake->>'has_prior_representation')::boolean,
    p_intake, coalesce(p_transcript, ''), p_call_ended_reason,
    nullif(p_s3->>'intake_key', ''), nullif(p_s3->>'transcript_key', ''),
    nullif(p_s3->>'queue_key', ''),
    now()
  )
  on conflict (session_id) do update set
    caller_id         = excluded.caller_id,
    caller_phone      = excluded.caller_phone,
    firm_phone        = excluded.firm_phone,
    caller_name       = excluded.caller_name,
    caller_email      = excluded.caller_email,
    case_type         = excluded.case_type,
    state             = excluded.state,
    accident_date     = excluded.accident_date,
    sol_viable        = excluded.sol_viable,
    sol_deadline      = excluded.sol_deadline,
    sol_days_remaining = excluded.sol_days_remaining,
    severity_tier     = excluded.severity_tier,
    red_flags         = excluded.red_flags,
    urgency           = excluded.urgency,
    decision          = excluded.decision,
    attorney_tier     = excluded.attorney_tier,
    emotional_state   = excluded.emotional_state,
    appointment_slot  = excluded.appointment_slot,
    defendant_type    = excluded.defendant_type,
    has_prior_representation = excluded.has_prior_representation,
    intake_json       = excluded.intake_json,
    transcript        = excluded.transcript,
    call_ended_reason = excluded.call_ended_reason,
    s3_intake_key     = excluded.s3_intake_key,
    s3_transcript_key = excluded.s3_transcript_key,
    s3_queue_key      = excluded.s3_queue_key,
    ended_at          = now()
  returning id into v_call_id;

  delete from public.model_events where call_id = v_call_id;
  insert into public.model_events (call_id, session_id, tool_name, phase, arguments, result, note, event_ts)
  select v_call_id, p_session_id,
         e->>'tool_name', e->>'phase',
         coalesce(e->'arguments', '{}'::jsonb), e->'result', e->>'note',
         coalesce((nullif(e->>'timestamp', ''))::timestamptz, now())
  from jsonb_array_elements(p_events) e;

  delete from public.queue_tasks where call_id = v_call_id;
  insert into public.queue_tasks (call_id, task_type, priority, payload, added_at)
  select v_call_id,
         t->>'task_type',
         (t->>'priority')::public.task_priority,
         coalesce(t->'payload', '{}'::jsonb),
         coalesce((nullif(t->>'added_at', ''))::timestamptz, now())
  from jsonb_array_elements(p_tasks) t;

  return v_call_id;
end;
$$;

revoke all on function public.record_call(text, text, jsonb, text, jsonb, jsonb, text, jsonb, text)
  from public, anon, authenticated;
grant execute on function public.record_call(text, text, jsonb, text, jsonb, jsonb, text, jsonb, text)
  to service_role;

-- ============================================================ live_tool_events
-- Real-time tool-call stream (no FK to calls — written DURING the call, before the
-- call row exists). The bot inserts here fire-and-forget; the web reads it live.
create table if not exists public.live_tool_events (
  id          bigint generated always as identity primary key,
  session_id  text,
  firm_phone  text,
  tool_name   text not null,
  phase       text not null,
  arguments   jsonb not null default '{}',
  result      jsonb,
  note        text,
  event_ts    timestamptz not null default now(),
  created_at  timestamptz not null default now()
);
create index if not exists live_tool_events_session_idx on public.live_tool_events (session_id);
create index if not exists live_tool_events_ts_idx on public.live_tool_events (event_ts desc);

alter table public.live_tool_events enable row level security;

drop policy if exists "staff read live_tool_events" on public.live_tool_events;
create policy "staff read live_tool_events"
  on public.live_tool_events for select to authenticated using (true);
