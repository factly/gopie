-- +goose Up
-- +goose StatementBegin
ALTER TABLE database_sources ADD COLUMN org_id UUID;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE database_sources DROP COLUMN org_id;
-- +goose StatementEnd

