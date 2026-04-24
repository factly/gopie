-- name: CreateAPIKey :one
insert into api_keys (
    name,
    key_hash,
    created_by,
    description,
    expires_at
) values (
    $1, $2, $3, $4, $5
)
returning *;

-- name: GetAPIKey :one
select * from api_keys
where id = $1;

-- name: GetAPIKeyByHash :one
select * from api_keys
where key_hash = $1
and (expires_at is null or expires_at > now())
and is_revoked = false;

-- name: ListAPIKeys :many
select * from api_keys
order by created_at desc
limit $1 offset $2;

-- name: UpdateAPIKeyLastUsed :one
update api_keys
set last_used_at = now()
where id = $1
returning *;

-- name: RevokeAPIKey :one
update api_keys
set is_revoked = true
where id = $1
returning *;

-- name: DeleteAPIKey :exec
delete from api_keys
where id = $1;

-- name: ListExpiredAPIKeys :many
select * from api_keys
where expires_at < now()
order by expires_at desc
limit $1 offset $2;

-- name: GetAPIKeysCount :one
select count(*) from api_keys;

-- name: SearchAPIKeys :many
SELECT *
FROM api_keys
WHERE
    name ILIKE concat('%', $1::text, '%') OR
    description ILIKE concat('%', $1::text, '%')
ORDER BY
    CASE
        WHEN name ILIKE concat($1::text, '%') THEN 1
        WHEN name ILIKE concat('%', $1::text, '%') THEN 2
        ELSE 3
    END,
    created_at DESC
LIMIT $2 OFFSET $3;
