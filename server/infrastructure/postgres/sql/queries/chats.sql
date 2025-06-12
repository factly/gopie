-- name: ListChatsByUser :many
select * from chats
where created_by = $1
order by updated_at desc
limit $2 offset $3;

-- name: CountChatsByUser :one
select count(*) from chats
where created_by = $1;

-- name: CreateChat :one
insert into chats (
  title,
  created_by
) values (
  $1, $2
)
returning *;

-- name: UpdateChatTitle :one
update chats
set title = $2
where id = $1
and created_by = $3
returning *;

-- name: DeleteChat :exec
delete from chats
where id = $1
and created_by = $2;

-- name: GetChatMessages :many
select * from chat_messages
where chat_id = $1
order by created_at asc;

-- name: CreateChatMessage :one
insert into chat_messages (
  chat_id,
  choices,
  object,
  model,
  key
) values (
  $1, $2, $3, $4, $5
)
returning *;

-- name: UpdateChatMessage :one
update chat_messages
set choices = $2
where id = $1
and chat_id = $3
returning *;

-- name: GetChatWithMessages :many
select 
  c.*,
  m.id as message_id,
  m.choices,
  m.object,
  m.model,
  m.created_at as message_created_at
from chats c
left join chat_messages m on c.id = m.chat_id
where c.id = $1
order by m.created_at asc;

-- name: GetChatById :one
select * from chats
where id = $1
and created_by = $2;

