-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS database_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_string TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    driver TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
); 
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS database_sources; 
-- +goose StatementEnd
