-- +goose Up
-- +goose StatementBegin
alter table database_sources add column org_id uuid;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table database_sources drop column org_id;
-- +goose StatementEnd
