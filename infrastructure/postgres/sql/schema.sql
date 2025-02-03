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
