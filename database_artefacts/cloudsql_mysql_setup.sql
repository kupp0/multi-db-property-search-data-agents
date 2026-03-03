/*
===================================================================================
CLOUD SQL FOR MYSQL: DATABASE & SCHEMA BOOTSTRAP
===================================================================================
*/

-- 1. TABLE CREATION
DROP TABLE IF EXISTS user_prompt_history;

CREATE TABLE user_prompt_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_prompt TEXT,
    prompt_embedded VECTOR(3072),
    query_template_used BOOLEAN,
    query_template_id INT,
    query_explanation TEXT
);

DROP TABLE IF EXISTS property_listings;

CREATE TABLE property_listings (
    id INT AUTO_INCREMENT PRIMARY KEY,
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

-- 3. INDEX CREATION
-- Note: MySQL vector indexes (if supported in the specific version) can be added here.
-- ALTER TABLE property_listings ADD VECTOR INDEX (description_embedding);

-- 4. DATA AGENT PREREQUISITES
-- Grant permissions to the IAM user (replace IAM_USERNAME with the actual service account email)
-- GRANT ALL PRIVILEGES ON * TO "IAM_USERNAME";
