/*
===================================================================================
CLOUD SPANNER (POSTGRESQL DIALECT): DATABASE & SCHEMA BOOTSTRAP
===================================================================================
*/

-- 1. TABLE CREATION
DROP TABLE IF EXISTS user_prompt_history;

CREATE TABLE public.user_prompt_history (
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_prompt text,
    prompt_embedded vector(3072),
    query_template_used boolean,
    query_template_id integer,
    query_explanation text
);

DROP TABLE IF EXISTS property_listings;

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
    description_embedding vector(3072),
    image_embedding vector(1408) 
);

-- Note: Spanner vector search uses exact nearest neighbor or specific vector indexes.
-- CREATE INDEX property_listings_desc_idx ON property_listings USING vector_index (description_embedding) OPTIONS (distance_type='COSINE');
