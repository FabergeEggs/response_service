-- depends: 0006.drop_denormalized_user_avatar_url
-- depends: 0004.create_denormalized_post_table

ALTER TABLE comments DROP CONSTRAINT IF EXISTS comments_post_id_fkey;

DELETE FROM comments
WHERE post_id IS NOT NULL
  AND post_id NOT IN (SELECT id FROM denormalized_post);

ALTER TABLE comments
    ADD CONSTRAINT comments_post_id_fkey
    FOREIGN KEY (post_id) REFERENCES denormalized_post (id) ON DELETE CASCADE;
