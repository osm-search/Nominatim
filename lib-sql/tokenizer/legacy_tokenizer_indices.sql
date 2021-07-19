CREATE INDEX IF NOT EXISTS idx_word_word_id
  ON word USING BTREE (word_id) {{db.tablespace.search_index}};
