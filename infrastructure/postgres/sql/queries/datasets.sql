-- name: CreateDataset :one
insert into datasets (
    name,
    description,
    format,
    row_count,
    size,
    file_path,
    columns
) values ($1, $2, $3, $4, $5, $6, $7)
returning *;

-- name: GetDataset :one
select * from datasets where id = $1;

-- name: UpdateDataset :one
update datasets
set 
    name = coalesce($1, name),
    description = coalesce($2, description),
    format = coalesce($3, format),
    row_count = coalesce($4, row_count),
    size = coalesce($5, size),
    file_path = coalesce($6, file_path),
    columns = coalesce($7, columns)
where id = $8
returning *;

-- name: DeleteDataset :exec
delete from datasets where id = $1;

-- name: ListDatasets :many
select * from datasets
order by created_at desc
limit $1 offset $2;

-- name: SearchDatasets :many
select * from datasets
where 
    name ilike concat('%', $1, '%') or
    description ilike concat('%', $1, '%') or
    format ilike concat('%', $1, '%') 
order by 
    case 
        when name ilike concat($1, '%') then 1
        when name ilike concat('%', $1, '%') then 2
        else 3
    end,
    created_at desc
limit $2 offset $3;

-- name: GetDatasetsByIds :many
select * from datasets
where id = any($1::uuid[]);

-- name: UpdateDatasetColumns :one
update datasets
set columns = $1
where id = $2
returning *;

-- You might also want these additional queries:

-- name: UpdateDatasetStats :one
update datasets
set 
    row_count = $1,
    size = $2
where id = $3
returning *;

-- name: UpdateDatasetPath :one
update datasets
set file_path = $1
where id = $2
returning *;

