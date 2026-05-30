-- Row-level security. The bot writes with the service_role key, which BYPASSES
-- RLS entirely — so there are no write policies here. These policies only govern
-- the dashboard's anon/authenticated roles: logged-in staff get read-only access.

alter table public.callers      enable row level security;
alter table public.calls        enable row level security;
alter table public.model_events enable row level security;
alter table public.queue_tasks  enable row level security;
alter table public.profiles     enable row level security;

-- Data tables: any authenticated staff member can read; no write policies =>
-- inserts/updates/deletes from anon/authenticated are denied.
create policy "staff read callers"
  on public.callers for select to authenticated using (true);

create policy "staff read calls"
  on public.calls for select to authenticated using (true);

create policy "staff read model_events"
  on public.model_events for select to authenticated using (true);

create policy "staff read queue_tasks"
  on public.queue_tasks for select to authenticated using (true);

-- profiles: a user reads their own row; admins read all.
create policy "read own profile or admin reads all"
  on public.profiles for select to authenticated
  using (
    id = auth.uid()
    or exists (
      select 1 from public.profiles p
      where p.id = auth.uid() and p.role = 'admin'
    )
  );

create policy "update own profile"
  on public.profiles for update to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());
