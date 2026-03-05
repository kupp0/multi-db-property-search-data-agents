-- 0. CLEANUP
DROP INDEX IF EXISTS property_listings_desc_idx;
DROP INDEX IF EXISTS property_listings_img_idx;
DROP TABLE IF EXISTS user_prompt_history;
DROP TABLE IF EXISTS property_listings;
DROP SEQUENCE IF EXISTS global_id_sequence;

-- 1. SEQUENCES
CREATE SEQUENCE global_id_sequence 
  OPTIONS (sequence_kind='bit_reversed_positive');

-- 2. TABLES
CREATE TABLE user_prompt_history (
  id INT64 DEFAULT (GET_NEXT_SEQUENCE_VALUE(SEQUENCE global_id_sequence)),
  timestamp TIMESTAMP OPTIONS (allow_commit_timestamp=true),
  user_prompt STRING(MAX),
  -- Arrays are defined as ARRAY<TYPE>
  prompt_embedded ARRAY<FLOAT64>(vector_length=>3072),
  query_template_used BOOL,
  query_template_id INT64,
  query_explanation STRING(MAX)
) PRIMARY KEY (id);

CREATE TABLE property_listings (
  id INT64 DEFAULT (GET_NEXT_SEQUENCE_VALUE(SEQUENCE global_id_sequence)),
  title STRING(255) NOT NULL,
  description STRING(MAX),
  price NUMERIC NOT NULL,
  bedrooms INT64,
  city STRING(100),
  image_gcs_uri STRING(MAX),
  country STRING(100) DEFAULT ('Switzerland'),
  canton STRING(100),
  description_embedding ARRAY<FLOAT64>(vector_length=>3072),
  image_embedding ARRAY<FLOAT64>(vector_length=>1408)
) PRIMARY KEY (id);

-- 3. MODEL ALIASING
CREATE OR REPLACE MODEL property_text_embedding_model
  INPUT (content STRING(MAX))
  -- Based on the error, the model returns a direct 'embeddings' object
  OUTPUT (
    embeddings STRUCT<values ARRAY<FLOAT64>>
  )
  REMOTE OPTIONS (
    endpoint = '//aiplatform.googleapis.com/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/gemini-embedding-001'
  );