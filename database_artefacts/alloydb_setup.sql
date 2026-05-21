/*
===================================================================================
ALLOYDB AI: DATABASE & SCHEMA BOOTSTRAP
===================================================================================
*/

-- 0. DATABASE CREATION
SELECT 'CREATE DATABASE search'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'search')\gexec

\c search

-- 1. EXTENSION MANAGEMENT
CREATE EXTENSION IF NOT EXISTS vector CASCADE;
CREATE EXTENSION IF NOT EXISTS alloydb_scann CASCADE;

-- 2. TABLE CREATION
DROP TABLE IF EXISTS user_prompt_history CASCADE;

CREATE TABLE public.user_prompt_history (
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_prompt text,
    prompt_embedded vector(3072),
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
    description_embedding VECTOR(3072) ,
    image_embedding VECTOR(1408) 
);

-- 2.1 COLUMN METADATA COMMENTS (Gemini Context Enrichment)
COMMENT ON COLUMN property_listings.bedrooms IS '<gemini>Examples: [''4'', ''6'', ''3''] | Distinct Values: 7 | Null Count: 0 |</gemini>';
COMMENT ON COLUMN property_listings.canton IS '<gemini>Examples: [''Solothurn'', ''Ticino'', ''Zug''] | Distinct Values: 27 | Null Count: 0 |</gemini>';
COMMENT ON COLUMN property_listings.city IS '<gemini>Examples: [''Stans'', ''Altdorf'', ''Kilchberg''] | Distinct Values: 89 | Null Count: 0 |</gemini>';
COMMENT ON COLUMN property_listings.country IS '<gemini>Examples: [''Switzerland''] | Distinct Values: 1 | Null Count: 0 |</gemini>';
COMMENT ON COLUMN property_listings.description IS '<gemini>Examples: [''The central rail crossroad of Switzerland. Reach anywhere fast. Modern functional apartment.'', ''Cozy retreat for weekend getaways or permanent living.''] | Distinct Values: 250 | Null Count: 0 |</gemini>';
COMMENT ON COLUMN property_listings.id IS '<gemini>Examples: [''75'', ''247'', ''13''] | Distinct Values: 250 | Null Count: 0 |</gemini>';
COMMENT ON COLUMN property_listings.image_gcs_uri IS '<gemini>Examples: [''https://storage.googleapis.com/property-images-data-agent-ai-powered-search-alloydb-1542/listings/10.jpg''] | Distinct Values: 250 | Null Count: 0 |</gemini>';
COMMENT ON COLUMN property_listings.price IS '<gemini>Examples: [''11878.00'', ''4869.00'', ''2792.00''] | Distinct Values: 189 | Null Count: 0 |</gemini>';
COMMENT ON COLUMN property_listings.title IS '<gemini>Examples: [''Rustic Studio in Landquart'', ''Renovated Villa in Herisau'', ''Quiet Home in Appenzell''] | Distinct Values: 248 | Null Count: 0 |</gemini>';


-- 3. INDEX CREATION (ScaNN). Follow index sql files after data is loaded. 

-- 4. MODEL ALIASING (Vertex AI Integration)
CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;


-- 4.1 Test Text Embeddings in Database Vertex AI integration
SELECT google_ml.embedding(
    model_id => 'gemini-embedding-001',
    content => 'This is the text to embed.'
);
SELECT google_ml.embedding(
    model_id => 'multimodalembedding@001',
    content => 'This is the text to embed.'
);

-- 5. IAM GRANTS
-- Revoke default public access
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM PUBLIC;

-- Grant access to the service account user
GRANT USAGE ON SCHEMA public TO "search-backend-sa@{PROJECT_ID}.iam";
GRANT SELECT ON TABLE property_listings TO "search-backend-sa@{PROJECT_ID}.iam";
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE user_prompt_history TO "search-backend-sa@{PROJECT_ID}.iam";
GRANT USAGE, SELECT ON SEQUENCE user_prompt_history_id_seq TO "search-backend-sa@{PROJECT_ID}.iam";
