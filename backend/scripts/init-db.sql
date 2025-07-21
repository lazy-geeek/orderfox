-- Initialize OrderFox database
-- This script runs when the PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The tables will be created by SQLModel/Alembic migrations
-- This script is mainly for setting up extensions and basic configuration

-- Set timezone
SET timezone = 'UTC';

-- Log initialization
SELECT 'OrderFox database initialized' AS status;