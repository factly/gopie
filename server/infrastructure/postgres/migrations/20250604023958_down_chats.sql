-- +goose Up
-- +goose StatementBegin
drop table if exists chat_messages;
drop table if exists chats;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
-- The down migration is not applicable as the chats table and chat_messages table are not created in this migration.
-- +goose StatementEnd
