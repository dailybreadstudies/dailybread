-- Daily Bread Online: sign-in and progress sync (Supabase project "dailybread", West EU)
-- Paste into Supabase → SQL Editor → New query → Run. Safe to run again.

-- 1. Reading progress, one row per reader and edition (classic / kids)
create table if not exists public.progress (
  user_id    uuid not null references auth.users (id) on delete cascade,
  edition    text not null default 'classic' check (edition in ('classic', 'kids')),
  data       jsonb not null default '{}'::jsonb,   -- the browser's dbs-progress / dbs-kids-progress
  settings   jsonb,                               -- reader settings (theme, text size …), optional
  updated_at timestamptz not null default now(),
  primary key (user_id, edition)
);

-- 2. Email-list consent records (phase 2): what was shown, when, and how they signed in
create table if not exists public.consent (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users (id) on delete cascade,
  opted_in   boolean not null,
  wording    text not null,
  method     text,
  created_at timestamptz not null default now()
);

-- 3. Each reader can only see and change their own rows
alter table public.progress enable row level security;
alter table public.consent  enable row level security;

drop policy if exists "own progress: read"   on public.progress;
drop policy if exists "own progress: add"    on public.progress;
drop policy if exists "own progress: change" on public.progress;
drop policy if exists "own progress: remove" on public.progress;
create policy "own progress: read"   on public.progress for select to authenticated using ((select auth.uid()) = user_id);
create policy "own progress: add"    on public.progress for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "own progress: change" on public.progress for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "own progress: remove" on public.progress for delete to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "own consent: read" on public.consent;
drop policy if exists "own consent: add"  on public.consent;
create policy "own consent: read" on public.consent for select to authenticated using ((select auth.uid()) = user_id);
create policy "own consent: add"  on public.consent for insert to authenticated with check ((select auth.uid()) = user_id);

-- 4. Keep updated_at current
create or replace function public.touch_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end; $$;
drop trigger if exists progress_touch on public.progress;
create trigger progress_touch before update on public.progress
  for each row execute function public.touch_updated_at();

-- 5. "Delete my account" from the account area: removes the sign-in and (by cascade) all the reader's data
create or replace function public.delete_my_account() returns void
language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  delete from auth.users where id = auth.uid();
end; $$;
revoke all on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;

-- 6. Keep-alive: a harmless public call the GitHub podcast job can make every few hours so the free project never pauses
create or replace function public.ping() returns text language sql stable set search_path = '' as $$ select 'ok'::text $$;
grant execute on function public.ping() to anon, authenticated;
