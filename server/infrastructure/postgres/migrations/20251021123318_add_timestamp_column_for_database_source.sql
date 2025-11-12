-- +goose Up
-- +goose StatementBegin
alter table database_sources add column timestamp_column text not null default '';
alter table database_sources add column last_updated_at timestamptz not null default now();
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table database_sources drop column if exists timestamp_column;
alter table database_sources drop column if exists last_updated_at;
-- +goose StatementEnd
