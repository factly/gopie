-- +goose up
-- Create chats table
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

-- Create chat_messages table for storing the conversation
create table if not exists chat_messages(
    id uuid primary key default uuid_generate_v4(),
    chat_id uuid not null references chats(id) on delete cascade,
    content text not null,
    role text not null, -- 'user' or 'assistant'
    created_at timestamp with time zone not null default now(),
    created_by text default null
);

-- Create indexes
create index if not exists idx_chats_dataset_id on chats(dataset_id);
create index if not exists idx_chat_messages_chat_id on chat_messages(chat_id);

-- Setup triggers
select trigger_updated_at('chats'::regclass);

-- +goose down
drop table if exists chat_messages;
drop table if exists chats;
