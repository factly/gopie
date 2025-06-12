-- +goose Up
-- +goose StatementBegin
create table if not exists chats (
    id uuid primary key default uuid_generate_v4(),
    title TEXT,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now(),
    created_by text default null
);

create index idx_chats_user_id on chats(created_by);

create table if not exists chat_messages (
    id uuid primary key default uuid_generate_v4(),
    key integer not null,
    chat_id uuid not null references chats(id) on delete cascade,
    choices jsonb not null,
    object text not null,
    model text default null,
    created_at timestamp with time zone default now()
    unique (chat_id, key)
);

create index idx_chat_messages_chat_id on chat_messages(chat_id);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
drop table if exists chat_messages;
drop table if exists chats;
-- +goose StatementEnd
