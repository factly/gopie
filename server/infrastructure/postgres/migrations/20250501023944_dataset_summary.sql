-- +goose Up
-- +goose StatementBegin
create table if not exists dataset_summary (
    dataset_name text not null references datasets(name) on delete cascade,
    summary jsonb not null
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
drop table if exists dataset_summary;
-- +goose StatementEnd
