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
    description = coalesce($1, description),
    format = coalesce($2, format),
    row_count = coalesce($3, row_count),
    size = coalesce($4, size),
    file_path = coalesce($5, file_path),
    columns = coalesce($6, columns)
where id = $7
returning *;

-- name: DeleteDataset :exec
delete from datasets where id = $1;

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

-- name: GetDatasetByName :one
select * from datasets where name = $1;
