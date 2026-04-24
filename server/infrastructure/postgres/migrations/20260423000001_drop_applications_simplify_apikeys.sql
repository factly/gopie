-- +goose Up
-- +goose StatementBegin
-- Drop foreign key constraint and columns from api_keys
alter table api_keys drop constraint if exists api_keys_application_id_fkey;
alter table api_keys drop column if exists application_id;
alter table api_keys drop column if exists org_id;
-- Drop indexes that referenced application_id
drop index if exists idx_api_keys_application_id;
-- Drop applications table and its indexes
drop index if exists idx_applications_name;
drop index if exists idx_applications_created_by;
drop table if exists applications;
-- +goose StatementEnd

-- +goose Down
