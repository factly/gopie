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

-- name: DeleteDatabaseSource :exec
DELETE FROM database_sources
WHERE id = $1;

-- name: ListDatabaseSources :many
SELECT * FROM database_sources
ORDER BY created_at DESC
LIMIT $1 OFFSET $2; 
