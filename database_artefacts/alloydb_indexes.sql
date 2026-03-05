CREATE INDEX property_listings_desc_idx ON property_listings USING scann (description_embedding) WITH (num_leaves=10);
CREATE INDEX property_listings_img_idx ON property_listings USING scann (image_embedding) WITH (num_leaves=10);
