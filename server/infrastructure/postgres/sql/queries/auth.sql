-- name: GetSessionByToken :one
SELECT "userId" AS user_id
FROM session
WHERE token = $1 AND "expiresAt" > NOW();

-- name: GetUserRole :one
SELECT role
FROM "user"
WHERE id = sqlc.arg(user_id);
