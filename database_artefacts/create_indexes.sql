-- 5. INDEX CREATION (ScaNN)
-- ===================================================================================
-- Index 1: Text Description Index
-- Uses Cosine Distance for semantic similarity.
CREATE INDEX idx_scann_property_desc ON property_listings
USING scann (description_embedding)
WITH (
    -- 'auto' mode requires ~10k rows. For this demo, we force MANUAL mode.
    mode = 'MANUAL',
    num_leaves = 1,     -- 1 partition is optimal for < 1000 rows.
    quantizer = 'SQ8'   -- Standard quantization for balance of speed/accuracy.
);

-- Index 2: Visual Search Index
 CREATE INDEX idx_scann_image_search ON property_listings
 USING scann (image_embedding)
 WITH (
    mode = 'MANUAL',
    num_leaves = 1,
    quantizer = 'SQ8'
);
