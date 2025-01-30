-- name: AddDatasetToProject :exec
insert into project_datasets (project_id, dataset_id)
values ($1, $2)
on conflict do nothing;

-- name: RemoveDatasetFromProject :exec
delete from project_datasets
where project_id = $1 and dataset_id = $2;

-- name: ListProjectDatasets :many
select 
    d.*,
    pd.created_at as added_at
from datasets d
join project_datasets pd on d.id = pd.dataset_id
where pd.project_id = $1
order by pd.created_at desc
limit $2 offset $3;

-- name: ListDatasetProjects :many
select 
    p.*,
    pd.created_at as added_at
from projects p
join project_datasets pd on p.id = pd.project_id
where pd.dataset_id = $1
order by pd.created_at desc
limit $2 offset $3;

-- name: GetProjectDatasetsCount :one
select count(*) 
from project_datasets
where project_id = $1;

-- name: GetDatasetProjectsCount :one
select count(*) 
from project_datasets
where dataset_id = $1;

-- Batch Operations
-- name: BatchAddDatasetsToProject :exec
insert into project_datasets (project_id, dataset_id)
select $1, unnest($2::uuid[])
on conflict do nothing;

-- name: BatchRemoveDatasetsFromProject :exec
delete from project_datasets
where project_id = $1 and dataset_id = any($2::uuid[]);

-- Search and Filter Operations
-- name: SearchDatasetsByColumn :many
select *
from datasets
where columns @> $1
order by created_at desc
limit $2 offset $3;

-- name: GetProjectsByDateRange :many
select 
    p.*,
    array_remove(array_agg(pd.dataset_id), null) as dataset_ids,
    count(pd.dataset_id) as dataset_count
from projects p
left join project_datasets pd on p.id = pd.project_id
where p.created_at between $1 and $2
group by p.id
order by p.created_at desc
limit $3 offset $4;

-- name: GetDatasetsByDateRange :many
select *
from datasets
where created_at between $1 and $2
order by created_at desc
limit $3 offset $4;
