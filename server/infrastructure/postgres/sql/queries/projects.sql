-- name: CreateProject :one
insert into projects (
    name,
    description,
    created_by,
    updated_by,
    org_id,
    custom_prompt
) values ($1, $2, $3, $4, $5, $6)
returning *;

-- name: ListAllProjects :many
select * from projects;

-- name: GetProject :one
select 
    p.*,
    array_remove(array_agg(pd.dataset_id), null) as dataset_ids,
    count(pd.dataset_id) as dataset_count
from projects p
left join project_datasets pd on p.id = pd.project_id
where p.id = $1 and p.org_id = $2
group by p.id;

-- name: UpdateProject :one
update projects
set 
    name = coalesce($1, name),
    description = coalesce($2, description),
    updated_by = coalesce($3, updated_by),
    custom_prompt = coalesce($4, custom_prompt)
where id = $5 and org_id = $6
returning *;

-- name: DeleteProject :exec
delete from projects where id = $1 and org_id = $2;

-- name: SearchProjects :many
SELECT 
    p.*,
    count(pd.dataset_id) as dataset_count
FROM projects p
LEFT JOIN project_datasets pd ON p.id = pd.project_id
WHERE 
    p.org_id = $1 AND
    (p.name ILIKE concat('%', $2::text, '%') OR
    p.description ILIKE concat('%', $2::text, '%'))
GROUP BY p.id
ORDER BY 
    CASE 
        WHEN p.name ILIKE concat($2::text, '%') THEN 1
        WHEN p.name ILIKE concat('%', $2::text, '%') THEN 2
        ELSE 3
    END,
    p.created_at DESC
LIMIT $3 OFFSET $4;

-- name: GetProjectsCount :one
select count(*) from projects where org_id = $1;

-- name: GetProjectByID :one
select * from projects where id = $1;

-- name: ProjectsBelongToOrg :one
SELECT count(*) = cardinality($1::text[]) AS all_belong_to_org
FROM projects
WHERE id = ANY($1::text[]) AND org_id = $2;

-- name: DatasetWithNamesBelongsToOrg :one
SELECT count(*) = cardinality($1::text[]) AS all_belong_to_org
FROM datasets
WHERE name = ANY($1::text[]) AND org_id = $2;

-- name: DatasetWithIDsBelongsToOrg :one
SELECT count(*) = cardinality($1::uuid[]) AS all_belong_to_org
FROM datasets
WHERE id = ANY($1::uuid[]) AND org_id = $2;

-- name: GetProjectsByIDs :many
SELECT * FROM projects
WHERE org_id = sqlc.arg(org_id) AND id = ANY(sqlc.arg(project_ids)::text[])
ORDER BY created_at DESC;

-- name: GetProjectByOrgAndCreator :one
select
    p.*,
    array_remove(array_agg(pd.dataset_id), null) as dataset_ids,
    count(pd.dataset_id) as dataset_count
from projects p
left join project_datasets pd on p.id = pd.project_id
where p.id = $1 and p.org_id = $2 and p.created_by = $3
group by p.id;

-- name: ListProjectsByOrgAndCreator :many
SELECT
    p.*,
    count(pd.dataset_id) as dataset_count
FROM projects p
LEFT JOIN project_datasets pd ON p.id = pd.project_id
WHERE p.org_id = $1 AND p.created_by = $2
GROUP BY p.id
ORDER BY p.created_at DESC;

-- name: DeleteProjectByOrgAndCreator :exec
delete from projects where id = $1 and org_id = $2 and created_by = $3;

-- name: SearchProjectsByOrgAndCreator :many
SELECT
    p.*,
    count(pd.dataset_id) as dataset_count
FROM projects p
LEFT JOIN project_datasets pd ON p.id = pd.project_id
WHERE
    p.org_id = $1 AND
    p.created_by = $2 AND
    (p.name ILIKE concat('%', $3::text, '%') OR
    p.description ILIKE concat('%', $3::text, '%'))
GROUP BY p.id
ORDER BY
    CASE
        WHEN p.name ILIKE concat($3::text, '%') THEN 1
        WHEN p.name ILIKE concat('%', $3::text, '%') THEN 2
        ELSE 3
    END,
    p.created_at DESC
LIMIT $4 OFFSET $5;

-- name: UpdateProjectByOrgAndCreator :one
update projects
set
    name = coalesce($1, name),
    description = coalesce($2, description),
    updated_by = coalesce($3, updated_by),
    custom_prompt = coalesce($4, custom_prompt)
where id = $5 and org_id = $6 and created_by = $7
returning *;
