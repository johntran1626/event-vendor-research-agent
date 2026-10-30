-- Project C, rotation round (#3).
-- Every result the pipeline makes has a table. The pipeline writes with the
-- secret key (service_role). The app reads with the publishable key (anon):
-- select only, through RLS. No insert, update or delete policy exists for anon.

-- One row per pipeline run. Everything a run produced carries its run_id.
create table if not exists public.runs (
  run_id text primary key,
  started_at timestamptz not null,
  finished_at timestamptz,
  code_version text not null,                     -- git commit of the pipeline
  models jsonb not null default '{}'::jsonb,      -- step -> model, for every step that called one
  crawl_id text,
  availability_check_id text,
  briefs jsonb not null default '[]'::jsonb,      -- the brief ids and dates this run scored
  notes text,
  check (jsonb_typeof(models) = 'object'),
  check (jsonb_typeof(briefs) = 'array')
);

-- One row per vendor in data/vendors.csv, with the listing the crawl matched.
create table if not exists public.vendors (
  vendor_id text primary key,
  vendor_name text not null,
  category text not null,
  area_hint text,
  slug text,
  listing_name text,
  match_notes text[] not null default '{}',
  check (category in ('venue', 'caterer', 'rental'))
);

-- One row per claim. Sources that disagree are two rows for the same field,
-- marked as a conflict. A re-check adds new rows; old ones stay with their date.
create table if not exists public.facts (
  fact_id bigint generated always as identity primary key,
  run_id text not null references public.runs (run_id) on delete cascade,
  vendor_id text not null references public.vendors (vendor_id),
  field text not null,                            -- status, zip, owner, capacity, price, feature, dietary, ...
  value jsonb,                                    -- null only when the value is unknown
  is_unknown boolean not null default false,
  source_url text,
  quote text,                                     -- the words on the page that support the value
  checked_at timestamptz not null,                -- when the source page was fetched
  is_conflict boolean not null default false,
  used boolean not null default false,        -- the claim the rubric uses for this field
  note text,
  check (is_unknown or (value is not null and source_url is not null))
);
create index if not exists facts_run_vendor on public.facts (run_id, vendor_id);

-- What a careful researcher would raise for a vendor (docs/RUBRIC.md, the flags table).
create table if not exists public.flags (
  run_id text not null references public.runs (run_id) on delete cascade,
  vendor_id text not null references public.vendors (vendor_id),
  flag text not null,
  reason text not null,
  source_url text,
  primary key (run_id, vendor_id, flag)
);

-- The booking calendar, per vendor and brief date.
create table if not exists public.availability (
  run_id text not null references public.runs (run_id) on delete cascade,
  vendor_id text not null references public.vendors (vendor_id),
  date date not null,
  status text not null,
  url text,                                       -- the /availability URL called
  checked_at timestamptz not null,
  note text,
  primary key (run_id, vendor_id, date),
  check (status in ('available', 'booked', 'hold', 'unknown'))
);

-- The rubric, per vendor and brief. Plain code writes these, never a model.
create table if not exists public.scores (
  run_id text not null references public.runs (run_id) on delete cascade,
  brief_id text not null,
  vendor_id text not null references public.vendors (vendor_id),
  category text not null,
  disqualified_reasons text[] not null default '{}',
  points jsonb not null default '{}'::jsonb,      -- condition -> points earned
  score integer,
  rank integer,
  label text not null,
  reason text,                                    -- one plain line on why
  primary key (run_id, brief_id, vendor_id),
  check (category in ('venue', 'caterer', 'rental')),
  check (label in ('shortlist', 'maybe', 'reject', 'disqualified')),
  check (score is null or score between 0 and 100)
);

-- The best package per brief: the rubric's, and the one after replies.
create table if not exists public.packages (
  run_id text not null references public.runs (run_id) on delete cascade,
  brief_id text not null,
  kind text not null,
  fits boolean not null,                          -- false: no package fits the budget
  venue_id text references public.vendors (vendor_id),
  caterer_id text references public.vendors (vendor_id),
  rental_id text references public.vendors (vendor_id),
  costs jsonb not null default '{}'::jsonb,       -- venue, caterer, rental -> dollars
  total_cost numeric,
  total_budget numeric not null,
  budget_left numeric,
  points integer,
  rank_total integer,
  why text not null,
  winners jsonb,                                  -- the category winners and what they would cost together
  primary key (run_id, brief_id, kind),
  check (kind in ('rubric', 'after_replies'))
);

-- Inquiry and follow-up drafts. citations: the facts each specific comes from.
create table if not exists public.drafts (
  draft_id bigint generated always as identity primary key,
  run_id text not null references public.runs (run_id) on delete cascade,
  brief_id text not null,
  vendor_id text not null references public.vendors (vendor_id),
  kind text not null,
  addressed_to text,                              -- the owner by name, or null for no name
  subject text not null,
  body text not null,
  citations jsonb not null default '[]'::jsonb,
  answers_thread_id text,                         -- follow-ups: the reply this one answers
  created_at timestamptz not null default now(),
  check (kind in ('inquiry', 'follow_up')),
  check (jsonb_typeof(citations) = 'array')
);

-- Every inquiry sent through /inbox/send. The sandbox keeps nothing.
create table if not exists public.threads (
  thread_id text primary key,
  brief_id text not null,
  vendor_id text not null references public.vendors (vendor_id),
  draft_id bigint references public.drafts (draft_id),
  in_reply_to text references public.threads (thread_id),
  event_date date not null,
  guests integer not null,
  subject text not null,
  body text not null,                             -- our own copy of what we sent
  sent_at timestamptz not null,
  reply_expected_after timestamptz
);

-- Vendor replies, stored as data. They never change labels or points.
create table if not exists public.replies (
  thread_id text primary key references public.threads (thread_id) on delete cascade,
  received_at timestamptz not null,
  from_name text,
  from_email text,
  subject text,
  body text not null,
  kind text,                                      -- what the reply is
  quote_price numeric,
  hold_until date,
  counter_dates date[] not null default '{}',
  question text,
  plain_summary text,                             -- what the vendor said, in plain words
  has_instructions boolean not null default false,-- the reply tried to tell us to do something; ignored
  instructions_note text,
  read_by_model text,
  check (kind is null or kind in ('quote', 'hold', 'counter_date', 'decline', 'question', 'other'))
);

-- RLS on every table. anon (the app) can select. Only service_role writes.
do $$
declare t text;
begin
  foreach t in array array['runs', 'vendors', 'facts', 'flags', 'availability', 'scores',
                           'packages', 'drafts', 'threads', 'replies']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated, public', t);
    execute format('grant select on public.%I to anon, authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
    execute format('drop policy if exists "app can read %s" on public.%I', t, t);
    execute format('create policy "app can read %s" on public.%I for select to anon, authenticated using (true)', t, t);
  end loop;
end $$;

grant usage, select on all sequences in schema public to service_role;
