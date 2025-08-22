-- +goose Up
-- +goose StatementBegin
drop table if exists failed_dataset_uploads;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
-- nothing to run here
-- +goose StatementEnd
