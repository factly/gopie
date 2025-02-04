-- name: CreateFailedDatasetUpload :one
insert into failed_dataset_uploads (
    dataset_id,
    error
) values (
    $1, $2
) returning *;


-- name: DeleteFailedDatasetUpload :exec
delete from failed_dataset_uploads
where dataset_id = $1;

-- name: ListFailedDatasetUploads :many
select * from failed_dataset_uploads
order by created_at desc;

-- name: GetFailedDatasetUploadsCount :one
select count(*) from failed_dataset_uploads;
