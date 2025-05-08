-- name: CreateDatabaseSource :one
INSERT INTO database_sources (
    connection_string,
    sql_query,
    driver
) VALUES (
    $1, $2, $3
) RETURNING *;

-- name: GetDatabaseSource :one
SELECT * FROM database_sources
WHERE id = $1;

-- name: UpdateDatabaseSource :one
UPDATE database_sources
SET 
    connection_string = COALESCE($2, connection_string),
    sql_query = COALESCE($3, sql_query),
    driver = COALESCE($4, driver),
    updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: DeleteDatabaseSource :exec
DELETE FROM database_sources
WHERE id = $1;

-- name: ListDatabaseSources :many
SELECT * FROM database_sources
ORDER BY created_at DESC
LIMIT $1 OFFSET $2; 