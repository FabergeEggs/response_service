-- depends: 0003.create_denormalized_user_table
-- depends: 0005.create_denormalized_task_table
CREATE TYPE response_status AS ENUM('PENDING', 'APPROVED', 'REJECTED');

CREATE TABLE IF NOT EXISTS
    response (
        id UUID PRIMARY KEY,
        user_id UUID,
        FOREIGN KEY (user_id) REFERENCES denormalized_user (id),
        task_id UUID,
        FOREIGN KEY (task_id) REFERENCES denormalized_task (id) ON DELETE CASCADE,
        project_id UUID,
        text VARCHAR(5000) NOT NULL,
        status response_status NOT NULL DEFAULT 'PENDING',
        files TEXT[] NOT NULL DEFAULT '{}'::text[],
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

CREATE INDEX idx_response_task_id ON response (task_id);