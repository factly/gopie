-- name: CreateDataset :one
insert into datasets (
    name,
    description,
    row_count,
    size,
    file_path,
    columns,
    alias,
    created_by,
    updated_by,
    org_id,
    custom_prompt
) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
returning *;

-- name: GetDataset :one
select * from datasets where id = $1 and org_id = $2;

-- name: UpdateDataset :one
update datasets
set
    description = coalesce($1, description),
    row_count = coalesce($2, row_count),
    size = coalesce($3, size),
    file_path = coalesce($4, file_path),
    columns = coalesce($5, columns),
    alias = coalesce($6, alias),
    updated_by = coalesce($7, updated_by),
    custom_prompt = coalesce($8, custom_prompt)
where id = $9 and org_id = $10
returning *;

-- name: DeleteDataset :exec
delete from datasets where id = $1 and org_id = $2;

-- name: SearchDatasets :many
select * from datasets
where
    org_id = $1 and
    (name ilike concat('%', $2, '%') or
    description ilike concat('%', $2, '%') or
    alias ilike concat('%', $2, '%'))
order by
    case
        when alias ilike concat($2, '%') then 1
        when name ilike concat($2, '%') then 2
        when name ilike concat('%', $2, '%') then 3
        else 4
    end,
    created_at desc
limit $3 offset $4;

-- name: GetDatasetByName :one
select * from datasets where name = $1 and org_id = $2;

-- name: GetDatasetByID :one
select * from datasets where id = $1;

-- name: ListAllDatasets :many
select * from datasets;
