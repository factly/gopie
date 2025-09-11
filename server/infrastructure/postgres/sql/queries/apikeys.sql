-- name: CreateAPIKey :one
insert into api_keys (
    name,
    key_hash,
    created_by,
    description,
    expires_at,
    org_id
) values (
    $1, $2, $3, $4, $5, $6
)
returning *;

-- name: GetAPIKey :one
select * from api_keys
where id = $1 and org_id = $2;

-- name: GetAPIKeyByHash :one
select * from api_keys
where key_hash = $1
and (expires_at is null or expires_at > now())
and is_revoked = false;

-- name: ListAPIKeys :many
select * from api_keys
where org_id = $1
order by created_at desc
limit $2 offset $3;

-- name: UpdateAPIKeyLastUsed :one
update api_keys
set last_used_at = now()
where id = $1 and org_id = $2
returning *;

-- name: RevokeAPIKey :one
update api_keys
set is_revoked = true
where id = $1 and org_id = $2
returning *;

-- name: DeleteAPIKey :exec
delete from api_keys
where id = $1 and org_id = $2;

-- name: ListExpiredAPIKeys :many
select * from api_keys
where org_id = $1
and expires_at < now()
order by expires_at desc
limit $2 offset $3;

-- name: GetAPIKeysCount :one
select count(*) from api_keys
where org_id = $1;

-- name: SearchAPIKeys :many
SELECT *
FROM api_keys
WHERE
    org_id = $1 AND
    (name ILIKE concat('%', $2::text, '%') OR
    description ILIKE concat('%', $2::text, '%'))
ORDER BY
    CASE
        WHEN name ILIKE concat($2::text, '%') THEN 1
        WHEN name ILIKE concat('%', $2::text, '%') THEN 2
        ELSE 3
    END,
    created_at DESC
LIMIT $3 OFFSET $4;

