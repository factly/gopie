-- +goose Up
-- +goose StatementBegin
-- create applications table
create table if not exists applications(
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    description text default null,
    created_by text not null,
    org_id text not null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);
-- create api_keys table
create table if not exists api_keys(
    id uuid primary key default uuid_generate_v4(),
    application_id uuid not null references applications(id) on delete cascade,
    name text not null,
    key_hash text not null,
    created_by text not null,
    description text default null,
    last_used_at timestamp with time zone default null,
    expires_at timestamp with time zone default null,
    is_revoked boolean not null default false,
    org_id text not null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);
-- create indexes for applications
create index if not exists idx_applications_name on applications(name collate case_insensitive);
create index if not exists idx_applications_created_by on applications(created_by);
-- create indexes for api_keys
create index if not exists idx_api_keys_application_id on api_keys(application_id);
create index if not exists idx_api_keys_key_hash on api_keys(key_hash);
create index if not exists idx_api_keys_created_by on api_keys(created_by);
create index if not exists idx_api_keys_name on api_keys(name collate case_insensitive);
create index if not exists idx_api_keys_expires_at on api_keys(expires_at);
-- setup updated_at triggers
select trigger_updated_at('applications'::regclass);
select trigger_updated_at('api_keys'::regclass);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
drop table if exists api_keys;
drop table if exists applications;
-- +goose StatementEnd
