CREATE INDEX {{sql.if_index_not_exists}} idx_word_word_id
  ON word USING BTREE (word_id) {{db.tablespace.search_index}};
