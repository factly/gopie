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
