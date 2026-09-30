-- CedarStone Phase 9 production-schema alignment
-- Apply only if migrating the demo schema to PostgreSQL/Supabase.

ALTER TABLE communications
ADD COLUMN IF NOT EXISTS message text;

-- Production implementations should additionally enforce role-based access
-- with authenticated user profiles and Row Level Security policies.
