-- +goose Up
-- +goose StatementBegin
alter table datasets
    add column if not exists org_id text;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table datasets
    drop column if exists org_id;
-- +goose StatementEnd
