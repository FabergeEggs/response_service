CREATE TYPE project_status AS ENUM('ACTIVE', 'FINISHED', 'DELETED');

CREATE TABLE IF NOT EXISTS
    denormalized_post (
        id UUID PRIMARY KEY,
        project_id UUID,
        project_status project_status NOT NULL DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX idx_denormalized_post_project_id ON denormalized_post (project_id);
