-- +goose up
-- create extension
create extension if not exists "uuid-ossp";

-- +goose statementbegin
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;
-- +goose statementend

-- +goose statementbegin
create or replace function trigger_updated_at(tablename regclass)
returns void as $$
begin
    execute format('create trigger set_updated_at before update on %s for each row when (old is distinct from new) execute function set_updated_at()', tablename);
end;
$$ language plpgsql;
-- +goose statementend

-- create collation
create collation if not exists case_insensitive (provider = icu, locale = 'und-u-ks-level2', deterministic = false);

-- create tables
create table if not exists datasets(
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    description text default null,
    format text not null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    row_count integer not null default 0,
    -- in bytes
    size bigint not null default 0,
    file_path text not null,
    columns jsonb
);

create table if not exists projects(
    id text primary key default uuid_generate_v4(),
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

create table if not exists failed_dataset_uploads(
    id text primary key default uuid_generate_v4(),
    dataset_id uuid not null references datasets(id) on delete cascade,
    error text not null,
    created_at timestamp with time zone not null default now()
);

-- create indexes
create index if not exists idx_project_datasets_project_id on project_datasets(project_id);
create index if not exists idx_project_datasets_dataset_id on project_datasets(dataset_id);
create index if not exists idx_datasets_name on datasets(name);
create index if not exists idx_projects_name on projects(name);

-- setup triggers
select trigger_updated_at('datasets'::regclass);
select trigger_updated_at('projects'::regclass);

-- +goose down
drop table if exists project_datasets;
drop table if exists failed_dataset_uploads;
drop table if exists projects;
drop table if exists datasets;
drop collation if exists case_insensitive;
drop function if exists trigger_updated_at(regclass);
drop function if exists set_updated_at();

