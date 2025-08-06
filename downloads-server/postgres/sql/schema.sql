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
