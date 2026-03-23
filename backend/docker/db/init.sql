-- Executed by the official postgres image on the first start of a fresh volume.
-- Keep this script idempotent.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS citext;

