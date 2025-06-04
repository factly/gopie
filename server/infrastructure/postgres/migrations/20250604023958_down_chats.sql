-- +goose Up
-- +goose StatementBegin
drop table if exists chats;
drop table if exists chat_messages;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
-- The down migration is not applicable as the chats table and chat_messages table are not created in this migration.
-- +goose StatementEnd
