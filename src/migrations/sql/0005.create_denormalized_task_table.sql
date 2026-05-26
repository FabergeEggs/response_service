-- depends: 0004.create_denormalized_post_table
CREATE TABLE IF NOT EXISTS
    denormalized_task (
        id UUID PRIMARY KEY,
        project_id UUID,
        project_status project_status NOT NULL DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX idx_denormalized_task_project_id ON denormalized_task (project_id);
