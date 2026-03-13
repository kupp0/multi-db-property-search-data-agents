# MySQL Implementation Differences vs. Cloud SQL PostgreSQL, AlloyDB, and Spanner

This document outlines the key differences and workarounds required when implementing the property search data agent using **Cloud SQL for MySQL** compared to the other supported database backends (Cloud SQL for PostgreSQL, AlloyDB, and Cloud Spanner).

## Summary Matrix

| Feature | Cloud SQL for MySQL | Cloud SQL PostgreSQL | AlloyDB | Cloud Spanner |
| :--- | :--- | :--- | :--- | :--- |
| **Embeddings Storage** | Separate tables per embedding type (1 vector/table limit) | Direct `vector` columns in main table | Direct `vector` columns in main table | Direct `ARRAY<FLOAT64>` columns in main table |
| **Model Registration** | `mysql.ml_create_model_registration` | `google_ml.create_model` | `google_ml.embedding` (direct usage) | `CREATE OR REPLACE MODEL ... REMOTE OPTIONS` |
| **Transform Functions** | Required (Custom SQL functions) | Required (Custom PL/pgSQL functions) | Not required | Not required |
| **Vector Data Type** | `VECTOR(dim) USING VARBINARY` | `vector(dim)` | `vector(dim)` | `ARRAY<FLOAT64>(vector_length=>dim)` |
| **Index Type** | `SCANN` (Requires ≥ 1000 rows) | `HNSW` or `IVFFlat` | `ScaNN` | Native Vector Index (ScaNN-based) |
| **Required Extensions** | None (Built-in) | `vector`, `google_ml_integration` | `vector`, `alloydb_scann`, `google_ml_integration` | None (Native) |
| **Required DB Flags** | `cloudsql_iam_authentication=on`, `cloudsql_vector=on`, `log_bin_trust_function_creators=on` | `cloudsql.iam_authentication=on`, `google_ml_integration.enable_model_support=on` | `alloydb_ai_nl.enabled=on`, `alloydb.iam_authentication=on`, `google_db_advisor.enable_auto_advisor=on`, `google_ml_integration.enable_ai_query_engine=on`, `parameterized_views.enabled=on`, `scann.enable_zero_knob_index_creation=on` | None |
| **Primary Keys** | `AUTO_INCREMENT` | `SERIAL` or `IDENTITY` | `SERIAL` or `IDENTITY` | `GET_NEXT_SEQUENCE_VALUE` (bit-reversed) |
| **Known Impediments** | 1000 row minimum for index creation; GDA rejects `SET`/`SELECT INTO` workarounds as non-read-only | - | - | `default_batch_size=1` forces row-by-row Vertex AI calls (use CTEs) |
## 1. Embeddings Storage (Tables vs. Columns)

The most significant architectural difference lies in how vector embeddings are stored:

*   **Cloud SQL for MySQL**: Due to current limitations where only one vector embedding can be effectively stored and indexed per table ([Source: Cloud SQL for MySQL Vector Search Limitations](https://docs.cloud.google.com/sql/docs/mysql/vector-search#limitations)), the schema requires **separate tables** for each embedding type. 
    *   `property_listings` (Main table)
    *   `property_description_embeddings` (Foreign key to `property_listings`)
    *   `property_image_embeddings` (Foreign key to `property_listings`)
*   **Cloud SQL PostgreSQL / AlloyDB**: Embeddings are stored as direct `vector` columns within the main `property_listings` table.
*   **Cloud Spanner**: Embeddings are stored as `ARRAY<FLOAT64>` columns directly within the main `property_listings` table.

## 2. Model Registration and Integration

Integrating with Vertex AI models for generating embeddings directly from the database requires different approaches:

*   **Cloud SQL for MySQL**: 
    *   Uses the `mysql.ml_create_model_registration` stored procedure.
    *   Requires custom input and output transform functions (e.g., `cloudsql_ml_multimodal_embedding_input_transform`) written in SQL to format the JSON request and parse the response blob for the Vertex AI endpoint.
*   **Cloud SQL PostgreSQL**: 
    *   Uses the `google_ml.create_model` function provided by the `google_ml_integration` extension.
    *   Requires custom PL/pgSQL transform functions for complex multimodal models, as the syntax and JSON handling differ from MySQL.
*   **AlloyDB**:
    *   Uses the `google_ml.embedding` function provided by the `google_ml_integration` extension directly.
    *   Does **not** require custom transform functions for the multimodal model, unlike Cloud SQL PostgreSQL and MySQL.
*   **Cloud Spanner**: 
    *   Uses a declarative `CREATE OR REPLACE MODEL` statement with `REMOTE OPTIONS` pointing directly to the Vertex AI endpoint.
    *   Maps the input/output directly in the model definition without needing separate transform functions.
    *   **Impediment / Workaround**: Currently, the model registry enforces `default_batch_size = 1`. When the model is called in-line within a SQL statement (e.g., for semantic hybrid search), this causes Vertex AI to be called row-by-row, which is highly inefficient. The workaround is to use a Common Table Expression (CTE) to call the model once and then join the result with the main query.

## 3. Vector Data Types

The underlying data types used to store the high-dimensional vectors vary:

*   **Cloud SQL for MySQL**: Uses `VECTOR(dim) USING VARBINARY` (e.g., `VECTOR(3072) USING VARBINARY`).
*   **Cloud SQL PostgreSQL / AlloyDB**: Uses the `vector(dim)` type provided by the `pgvector` extension.
*   **Cloud Spanner**: Uses `ARRAY<FLOAT64>(vector_length=>dim)`.

## 4. Index Generation

Creating indexes for fast similarity search (Approximate Nearest Neighbor - ANN) has different syntax and constraints:

*   **Cloud SQL for MySQL**: 
    *   Uses `CREATE VECTOR INDEX ... USING SCANN DISTANCE_MEASURE = COSINE`.
    *   **Impediment / Workaround**: Cloud SQL for MySQL requires at least **1000 rows** to be present in the table before a vector index can be successfully created ([Source: Cloud SQL for MySQL Vector Search](https://docs.cloud.google.com/sql/docs/mysql/create-manage-vector-indexes#before_you_begin)). If the table has fewer rows, the index creation statement will fail.
*   **Cloud SQL PostgreSQL**: Uses `HNSW` indexes via `pgvector` (e.g., `CREATE INDEX ... USING hnsw`).
*   **AlloyDB**: Uses `ScaNN` indexes via the `alloydb_scann` extension (e.g., `CREATE INDEX ... USING scann`).
*   **Cloud Spanner**: Uses native Spanner vector search indexes, which are also based on the **ScaNN** algorithm (e.g., `CREATE VECTOR INDEX ... OPTIONS (distance_type='COSINE')`).

## 5. Extensions and Database Flags

*   **Cloud SQL for MySQL**: 
    *   Vector and ML features are built-in or enabled via instance flags.
    *   Requires the database flag `cloudsql_iam_authentication = on` to allow the service account to authenticate and use the model registry.
    *   Requires the database flag `cloudsql_vector = on` to enable vector search capabilities.
    *   Requires the database flag `log_bin_trust_function_creators = on`. This is necessary because the custom input/output transform functions (e.g., `cloudsql_ml_multimodal_embedding_input_transform`) required for the model registry are considered custom functions. Without this flag, MySQL restricts the creation of stored functions when binary logging is enabled (which is typical in Cloud SQL for backups/replication) to prevent potential replication issues from non-deterministic functions.
*   **Cloud SQL PostgreSQL**: 
    *   Explicitly requires `CREATE EXTENSION IF NOT EXISTS vector CASCADE;` and `CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;`.
    *   Requires the following database flags (configured via Terraform):
        *   `cloudsql.iam_authentication = on`
        *   `google_ml_integration.enable_model_support = on`
*   **AlloyDB**: 
    *   Explicitly requires `CREATE EXTENSION IF NOT EXISTS vector CASCADE;`, `CREATE EXTENSION IF NOT EXISTS alloydb_scann CASCADE;`, and `CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;`.
    *   Requires the following database flags (configured via Terraform):
        *   `alloydb_ai_nl.enabled = on`
        *   `alloydb.iam_authentication = on`
        *   `google_db_advisor.enable_auto_advisor = on`
        *   `google_ml_integration.enable_ai_query_engine = on`
        *   `parameterized_views.enabled = on`
        *   `scann.enable_zero_knob_index_creation = on`
*   **Cloud Spanner**: Native support; no extensions or specific ML flags required.

## 6. Primary Keys and Sequences

Generating unique IDs for tables like `user_prompt_history` differs:

*   **Cloud SQL for MySQL**: Uses standard `AUTO_INCREMENT`.
*   **Cloud SQL PostgreSQL / AlloyDB**: Uses `SERIAL` or `GENERATED BY DEFAULT AS IDENTITY`.
*   **Cloud Spanner**: Uses `GET_NEXT_SEQUENCE_VALUE(SEQUENCE global_id_sequence)` with a `bit_reversed_positive` sequence

## 7. Hybrid Semantic Search Queries

Implementing hybrid semantic search (combining multiple vector distances, e.g., text and image embeddings) reveals significant differences in query syntax, casting requirements, and how in-line model calls are handled:

### Cloud SQL for MySQL
*   **Syntax**: Uses `approx_distance(column, vector, 'distance_measure=cosine')`. Requires `LEFT JOIN`s for separate embedding tables.
*   **Casting**: No explicit casting required.
*   **In-line Model Calls (Problem & Workaround)**: 
    *   **Issue**: `APPROX_DISTANCE` fails with **Error 9005** if the vector argument is generated dynamically (e.g., via subquery or CTE). It requires a literal or pre-resolved constant.
    *   **Solution**: Store dynamically generated vectors in session variables before the main `SELECT` ([Source: Cloud SQL for MySQL Example Embedding Workflow](https://docs.cloud.google.com/sql/docs/mysql/understand-example-embedding-workflow#run)):
        ```sql
        -- Option 1: SELECT ... INTO
        SELECT mysql.ml_embedding('model', 'text') INTO @my_vector;
        
        -- Option 2: SET
        SET @my_vector = (SELECT mysql.ml_embedding('model', 'text'));
        ```
    *   **GDA Limitation**: While this fixes SQL execution, the Query Data API (GDA) rejects these multi-statement queries (e.g., `SET ...; SELECT ...;`) because they are not strictly read-only:
        ```json
        "queryExecutionError": "Query execution skipped: The generated query does not appear to be a valid read-only SQL statement."
        ```

### Cloud SQL PostgreSQL / AlloyDB
*   **Syntax**: Uses the `<=>` operator for cosine distance (e.g., `description_embedding <=> google_ml.embedding(...)`).
*   **Casting**: The output of `google_ml.embedding()` must be explicitly cast to a vector: `::vector`.
*   **In-line Model Calls**: Functions efficiently when called in-line within the `ORDER BY` clause; the database engine optimizes the call.

### Cloud Spanner
*   **Syntax**: Uses the `COSINE_DISTANCE(column, vector)` function and `ML.PREDICT(MODEL ..., (SELECT ...))` for generating embeddings.
*   **Casting**: Requires explicit casting when unnesting arrays from complex models (e.g., `CAST(val AS FLOAT64) FROM UNNEST(textEmbedding)`).
*   **In-line Model Calls (Problem & Workaround)**: As mentioned in section 2, the model registry enforces `default_batch_size = 1`. If `ML.PREDICT` is used in-line for every row, it triggers row-by-row API calls to Vertex AI.
    *   **Workaround**: Use a Common Table Expression (CTE) to execute `ML.PREDICT` once, and then `CROSS JOIN` or reference that CTE in the main query to calculate the distance.

