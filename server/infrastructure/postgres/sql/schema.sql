create table if not exists datasets(
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    description text default null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    row_count integer,
    alias text default null,
    created_by text default null,
    updated_by text default null,
    -- in bytes
    size bigint,
    file_path text not null,
    columns jsonb,
    org_id text,
    custom_prompt text default null
);

create table if not exists projects(
    id text primary key default uuid_generate_v4(),
    name text not null,
    org_id text,
    description text default null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    created_by text default null,
    updated_by text default null,
    custom_prompt text default null
);

create table if not exists project_datasets(
    project_id text not null references projects(id) on delete cascade,
    dataset_id uuid not null references datasets(id) on delete cascade,
    created_at timestamp with time zone not null default now(),
    primary key (project_id, dataset_id)
);

create table if not exists failed_dataset_uploads(
    id text primary key default uuid_generate_v4(),
    dataset_id text not null references datasets(id) on delete cascade,
    error text not null,
    created_at timestamp with time zone not null default now()
);

create table if not exists dataset_summary (
    dataset_name text not null references datasets(name) on delete cascade,
    summary jsonb not null
);

create table if not exists database_sources (
    id uuid primary key default uuid_generate_v4(),
    connection_string text not null,
    sql_query text not null,
    driver text not null,
    org_id text default null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);

create type chat_visibility as enum ('private', 'public', 'organization');

create table if not exists chats (
    id text primary key,
    title text,
    visibility chat_visibility default 'private',
    organization_id text default null,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now(),
    created_by text default null
);

create index idx_chats_created_by on chats(created_by);

create table if not exists chat_messages (
    id uuid primary key default uuid_generate_v4(),
    chat_id text not null references chats(id) on delete cascade,
    choices jsonb not null,
    object text not null,
    model text default null,
    created_at timestamp with time zone default now()
);

create type download_status as enum (
  'pending',
  'processing',
  'completed',
  'failed',
  'expired'
);

create table downloads(
  id uuid primary key default uuid_generate_v4(),
  sql text not null,
  dataset_id text not null,
  status download_status not null default 'pending',
  "format" text not null,
  pre_signed_url text,
  error_message text,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  expires_at timestamp with time zone,
  completed_at timestamp with time zone,
  user_id text not null,
  org_id text not null
);
