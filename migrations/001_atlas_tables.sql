create table if not exists atlas_libraries (
  id text primary key,
  name text not null,
  prover text not null,
  url text not null,
  license text,
  harvester_version text,
  last_harvest_at timestamptz,
  statement_count integer not null default 0
);

create table if not exists atlas_statements (
  id bigint generated always as identity primary key,
  library_id text not null references atlas_libraries(id),
  native_name text not null,
  kind text not null,
  statement_text text,
  module text,
  source_url text not null,
  subject_codes text[] not null default '{}',
  first_seen_edition integer,
  last_seen_edition integer,
  retired boolean not null default false,
  unique (library_id, native_name)
);
create index if not exists atlas_statements_library_idx on atlas_statements(library_id);
create index if not exists atlas_statements_name_idx on atlas_statements(native_name);

create table if not exists atlas_concepts (
  id bigint generated always as identity primary key,
  slug text not null unique,
  title text not null,
  informal_statement text,
  wikidata_id text,
  wiedijk_number integer,
  msc_primary text,
  seed_source text not null,
  status text not null default 'open',
  notes text
);

create table if not exists atlas_alignments (
  id bigint generated always as identity primary key,
  concept_id bigint not null references atlas_concepts(id),
  statement_id bigint not null references atlas_statements(id),
  tier text not null check (tier in ('CURATED','ALIGNED','CANDIDATE')),
  evidence jsonb not null default '{}',
  created_by text,
  confirmed_by text,
  unique (concept_id, statement_id)
);

create table if not exists atlas_harvest_runs (
  id bigint generated always as identity primary key,
  library_id text not null references atlas_libraries(id),
  started_at timestamptz not null default now(),
  edition_tag integer,
  source_version text,
  statements_seen integer,
  added integer,
  retired integer,
  status text not null default 'running',
  log_url text
);

drop policy if exists atlas_libraries_read    on atlas_libraries;
drop policy if exists atlas_statements_read   on atlas_statements;
drop policy if exists atlas_concepts_read     on atlas_concepts;
drop policy if exists atlas_alignments_read   on atlas_alignments;
drop policy if exists atlas_harvest_runs_read on atlas_harvest_runs;

alter table atlas_libraries    enable row level security;
alter table atlas_statements   enable row level security;
alter table atlas_concepts     enable row level security;
alter table atlas_alignments   enable row level security;
alter table atlas_harvest_runs enable row level security;
create policy atlas_libraries_read    on atlas_libraries    for select to anon using (true);
create policy atlas_statements_read   on atlas_statements   for select to anon using (true);
create policy atlas_concepts_read     on atlas_concepts     for select to anon using (true);
create policy atlas_alignments_read   on atlas_alignments   for select to anon using (true);
create policy atlas_harvest_runs_read on atlas_harvest_runs for select to anon using (true);
grant select on atlas_libraries, atlas_statements, atlas_concepts, atlas_alignments, atlas_harvest_runs to anon;

insert into atlas_libraries (id, name, prover, url, license) values
  ('brockian', 'Brockian Corpus', 'Lean 4 / AXLE', 'https://torus.riemannlab.com/explore/lean-registry', 'project'),
  ('metamath', 'Metamath (set.mm)', 'Metamath', 'https://us.metamath.org', 'CC0'),
  ('mathlib',  'Mathlib', 'Lean 4', 'https://leanprover-community.github.io/mathlib4_docs/', 'Apache-2.0')
on conflict (id) do nothing;
