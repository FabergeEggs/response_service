-- depends:
CREATE TABLE IF NOT EXISTS
    denormalized_user (
        id UUID PRIMARY KEY,
        name VARCHAR(255) NOT NULL
    );
