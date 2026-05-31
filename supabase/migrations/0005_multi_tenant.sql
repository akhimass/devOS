-- Multi-tenant: each firm sees only the calls that came in on ITS Twilio number.
-- A firm is identified by profiles.twilio_phone; calls carry firm_phone (the called
-- number, set by the bot from Twilio's `to`). Admins (platform operators) see all.
-- Idempotent: safe to re-run.

-- ---- per-firm config on the staff profile -------------------------------------
alter table public.profiles add column if not exists business_hours jsonb;  -- {tz, days:{mon:[["09:00","17:00"]],...}}
alter table public.profiles add column if not exists timezone text;
-- twilio_phone already exists on profiles.

-- ---- helpers (SECURITY DEFINER so policies can read profiles without recursion)-
create or replace function public.current_firm_phone()
returns text language sql stable security definer set search_path = public as $$
  select twilio_phone from public.profiles where id = auth.uid()
$$;

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce((select role = 'admin' from public.profiles where id = auth.uid()), false)
$$;

grant execute on function public.current_firm_phone() to authenticated;
grant execute on function public.is_admin() to authenticated;

-- ---- replace the permissive read policies with firm-scoped ones ----------------
-- calls: scoped by firm_phone
drop policy if exists "staff read calls" on public.calls;
create policy "firm read calls" on public.calls for select to authenticated
  using (public.is_admin() or firm_phone = public.current_firm_phone());

-- live_tool_events: scoped by firm_phone
drop policy if exists "staff read live_tool_events" on public.live_tool_events;
create policy "firm read live_tool_events" on public.live_tool_events for select to authenticated
  using (public.is_admin() or firm_phone = public.current_firm_phone());

-- model_events: scoped via parent call
drop policy if exists "staff read model_events" on public.model_events;
create policy "firm read model_events" on public.model_events for select to authenticated
  using (
    public.is_admin() or exists (
      select 1 from public.calls c
      where c.id = model_events.call_id and c.firm_phone = public.current_firm_phone()
    )
  );

-- queue_tasks: scoped via parent call
drop policy if exists "staff read queue_tasks" on public.queue_tasks;
create policy "firm read queue_tasks" on public.queue_tasks for select to authenticated
  using (
    public.is_admin() or exists (
      select 1 from public.calls c
      where c.id = queue_tasks.call_id and c.firm_phone = public.current_firm_phone()
    )
  );

-- callers: scoped to callers who have a call with this firm
drop policy if exists "staff read callers" on public.callers;
create policy "firm read callers" on public.callers for select to authenticated
  using (
    public.is_admin() or exists (
      select 1 from public.calls c
      where c.caller_id = callers.id and c.firm_phone = public.current_firm_phone()
    )
  );

-- NOTE: for the current single-firm demo, set your staff user to admin (sees all)
--   update public.profiles set role = 'admin' where id = '<your-auth-user-id>';
-- or give it the firm number:
--   update public.profiles set twilio_phone = '+13853634730' where id = '<your-auth-user-id>';
