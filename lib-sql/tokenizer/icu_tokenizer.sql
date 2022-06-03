-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

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


CREATE OR REPLACE FUNCTION token_has_addr_street(info JSONB)
  RETURNS BOOLEAN
AS $$
  SELECT info->>'street' is not null;
$$ LANGUAGE SQL IMMUTABLE;


CREATE OR REPLACE FUNCTION token_has_addr_place(info JSONB)
  RETURNS BOOLEAN
AS $$
  SELECT info->>'place' is not null;
$$ LANGUAGE SQL IMMUTABLE;


CREATE OR REPLACE FUNCTION token_matches_street(info JSONB, street_tokens INTEGER[])
  RETURNS BOOLEAN
AS $$
  SELECT (info->>'street')::INTEGER[] && street_tokens
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_matches_place(info JSONB, place_tokens INTEGER[])
  RETURNS BOOLEAN
AS $$
  SELECT (info->>'place')::INTEGER[] <@ place_tokens
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_addr_place_search_tokens(info JSONB)
  RETURNS INTEGER[]
AS $$
  SELECT (info->>'place')::INTEGER[]
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_get_address_keys(info JSONB)
  RETURNS SETOF TEXT
AS $$
  SELECT * FROM jsonb_object_keys(info->'addr');
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_get_address_search_tokens(info JSONB, key TEXT)
  RETURNS INTEGER[]
AS $$
  SELECT (info->'addr'->>key)::INTEGER[];
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_matches_address(info JSONB, key TEXT, tokens INTEGER[])
  RETURNS BOOLEAN
AS $$
  SELECT (info->'addr'->>key)::INTEGER[] <@ tokens;
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_normalized_postcode(postcode TEXT)
  RETURNS TEXT
AS $$
  SELECT CASE WHEN postcode SIMILAR TO '%(,|;)%' THEN NULL ELSE upper(trim(postcode))END;
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_get_postcode(info JSONB)
  RETURNS TEXT
AS $$
  SELECT info->>'postcode';
$$ LANGUAGE SQL IMMUTABLE STRICT;


-- Return token info that should be saved permanently in the database.
CREATE OR REPLACE FUNCTION token_strip_info(info JSONB)
  RETURNS JSONB
AS $$
  SELECT NULL::JSONB;
$$ LANGUAGE SQL IMMUTABLE STRICT;

--------------- private functions ----------------------------------------------

CREATE OR REPLACE FUNCTION getorcreate_full_word(norm_term TEXT, lookup_terms TEXT[],
                                                 OUT full_token INT,
                                                 OUT partial_tokens INT[])
  AS $$
DECLARE
  partial_terms TEXT[] = '{}'::TEXT[];
  term TEXT;
  term_id INTEGER;
  term_count INTEGER;
BEGIN
  SELECT min(word_id) INTO full_token
    FROM word WHERE word = norm_term and type = 'W';

  IF full_token IS NULL THEN
    full_token := nextval('seq_word');
    INSERT INTO word (word_id, word_token, type, word, info)
      SELECT full_token, lookup_term, 'W', norm_term,
             json_build_object('count', 0)
        FROM unnest(lookup_terms) as lookup_term;
  END IF;

  FOR term IN SELECT unnest(string_to_array(unnest(lookup_terms), ' ')) LOOP
    term := trim(term);
    IF NOT (ARRAY[term] <@ partial_terms) THEN
      partial_terms := partial_terms || term;
    END IF;
  END LOOP;

  partial_tokens := '{}'::INT[];
  FOR term IN SELECT unnest(partial_terms) LOOP
    SELECT min(word_id), max(info->>'count') INTO term_id, term_count
      FROM word WHERE word_token = term and type = 'w';

    IF term_id IS NULL THEN
      term_id := nextval('seq_word');
      term_count := 0;
      INSERT INTO word (word_id, word_token, type, info)
        VALUES (term_id, term, 'w', json_build_object('count', term_count));
    END IF;

    partial_tokens := array_merge(partial_tokens, ARRAY[term_id]);
  END LOOP;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION getorcreate_partial_word(partial TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  token INTEGER;
BEGIN
  SELECT min(word_id) INTO token
    FROM word WHERE word_token = partial and type = 'w';

  IF token IS NULL THEN
    token := nextval('seq_word');
    INSERT INTO word (word_id, word_token, type, info)
        VALUES (token, partial, 'w', json_build_object('count', 0));
  END IF;

  RETURN token;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION getorcreate_hnr_id(lookup_term TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  return_id INTEGER;
BEGIN
  SELECT min(word_id) INTO return_id FROM word
    WHERE word_token = lookup_term and type = 'H';

  IF return_id IS NULL THEN
    return_id := nextval('seq_word');
    INSERT INTO word (word_id, word_token, type)
      VALUES (return_id, lookup_term, 'H');
  END IF;

  RETURN return_id;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION create_analyzed_hnr_id(norm_term TEXT, lookup_terms TEXT[])
  RETURNS INTEGER
  AS $$
DECLARE
  return_id INTEGER;
BEGIN
  SELECT min(word_id) INTO return_id
    FROM word WHERE word = norm_term and type = 'H';

  IF return_id IS NULL THEN
    return_id := nextval('seq_word');
    INSERT INTO word (word_id, word_token, type, word, info)
      SELECT return_id, lookup_term, 'H', norm_term,
             json_build_object('lookup', lookup_terms[1])
        FROM unnest(lookup_terms) as lookup_term;
  END IF;

  RETURN return_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION create_postcode_word(postcode TEXT, lookup_terms TEXT[])
  RETURNS BOOLEAN
  AS $$
DECLARE
  existing INTEGER;
BEGIN
  SELECT count(*) INTO existing
    FROM word WHERE word = postcode and type = 'P';

  IF existing > 0 THEN
    RETURN TRUE;
  END IF;

  -- postcodes don't need word ids
  INSERT INTO word (word_token, type, word)
    SELECT lookup_term, 'P', postcode FROM unnest(lookup_terms) as lookup_term;

  RETURN FALSE;
END;
$$
LANGUAGE plpgsql;

