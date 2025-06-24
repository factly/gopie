-- +goose Up
-- +goose StatementBegin
create type chat_visibility as enum ('private', 'public', 'organization');

alter table chats
add column visibility chat_visibility not null default 'private',
add column organization_id text default null;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table chats
drop column organization_id,
drop column visibility;

drop type chat_visibility;
-- +goose StatementEnd
