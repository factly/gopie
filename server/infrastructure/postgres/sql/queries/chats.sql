-- Chat Operations
-- name: CreateChat :one
insert into chats (
    name,
    dataset_id,
    created_by
) values ($1, $2, $3)
returning *;

-- name: DeleteChat :exec
delete from chats where id = $1;

-- name: GetChat :one
select 
    c.*,
    d.name as dataset_name,
    (select count(*) from chat_messages where chat_id = c.id) as message_count
from chats c
join datasets d on c.dataset_id = d.id
where c.id = $1;

-- name: ListUserChats :many
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

-- name: UpdateChat :one
update chats
set 
    name = coalesce($1, name)
where id = $2
returning *;

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

-- Chat Messages Operations
-- name: CreateChatMessage :one
insert into chat_messages (
    chat_id,
    content,
    role,
    created_at
) values ($1, $2, $3, $4)
returning *;

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
delete from chat_messages 
where id = $1 and chat_id = $2;
