-- 1. Create a copy of the property_listings table for testing
CREATE TABLE property_listings_repro (
  id INT64,
  title STRING(255) NOT NULL,
  description STRING(MAX),
  price NUMERIC NOT NULL,
  bedrooms INT64,
  city STRING(100),
  image_gcs_uri STRING(MAX),
  country STRING(100),
  canton STRING(100),
  description_embedding ARRAY<FLOAT32>(vector_length=>3072),
  image_embedding ARRAY<FLOAT32>(vector_length=>1408)
) PRIMARY KEY (id);

-- 2. Register the MultiEmbedding model using FLOAT32
CREATE OR REPLACE MODEL MultiEmbedding
INPUT(
  text STRING(MAX) OPTIONS (required = false),
  image STRUCT<gcsUri STRING(MAX)> OPTIONS (required = false)
)
OUTPUT(
  imageEmbedding ARRAY<FLOAT32> OPTIONS (required = false),
  textEmbedding ARRAY<FLOAT32> OPTIONS (required = false)
)
REMOTE OPTIONS (
  endpoint = '//aiplatform.googleapis.com/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/multimodalembedding@001'
);

-- Note: You will need to copy data from property_listings to property_listings_repro
-- You can run the following INSERT statement to copy and cast the embeddings:
-- INSERT INTO property_listings_repro (id, title, description, price, bedrooms, city, image_gcs_uri, country, canton, description_embedding, image_embedding)
-- SELECT 
--   id, 
--   title, 
--   description, 
--   price, 
--   bedrooms, 
--   city, 
--   image_gcs_uri, 
--   country, 
--   canton, 
--   ARRAY(SELECT CAST(x AS FLOAT32) FROM UNNEST(description_embedding) AS x),
--   ARRAY(SELECT CAST(x AS FLOAT32) FROM UNNEST(image_embedding) AS x)
-- FROM property_listings;

-- 3. Test Query Template for Text Embedding Search
WITH query_embedding AS (
  SELECT textEmbedding
  FROM ML.PREDICT(MODEL MultiEmbedding, (SELECT 'Lovely wooden cabin' AS text))
)
SELECT
  id,
  title,
  city,
  price,
  COSINE_DISTANCE(
    image_embedding,
    query_embedding.textEmbedding
  ) AS distance
FROM property_listings_repro, query_embedding
ORDER BY distance ASC
LIMIT 5;

-- 4. Test Query Template for Image Embedding Search
WITH query_embedding AS (
  SELECT imageEmbedding
  FROM ML.PREDICT(MODEL MultiEmbedding, (SELECT STRUCT('gs://your-bucket-name/sample-image.jpg' AS gcsUri) AS image))
)
SELECT
  id,
  title,
  city,
  price,
  COSINE_DISTANCE(
    image_embedding,
    query_embedding.imageEmbedding
  ) AS distance
FROM property_listings_repro, query_embedding
ORDER BY distance ASC
LIMIT 5;

-- 5. Final Sample Query: Combined Text and Image Embedding Search
WITH QueryEmbeddings AS (
  SELECT 
    (
      -- Get text embedding and cast from FLOAT64 to FLOAT32
      SELECT ARRAY(SELECT CAST(val AS FLOAT32) FROM UNNEST(embeddings.values) AS val) 
      FROM ML.PREDICT(MODEL property_text_embedding_model, (SELECT 'Lovely wooden cabin' AS content))
    ) AS text_emb, 
    (
      -- Get multimodal text embedding (already FLOAT32 from our new model)
      SELECT textEmbedding 
      FROM ML.PREDICT(MODEL MultiEmbedding, (SELECT 'Lovely wooden cabin' AS text))
    ) AS image_emb
) 
SELECT 
  p.image_gcs_uri, 
  p.id, 
  p.title, 
  p.description, 
  p.bedrooms, 
  p.price, 
  p.city, 
  p.country, 
  p.canton, 
  (0.6 * (1 - COSINE_DISTANCE(p.description_embedding, q.text_emb)) + 
   0.4 * (1 - COSINE_DISTANCE(p.image_embedding, q.image_emb))) AS similarity 
FROM property_listings_repro p 
CROSS JOIN QueryEmbeddings q 
ORDER BY similarity DESC 
LIMIT 25;
