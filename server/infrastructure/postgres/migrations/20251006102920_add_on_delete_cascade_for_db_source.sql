-- +goose Up
-- +goose StatementBegin
ALTER TABLE database_sources
DROP CONSTRAINT IF EXISTS database_sources_dataset_id_fkey;

ALTER TABLE database_sources
ADD CONSTRAINT database_sources_dataset_id_fkey
FOREIGN KEY (dataset_id)
REFERENCES datasets(id)
ON DELETE CASCADE;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE database_sources
DROP CONSTRAINT IF EXISTS database_sources_dataset_id_fkey;

ALTER TABLE database_sources
ADD CONSTRAINT database_sources_dataset_id_fkey
FOREIGN KEY (dataset_id)
REFERENCES datasets(id);
-- +goose StatementEnd
