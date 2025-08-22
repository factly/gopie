-- +goose Up
-- +goose StatementBegin
alter table datasets add column custom_prompt text default null;
alter table projects add column custom_prompt text default null;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table datasets drop column custom_prompt;
alter table projects drop column custom_prompt;
-- +goose StatementEnd
