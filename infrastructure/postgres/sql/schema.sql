create extension if not exists "uuid-ossp";

create or replace function set_updated_at()
  returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create or replace function trigger_updated_at(tablename regclass)
  returns trigger as $$
begin
  execute format('create trigger set_updated_at before update on %s for each row when (old is distinct from new) execute function set_updated_at()', tablename);
end;
$$ language plpgsql;

create collation case_insensitive (provider = icu, locale = 'und-u-ks-level2', deterministic = false);

create table if not exists datasets(
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  description text default null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  row_count integer,
  columns jsonb
);

create table if not exists projects(
  id text primary key,
  name text not null,
  description text default null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

create table if not exists project_datasets(
  project_id text not null references projects(id) on delete cascade,
  dataset_id uuid not null references datasets(id) on delete cascade,
  created_at timestamp with time zone not null default now(),
  primary key (project_id, dataset_id)
);

create index if not exists idx_project_datasets_project_id on project_datasets(project_id);
create index if not exists idx_project_datasets_dataset_id on project_datasets(dataset_id);
create index if not exists idx_datasets_name on datasets(name);
create index if not exists idx_projects_name on projects(name);

select trigger_updated_at('datasets');
select trigger_updated_at('projects');
