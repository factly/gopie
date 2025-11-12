-- +goose Up
-- +goose StatementBegin
alter table datasets add column source text not null default 'file';
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table datasets drop column if exists source;
-- +goose StatementEnd
