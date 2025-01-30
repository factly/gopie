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
select 
    p.*,
    array_remove(array_agg(pd.dataset_id), null) as dataset_ids,
    count(pd.dataset_id) as dataset_count
from projects p
left join project_datasets pd on p.id = pd.project_id
where 
    p.name ilike concat('%', $1, '%') or
    p.description ilike concat('%', $1, '%')
group by p.id
order by 
    case 
        when p.name ilike concat($1, '%') then 1
        when p.name ilike concat('%', $1, '%') then 2
        else 3
    end,
    p.created_at desc
limit $2 offset $3;

-- name: GetProjectsCount :one
select count(*) from projects;
