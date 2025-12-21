-- scripts/delete_tables.sql
-- Drops all tables in the correct order using CASCADE to handle foreign key dependencies.

DROP TABLE IF EXISTS task CASCADE;
DROP TABLE IF EXISTS planning CASCADE;
DROP TABLE IF EXISTS planning_metadata_field CASCADE;
DROP TABLE IF EXISTS planning_template CASCADE;
DROP TABLE IF EXISTS question CASCADE;
DROP TABLE IF EXISTS form CASCADE;
DROP TABLE IF EXISTS users CASCADE;