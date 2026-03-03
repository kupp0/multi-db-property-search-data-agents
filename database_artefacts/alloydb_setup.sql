/*
===================================================================================
ALLOYDB AI: DATABASE & SCHEMA BOOTSTRAP
===================================================================================
*/

-- 1. EXTENSION MANAGEMENT
CREATE EXTENSION IF NOT EXISTS vector CASCADE;
CREATE EXTENSION IF NOT EXISTS alloydb_scann CASCADE;

-- 2. TABLE CREATION
DROP TABLE IF EXISTS user_prompt_history CASCADE;

CREATE TABLE public.user_prompt_history (
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_prompt text,
    prompt_embedded public.vector(3072),
    query_template_used boolean,
    query_template_id integer,
    query_explanation text
);

DROP TABLE IF EXISTS property_listings CASCADE;

CREATE TABLE property_listings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(12, 2) NOT NULL,
    bedrooms INT,
    city VARCHAR(100),
    image_gcs_uri TEXT,
    country VARCHAR(100) DEFAULT 'Switzerland',
    canton VARCHAR(100),
    -- Embeddings are generated externally and inserted directly
    description_embedding VECTOR(3072),
    image_embedding VECTOR(1408) 
);

-- 3. INDEX CREATION (ScaNN)
-- Note: Run this AFTER data is loaded for best performance, but defined here for completeness.
-- CREATE INDEX property_listings_desc_idx ON property_listings USING scann (description_embedding) WITH (num_leaves=10);
