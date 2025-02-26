-- name: CreateChat :one
insert into chats (
    name,
    description,
    dataset_id,
    created_by,
    updated_by
) values ($1, $2, $3, $4, $5)
returning *;

-- name: GetChat :one
select 
    c.*,
    d.name as dataset_name,
    (select count(*) from chat_messages where chat_id = c.id) as message_count
from chats c
join datasets d on c.dataset_id = d.id
where c.id = $1;

-- name: UpdateChat :one
update chats
set 
    name = coalesce($1, name),
    description = coalesce($2, description),
    updated_by = coalesce($3, updated_by)
where id = $4
returning *;

-- name: DeleteChat :exec
delete from chats where id = $1;

-- name: ListDatasetChats :many
select 
    c.*,
    (select count(*) from chat_messages where chat_id = c.id) as message_count
from chats c
where c.dataset_id = $1
order by c.updated_at desc
limit $2 offset $3;

-- name: GetDatasetChatsCount :one
select count(*) 
from chats
where dataset_id = $1;

-- name: SearchChats :many
select 
    c.*,
    d.name as dataset_name,
    (select count(*) from chat_messages where chat_id = c.id) as message_count
from chats c
join datasets d on c.dataset_id = d.id
where 
    c.name ilike concat('%', $1, '%') or
    c.description ilike concat('%', $1, '%')
order by 
    case 
        when c.name ilike concat($1, '%') then 1
        when c.name ilike concat('%', $1, '%') then 2
        else 3
    end,
    c.updated_at desc
limit $2 offset $3;

-- name: GetUserChats :many
select 
    c.*,
    d.name as dataset_name,
    (select count(*) from chat_messages where chat_id = c.id) as message_count
from chats c
join datasets d on c.dataset_id = d.id
where c.created_by = $1
order by c.updated_at desc
limit $2 offset $3;

-- name: GetUserChatsCount :one
select count(*) 
from chats
where created_by = $1;

-- Chat Messages Operations
-- name: CreateChatMessage :one
insert into chat_messages (
    chat_id,
    content,
    role,
    created_by
) values ($1, $2, $3, $4)
returning *;

-- name: GetChatMessage :one
select * from chat_messages where id = $1;

-- name: ListChatMessages :many
select * from chat_messages
where chat_id = $1
order by created_at asc
limit $2 offset $3;

-- name: GetChatMessagesCount :one
select count(*) 
from chat_messages
where chat_id = $1;

-- name: DeleteChatMessage :exec
delete from chat_messages where id = $1;

-- name: DeleteAllChatMessages :exec
delete from chat_messages where chat_id = $1;

-- name: GetLatestChatMessage :one
select * from chat_messages
where chat_id = $1
order by created_at desc
limit 1;
