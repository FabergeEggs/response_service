-- depends: 0005.create_denormalized_task_table
ALTER TABLE denormalized_user DROP COLUMN IF EXISTS avatar_url;
