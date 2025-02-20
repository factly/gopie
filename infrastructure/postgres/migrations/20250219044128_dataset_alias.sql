-- +goose up
alter table datasets
add column if not exists alias text default null,
add column if not exists created_by text default null,
add column if not exists updated_by text default null;

alter table projects
add column if not exists created_by text default null,
add column if not exists updated_by text default null;

-- +goose down
alter table datasets
drop column if exists updated_by,
drop column if exists created_by,
drop column if exists alias;

alter table projects
drop column if exists updated_by,
drop column if exists created_by;
