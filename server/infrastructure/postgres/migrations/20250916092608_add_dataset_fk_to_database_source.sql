-- +goose Up
-- +goose StatementBegin
alter table database_sources
add column dataset_id uuid references datasets(id);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table database_sources
drop column dataset_id;
-- +goose StatementEnd
