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
    dataset_id,
    user_id,
    org_id,
    sql,
    "format"
) VALUES (
    $1, $2, $3, $4, $5
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
