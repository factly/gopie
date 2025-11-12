-- name: CreateDatabaseSource :one
INSERT INTO database_sources (
    connection_string,
    sql_query,
    driver,
    org_id,
    dataset_id,
    last_updated_at,
    timestamp_column
) VALUES (
    $1, $2, $3, $4, $5, $6, $7
) RETURNING *;

-- name: GetDatabaseSource :one
SELECT * FROM database_sources
WHERE dataset_id = $1 and org_id = $2;

-- name: DeleteDatabaseSource :exec
DELETE FROM database_sources
WHERE id = $1;

-- name: ListDatabaseSources :many
SELECT * FROM database_sources
WHERE org_id = $1
ORDER BY created_at DESC
LIMIT $2 OFFSET $3;

-- name: UpdateDatabaseSourceLastUpdatedAt :exec
update database_sources
set last_updated_at = $2
where id = $1;

-- name: HasTimestampColumn :one
SELECT EXISTS (
  SELECT 1
  FROM database_sources
  WHERE dataset_id = $1 AND org_id = $2 AND timestamp_column != ''
) AS has_timestamp_column; 
