-- name: CreateProject :one
insert into projects (
    name,
    description,
    created_by,
    updated_by
) values ($1, $2, $3, $4)
returning *;

-- name: GetProject :one
select 
    p.*,
    array_remove(array_agg(pd.dataset_id), null) as dataset_ids,
    count(pd.dataset_id) as dataset_count
from projects p
left join project_datasets pd on p.id = pd.project_id
where p.id = $1
group by p.id;

-- name: UpdateProject :one
update projects
set 
    name = coalesce($1, name),
    description = coalesce($2, description),
    updated_by = coalesce($3, updated_by)
where id = $4
returning *;

-- name: DeleteProject :exec
delete from projects where id = $1;

-- name: SearchProjects :many
SELECT 
    p.*,
    count(pd.dataset_id) as dataset_count
FROM projects p
LEFT JOIN project_datasets pd ON p.id = pd.project_id
WHERE 
    p.name ILIKE concat('%', $1::text, '%') OR
    p.description ILIKE concat('%', $1::text, '%')
GROUP BY p.id
ORDER BY 
    CASE 
        WHEN p.name ILIKE concat($1::text, '%') THEN 1
        WHEN p.name ILIKE concat('%', $1::text, '%') THEN 2
        ELSE 3
    END,
    p.created_at DESC
LIMIT $2 OFFSET $3;

-- name: GetProjectsCount :one
select count(*) from projects;
