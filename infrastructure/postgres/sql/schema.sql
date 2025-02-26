create table if not exists datasets(
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    description text default null,
    format text not null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    row_count integer,
    alias text default null,
    created_by text default null,
    updated_by text default null,
    -- in bytes
    size bigint,
    file_path text not null,
    columns jsonb
);

create table if not exists projects(
    id text primary key default uuid_generate_v4(),
    name text not null,
    description text default null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    created_by text default null,
    updated_by text default null
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


create table if not exists chats(
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    description text default null,
    dataset_id uuid not null references datasets(id) on delete cascade,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    created_by text default null,
    updated_by text default null
);

create table if not exists chat_messages(
    id uuid primary key default uuid_generate_v4(),
    chat_id uuid not null references chats(id) on delete cascade,
    content text not null,
    role text not null, -- 'user' or 'assistant'
    created_at timestamp with time zone not null default now(),
    created_by text default null
);
