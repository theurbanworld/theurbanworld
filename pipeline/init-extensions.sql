-- Initialize H3 extensions in the urbanworld database
-- This script runs automatically on first container startup
-- Note: PostGIS is already created by the base image's 10_postgis.sh

\c urbanworld

CREATE EXTENSION IF NOT EXISTS h3 CASCADE;
CREATE EXTENSION IF NOT EXISTS h3_postgis CASCADE;
