-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS search;
USE search;

-- Drop existing tables to recreate them with the correct schema
DROP TABLE IF EXISTS property_description_embeddings;
DROP TABLE IF EXISTS property_image_embeddings;
DROP TABLE IF EXISTS property_listings;
DROP TABLE IF EXISTS user_prompt_history;

-- Create the property_listings table
CREATE TABLE IF NOT EXISTS property_listings (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    bedrooms INT,
    city VARCHAR(100),
    country VARCHAR(100),
    canton VARCHAR(100),
    image_gcs_uri VARCHAR(255)
);

-- COLUMN METADATA COMMENTS (Gemini Context Enrichment)
ALTER TABLE property_listings MODIFY COLUMN bedrooms INT COMMENT '<gemini>Examples: [\'4\', \'6\', \'3\'] | Distinct Values: 7 | Null Count: 0 |</gemini>';
ALTER TABLE property_listings MODIFY COLUMN canton VARCHAR(100) COMMENT '<gemini>Examples: [\'Solothurn\', \'Ticino\', \'Zug\'] | Distinct Values: 27 | Null Count: 0 |</gemini>';
ALTER TABLE property_listings MODIFY COLUMN city VARCHAR(100) COMMENT '<gemini>Examples: [\'Stans\', \'Altdorf\', \'Kilchberg\'] | Distinct Values: 89 | Null Count: 0 |</gemini>';
ALTER TABLE property_listings MODIFY COLUMN country VARCHAR(100) COMMENT '<gemini>Examples: [\'Switzerland\'] | Distinct Values: 1 | Null Count: 0 |</gemini>';
ALTER TABLE property_listings MODIFY COLUMN description TEXT COMMENT '<gemini>Examples: [\'The central rail crossroad of Switzerland. Reach anywhere fast. Modern functional apartment.\', \'Cozy retreat for weekend getaways or permanent living.\'] | Distinct Values: 250 | Null Count: 0 |</gemini>';
ALTER TABLE property_listings MODIFY COLUMN id VARCHAR(50) COMMENT '<gemini>Examples: [\'75\', \'247\', \'13\'] | Distinct Values: 250 | Null Count: 0 |</gemini>';
ALTER TABLE property_listings MODIFY COLUMN image_gcs_uri VARCHAR(255) COMMENT '<gemini>Examples: [\'https://storage.googleapis.com/property-images-data-agent-ai-powered-search-alloydb-1542/listings/10.jpg\'] | Distinct Values: 250 | Null Count: 0 |</gemini>';
ALTER TABLE property_listings MODIFY COLUMN price DECIMAL(10, 2) COMMENT '<gemini>Examples: [\'11878.00\', \'4869.00\', \'2792.00\'] | Distinct Values: 189 | Null Count: 0 |</gemini>';
ALTER TABLE property_listings MODIFY COLUMN title VARCHAR(255) COMMENT '<gemini>Examples: [\'Rustic Studio in Landquart\', \'Renovated Villa in Herisau\', \'Quiet Home in Appenzell\'] | Distinct Values: 248 | Null Count: 0 |</gemini>';

-- Create FULLTEXT indexes on city and canton to support fuzzy MATCH AGAINST Value Searches
ALTER TABLE property_listings ADD FULLTEXT INDEX property_listings_city_ft_idx (city);
ALTER TABLE property_listings ADD FULLTEXT INDEX property_listings_canton_ft_idx (canton);


-- Create the property_description_embeddings table
CREATE TABLE IF NOT EXISTS property_description_embeddings (
    property_id VARCHAR(50) PRIMARY KEY,
    description_embedding VECTOR(3072) USING VARBINARY,
    FOREIGN KEY (property_id) REFERENCES property_listings(id) ON DELETE CASCADE
);

-- Create the property_image_embeddings table
CREATE TABLE IF NOT EXISTS property_image_embeddings (
    property_id VARCHAR(50) PRIMARY KEY,
    image_embedding VECTOR(1408) USING VARBINARY,
    FOREIGN KEY (property_id) REFERENCES property_listings(id) ON DELETE CASCADE
);

-- Create the user_prompt_history table
CREATE TABLE IF NOT EXISTS user_prompt_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_prompt TEXT NOT NULL,
    query_template_used BOOLEAN DEFAULT FALSE,
    query_template_id INT,
    query_explanation TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions to the MySQL service account
-- Note: In Cloud SQL MySQL, IAM users are created without passwords
-- and authenticate using tokens.
-- The user 'search-backend-sa' should be created by Terraform, but we grant privileges here.
-- We use a wildcard host '%' as the connection might come from different IPs.
GRANT ALL PRIVILEGES ON search.* TO 'search-backend-sa'@'%';
GRANT SELECT ON mysql.* TO 'search-backend-sa'@'%';
GRANT EXECUTE ON mysql.* TO 'search-backend-sa'@'%';

-- Grant permissions to the developer user for Cloud SQL Studio access
GRANT ALL PRIVILEGES ON search.* TO '{DEVELOPER_USER}'@'%';
GRANT SELECT ON mysql.* TO '{DEVELOPER_USER}'@'%';
GRANT EXECUTE ON mysql.* TO '{DEVELOPER_USER}'@'%';

FLUSH PRIVILEGES;

-- Create a custom input transform function for the multimodal embedding model
-- The multimodal model expects the input text to be in a "text" field, not "content"
DROP FUNCTION IF EXISTS search.cloudsql_ml_multimodal_embedding_input_transform;

DELIMITER //
CREATE FUNCTION search.cloudsql_ml_multimodal_embedding_input_transform(model_id VARCHAR(255), text_input TEXT)
RETURNS JSON
DETERMINISTIC
BEGIN
  RETURN JSON_OBJECT('instances', JSON_ARRAY(JSON_OBJECT('text', text_input)));
END //
DELIMITER ;

-- Create a custom output transform function for the multimodal embedding model
-- The multimodal model returns the embedding in a "textEmbedding" field
DROP FUNCTION IF EXISTS search.cloudsql_ml_multimodal_embedding_output_transform;

DELIMITER //
CREATE FUNCTION search.cloudsql_ml_multimodal_embedding_output_transform(model_id VARCHAR(255), response_json JSON)
RETURNS BLOB
DETERMINISTIC
BEGIN
  RETURN STRING_TO_VECTOR(
         JSON_EXTRACT(
              response_json,
              '$.predictions[0].textEmbedding'
          )
    );
END //
DELIMITER ;

-- Drop the existing model registration if it exists
-- We use a stored procedure to handle the error if the model is not registered yet
DELIMITER //
CREATE PROCEDURE DropModelIfExists()
BEGIN
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END;
    CALL mysql.ml_drop_model_registration('multimodalembedding@001');
END //
DELIMITER ;

CALL DropModelIfExists();
DROP PROCEDURE DropModelIfExists;

-- Register the multimodal embedding model
CALL mysql.ml_create_model_registration(
    'multimodalembedding@001',
    'publishers/google/models/multimodalembedding@001',
    'google',
    'text_embedding',
    'multimodalembedding@001',
    'AUTH_TYPE_CLOUDSQL_SERVICE_AGENT_IAM',
    NULL,
    'search.cloudsql_ml_multimodal_embedding_input_transform',
    'search.cloudsql_ml_multimodal_embedding_output_transform',
    NULL
);
