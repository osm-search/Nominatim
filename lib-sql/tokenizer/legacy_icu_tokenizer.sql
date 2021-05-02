-- Get tokens used for searching the given place.
--
-- These are the tokens that will be saved in the search_name table.
CREATE OR REPLACE FUNCTION token_get_name_search_tokens(info JSONB)
  RETURNS INTEGER[]
AS $$
  SELECT (info->>'names')::INTEGER[]
$$ LANGUAGE SQL IMMUTABLE STRICT;


-- Get tokens for matching the place name against others.
--
-- This should usually be restricted to full name tokens.
CREATE OR REPLACE FUNCTION token_get_name_match_tokens(info JSONB)
  RETURNS INTEGER[]
AS $$
  SELECT (info->>'names')::INTEGER[]
$$ LANGUAGE SQL IMMUTABLE STRICT;


-- Return the housenumber tokens applicable for the place.
CREATE OR REPLACE FUNCTION token_get_housenumber_search_tokens(info JSONB)
  RETURNS INTEGER[]
AS $$
  SELECT (info->>'hnr_tokens')::INTEGER[]
$$ LANGUAGE SQL IMMUTABLE STRICT;


-- Return the housenumber in the form that it can be matched during search.
CREATE OR REPLACE FUNCTION token_normalized_housenumber(info JSONB)
  RETURNS TEXT
AS $$
  SELECT info->>'hnr';
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_addr_street_match_tokens(info JSONB)
  RETURNS INTEGER[]
AS $$
  SELECT (info->>'street')::INTEGER[]
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_addr_place_match_tokens(info JSONB)
  RETURNS INTEGER[]
AS $$
  SELECT (info->>'place_match')::INTEGER[]
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_addr_place_search_tokens(info JSONB)
  RETURNS INTEGER[]
AS $$
  SELECT (info->>'place_search')::INTEGER[]
$$ LANGUAGE SQL IMMUTABLE STRICT;


DROP TYPE IF EXISTS token_addresstoken CASCADE;
CREATE TYPE token_addresstoken AS (
  key TEXT,
  match_tokens INT[],
  search_tokens INT[]
);

CREATE OR REPLACE FUNCTION token_get_address_tokens(info JSONB)
  RETURNS SETOF token_addresstoken
AS $$
  SELECT key, (value->>1)::int[] as match_tokens,
         (value->>0)::int[] as search_tokens
  FROM jsonb_each(info->'addr');
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_normalized_postcode(postcode TEXT)
  RETURNS TEXT
AS $$
  SELECT CASE WHEN postcode SIMILAR TO '%(,|;)%' THEN NULL ELSE upper(trim(postcode))END;
$$ LANGUAGE SQL IMMUTABLE STRICT;


-- Return token info that should be saved permanently in the database.
CREATE OR REPLACE FUNCTION token_strip_info(info JSONB)
  RETURNS JSONB
AS $$
  SELECT NULL::JSONB;
$$ LANGUAGE SQL IMMUTABLE STRICT;

--------------- private functions ----------------------------------------------

CREATE OR REPLACE FUNCTION getorcreate_term_id(lookup_term TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  return_id INTEGER;
  term_count INTEGER;
BEGIN
  SELECT min(word_id), max(search_name_count) INTO return_id, term_count
    FROM word WHERE word_token = lookup_term and class is null and type is null;

  IF return_id IS NULL THEN
    return_id := nextval('seq_word');
    INSERT INTO word (word_id, word_token, search_name_count)
      VALUES (return_id, lookup_term, 0);
  ELSEIF left(lookup_term, 1) = ' ' and term_count > {{ max_word_freq }} THEN
    return_id := 0;
  END IF;

  RETURN return_id;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION getorcreate_hnr_id(lookup_term TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  return_id INTEGER;
BEGIN
  SELECT min(word_id) INTO return_id
    FROM word
    WHERE word_token = '  '  || lookup_term
          and class = 'place' and type = 'house';

  IF return_id IS NULL THEN
    return_id := nextval('seq_word');
    INSERT INTO word (word_id, word_token, class, type, search_name_count)
      VALUES (return_id, ' ' || lookup_term, 'place', 'house', 0);
  END IF;

  RETURN return_id;
END;
$$
LANGUAGE plpgsql;
