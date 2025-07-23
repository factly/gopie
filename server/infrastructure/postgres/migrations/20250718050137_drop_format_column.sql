-- +goose Up
-- +goose StatementBegin
alter table datasets alter column format drop not null;
alter table datasets drop column if exists format;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table datasets add column format text not null default '';`
-- +goose StatementEnd
