CREATE INDEX property_listings_desc_idx ON property_listings USING hnsw ((description_embedding::halfvec(3072)) halfvec_cosine_ops);
CREATE INDEX property_listings_img_idx ON property_listings USING hnsw (image_embedding vector_cosine_ops);
