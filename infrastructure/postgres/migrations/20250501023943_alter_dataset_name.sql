-- +goose Up
-- +goose StatementBegin
alter table datasets add constraint datasets_name_unique unique(name);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
alter table datasets drop constraint if exists datasets_name_unique;
-- +goose StatementEnd
