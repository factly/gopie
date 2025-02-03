-- name: CreateProject :one
insert into projects (
    name,
    description
) values ($1, $2)
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
    description = coalesce($2, description)
where id = $3
returning *;

-- name: DeleteProject :exec
delete from projects where id = $1;

-- name: ListProjects :many
select 
    p.*,
    array_remove(array_agg(pd.dataset_id), null) as dataset_ids,
    count(pd.dataset_id) as dataset_count
from projects p
left join project_datasets pd on p.id = pd.project_id
group by p.id
order by p.created_at desc
limit $1 offset $2;

-- name: SearchProjects :many
SELECT 
    p.*,
    array_remove(array_agg(pd.dataset_id), null) as dataset_ids,
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
