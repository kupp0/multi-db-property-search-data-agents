USE search;

-- Create vector indexes for similarity search
-- Note: Cloud SQL for MySQL requires at least 1000 rows to create a vector index.
-- If you have fewer rows, this statement will fail.

-- Index for description embeddings (768 dimensions)
CREATE VECTOR INDEX idx_description_embedding ON property_description_embeddings(description_embedding) USING SCANN DISTANCE_MEASURE = COSINE;

-- Index for image embeddings (1408 dimensions)
CREATE VECTOR INDEX idx_image_embedding ON property_image_embeddings(image_embedding) USING SCANN DISTANCE_MEASURE = COSINE;
