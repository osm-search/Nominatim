DROP TABLE IF EXISTS word_frequencies;
CREATE TABLE word_frequencies AS
 SELECT unnest(name_vector) as id, count(*) FROM search_name GROUP BY id;

CREATE INDEX idx_word_frequencies ON word_frequencies(id);

UPDATE word SET search_name_count = count
  FROM word_frequencies
 WHERE word_token like ' %' and word_id = id;

DROP TABLE word_frequencies;
