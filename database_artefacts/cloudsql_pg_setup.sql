/*
===================================================================================
CLOUD SQL FOR POSTGRESQL: DATABASE & SCHEMA BOOTSTRAP
===================================================================================
*/

-- 1. EXTENSION MANAGEMENT
CREATE EXTENSION IF NOT EXISTS vector CASCADE;

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

-- 3. INDEX CREATION (HNSW)
-- Note: Run this AFTER data is loaded for best performance.
-- CREATE INDEX property_listings_desc_idx ON property_listings USING hnsw (description_embedding vector_cosine_ops);

-- 4. DATA AGENT PREREQUISITES
-- Grant permissions to the IAM user (or public for demo purposes)
GRANT ALL ON SCHEMA public TO public;

-- 5. MODEL ALIASING (Vertex AI Integration)
CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;

CALL google_ml.create_model(
  model_id => 'property_text_embedding_model',
  provider => 'google',
  saved_model_path => 'gemini-embedding-001'
);
