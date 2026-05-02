-- depends: 0003.create_denormalized_user_table
-- depends: 0004.create_denormalized_post_table
CREATE TABLE
    comments (
        id UUID PRIMARY KEY,
        user_id UUID,
        FOREIGN KEY (user_id) REFERENCES denormalized_user (id),
        post_id UUID,
        FOREIGN KEY (post_id) REFERENCES denormalized_post (id),
        text VARCHAR(5000) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX idx_comments_post_id ON comments (post_id);