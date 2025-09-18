-- name: ListPendingDownloads :many
SELECT * FROM downloads
WHERE status = 'pending'
ORDER BY created_at ASC
FOR UPDATE SKIP LOCKED;

-- name: SetDownloadToProcessing :one
UPDATE downloads
SET
    status = 'processing',
    updated_at = now()
WHERE id = $1
RETURNING *;

-- name: SetDownloadAsCompleted :one
UPDATE downloads
SET
    status = 'completed',
    pre_signed_url = $2,
    completed_at = now(),
    updated_at = now(),
    expires_at = $3
WHERE id = $1
RETURNING *;

-- name: SetDownloadAsFailed :one
UPDATE downloads
SET
    status = 'failed',
    error_message = $2,
    completed_at = now(),
    updated_at = now()
WHERE id = $1
RETURNING *;

-- name: DeleteDownload :exec
DELETE FROM downloads
WHERE id = $1 AND org_id = $2;

-- name: CreateDownload :one
INSERT INTO downloads (
    id,
    dataset_id,
    user_id,
    org_id,
    sql,
    "format"
) VALUES (
    $1, $2, $3, $4, $5, $6
) RETURNING *;

-- name: GetDownload :one
SELECT * FROM downloads
WHERE id = $1 AND org_id = $2;

-- name: ListDownloadsByUser :many
SELECT * FROM downloads
WHERE user_id = $1 AND org_id = $2
ORDER BY created_at DESC
LIMIT $3
OFFSET $4;

-- name: FindExistingValidDownload :one
SELECT * FROM downloads
WHERE
    dataset_id = $1 AND
    org_id = $2 AND
    sql = $3 AND
    "format" = $4 AND
    user_id = $5 AND
    status IN ('processing', 'completed') AND
    (expires_at IS NULL OR expires_at > now())
ORDER BY created_at DESC
LIMIT 1;
