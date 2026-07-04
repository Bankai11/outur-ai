-- =============================================================================
-- Outur AI — Database Initialisation Script
-- =============================================================================
-- This script is executed once when the PostgreSQL container first starts
-- (mounted at /docker-entrypoint-initdb.d/init.sql).
--
-- Purpose: Set up database-level configuration that Alembic cannot manage.
-- Alembic handles all table creation via migrations — do NOT create tables here.
-- =============================================================================

-- Enable UUID extension (required for uuid_generate_v4() if used server-side)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for fast fuzzy text search (used for company/lead name search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable citext for case-insensitive text columns (email addresses, domains)
CREATE EXTENSION IF NOT EXISTS citext;

-- Set the timezone for this database
ALTER DATABASE outur_ai SET timezone TO 'UTC';

-- Log that initialisation completed
DO $$
BEGIN
  RAISE NOTICE 'Outur AI database initialised with extensions: uuid-ossp, pg_trgm, citext';
END $$;
