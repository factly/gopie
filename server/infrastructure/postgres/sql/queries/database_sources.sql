-- name: CreateDatabaseSource :one
INSERT INTO database_sources (
    connection_string,
    sql_query,
    driver,
    org_id
) VALUES (
    $1, $2, $3, $4
) RETURNING *;

-- name: GetDatabaseSource :one
SELECT * FROM database_sources
WHERE id = $1 and org_id = $2;

-- name: DeleteDatabaseSource :exec
DELETE FROM database_sources
WHERE id = $1;

-- name: ListDatabaseSources :many
SELECT * FROM database_sources
WHERE org_id = $1
ORDER BY created_at DESC
LIMIT $2 OFFSET $3; 
