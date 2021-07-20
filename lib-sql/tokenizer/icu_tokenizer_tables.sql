DROP TABLE IF EXISTS word;
CREATE TABLE word_icu (
  word_id INTEGER,
  word_token text NOT NULL,
  type text NOT NULL,
  info jsonb
) {{db.tablespace.search_data}};

CREATE INDEX idx_word_word_token ON word
    USING BTREE (word_token) {{db.tablespace.search_index}};
-- Used when updating country names from the boundary relation.
CREATE INDEX idx_word_country_names ON word
    USING btree((info->>'cc')) {{db.tablespace.address_index}}
    WHERE type = 'C';
-- Used when inserting new postcodes on updates.
CREATE INDEX idx_word_postcodes ON word
    USING btree((info->>'postcode')) {{db.tablespace.address_index}}
    WHERE type = 'P'
GRANT SELECT ON word TO "{{config.DATABASE_WEBUSER}}";

DROP SEQUENCE IF EXISTS seq_word;
CREATE SEQUENCE seq_word start 1;
GRANT SELECT ON seq_word to "{{config.DATABASE_WEBUSER}}";
