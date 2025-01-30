-- name: CreateDataset :one
insert into datasets (
    name,
    description,
    row_count,
    columns
) values ($1, $2, $3, $4)
returning *;

-- name: GetDataset :one
select * from datasets where id = $1;

-- name: UpdateDataset :one
update datasets
set 
    name = coalesce($1, name),
    description = coalesce($2, description),
    row_count = coalesce($3, row_count),
    columns = coalesce($4, columns)
where id = $5
returning *;

-- name: DeleteDataset :exec
delete from datasets where id = $1;

-- Advanced Dataset Queries
-- name: ListDatasets :many
select * from datasets
order by created_at desc
limit $1 offset $2;

-- name: SearchDatasets :many
select * from datasets
where 
    name ilike concat('%', $1, '%') or
    description ilike concat('%', $1, '%')
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
