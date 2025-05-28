-- name: CreateDatasetSummary :exec
insert into dataset_summary (
    dataset_name,
    summary
) values (
    $1, $2
);

-- name: GetDatasetSummary :one
select * from dataset_summary 
where dataset_name = $1;

-- name: DeleteDatasetSummary :exec
delete from dataset_summary 
where dataset_name = $1;

