-- Extensões PostgreSQL necessárias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- busca por similaridade de texto
CREATE EXTENSION IF NOT EXISTS unaccent;  -- busca sem acento
