-- +goose Up
-- +goose StatementBegin
create table if not exists chats (
    id text primary key default uuid_generate_v4(),
    title TEXT,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now(),
    created_by text default null
);

CREATE index idx_chats_user_id on chats(created_by);

create table if not exists chat_messages (
    id uuid primary key default uuid_generate_v4(),
    chat_id text not null references chats(id) on delete cascade,
    choices jsonb not null,
    object text not null,
    model text default null,
    created_at timestamp with time zone default now()
);

create index idx_chat_messages_chat_id on chat_messages(chat_id);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
drop table if exists chat_messages;
drop table if exists chats;
-- +goose StatementEnd
