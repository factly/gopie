-- +goose Up
-- +goose StatementBegin
alter table projects
    add column if not exists org_id uuid;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table projects
    drop column if exists org_id;
-- +goose StatementEnd
