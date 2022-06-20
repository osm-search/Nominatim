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
  SELECT info->>'place_match' is not null;
$$ LANGUAGE SQL IMMUTABLE;


CREATE OR REPLACE FUNCTION token_matches_street(info JSONB, street_tokens INTEGER[])
  RETURNS BOOLEAN
AS $$
  SELECT (info->>'street')::INTEGER[] && street_tokens
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_matches_place(info JSONB, place_tokens INTEGER[])
  RETURNS BOOLEAN
AS $$
  SELECT (info->>'place_match')::INTEGER[] && place_tokens
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_addr_place_search_tokens(info JSONB)
  RETURNS INTEGER[]
AS $$
  SELECT (info->>'place_search')::INTEGER[]
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_get_address_keys(info JSONB)
  RETURNS SETOF TEXT
AS $$
  SELECT * FROM jsonb_object_keys(info->'addr');
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_get_address_search_tokens(info JSONB, key TEXT)
  RETURNS INTEGER[]
AS $$
  SELECT (info->'addr'->key->>0)::INTEGER[];
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION token_matches_address(info JSONB, key TEXT, tokens INTEGER[])
  RETURNS BOOLEAN
AS $$
  SELECT (info->'addr'->key->>1)::INTEGER[] && tokens;
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

-- Functions for term normalisation and access to the 'word' table.

CREATE OR REPLACE FUNCTION transliteration(text) RETURNS text
  AS '{{ modulepath }}/nominatim.so', 'transliteration'
LANGUAGE c IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION gettokenstring(text) RETURNS text
  AS '{{ modulepath }}/nominatim.so', 'gettokenstring'
LANGUAGE c IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION make_standard_name(name TEXT) RETURNS TEXT
  AS $$
DECLARE
  o TEXT;
BEGIN
  o := public.gettokenstring(public.transliteration(name));
  RETURN trim(substr(o,1,length(o)));
END;
$$
LANGUAGE plpgsql IMMUTABLE;

-- returns NULL if the word is too common
CREATE OR REPLACE FUNCTION getorcreate_word_id(lookup_word TEXT) 
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
  count INTEGER;
BEGIN
  lookup_token := trim(lookup_word);
  SELECT min(word_id), max(search_name_count) FROM word
    WHERE word_token = lookup_token and class is null and type is null
    INTO return_word_id, count;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, null, null, null, null, 0);
  ELSE
    IF count > {{ max_word_freq }} THEN
      return_word_id := NULL;
    END IF;
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;


-- Create housenumber tokens from an OSM addr:housenumber.
-- The housnumber is split at comma and semicolon as necessary.
-- The function returns the normalized form of the housenumber suitable
-- for comparison.
CREATE OR REPLACE FUNCTION create_housenumbers(housenumbers TEXT[],
                                               OUT tokens TEXT,
                                               OUT normtext TEXT)
  AS $$
BEGIN
  SELECT array_to_string(array_agg(trans), ';'), array_agg(tid)::TEXT
    INTO normtext, tokens
    FROM (SELECT lookup_word as trans, getorcreate_housenumber_id(lookup_word) as tid
          FROM (SELECT make_standard_name(h) as lookup_word
                FROM unnest(housenumbers) h) x) y;
END;
$$ LANGUAGE plpgsql STABLE STRICT;


CREATE OR REPLACE FUNCTION getorcreate_housenumber_id(lookup_word TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' ' || trim(lookup_word);
  SELECT min(word_id) FROM word
    WHERE word_token = lookup_token and class='place' and type='house'
    INTO return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, null,
                             'place', 'house', null, 0);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION create_postcode_id(postcode TEXT)
  RETURNS BOOLEAN
  AS $$
DECLARE
  r RECORD;
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' ' || make_standard_name(postcode);
  FOR r IN
    SELECT word_id FROM word
    WHERE word_token = lookup_token and word = postcode
          and class='place' and type='postcode'
  LOOP
    RETURN false;
  END LOOP;

  INSERT INTO word VALUES (nextval('seq_word'), lookup_token, postcode,
                           'place', 'postcode', null, 0);
  RETURN true;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION getorcreate_name_id(lookup_word TEXT, src_word TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  nospace_lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word
  WHERE word_token = lookup_token and class is null and type is null
  INTO return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, src_word,
                             null, null, null, 0);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;


-- Normalize a string and lookup its word ids (partial words).
CREATE OR REPLACE FUNCTION addr_ids_from_name(lookup_word TEXT)
  RETURNS INTEGER[]
  AS $$
DECLARE
  words TEXT[];
  id INTEGER;
  return_word_id INTEGER[];
  word_ids INTEGER[];
  j INTEGER;
BEGIN
  words := string_to_array(make_standard_name(lookup_word), ' ');
  IF array_upper(words, 1) IS NOT NULL THEN
    FOR j IN 1..array_upper(words, 1) LOOP
      IF (words[j] != '') THEN
        SELECT array_agg(word_id) INTO word_ids
          FROM word
         WHERE word_token = words[j] and class is null and type is null;

        IF word_ids IS NULL THEN
          id := nextval('seq_word');
          INSERT INTO word VALUES (id, words[j], null, null, null, null, 0);
          return_word_id := return_word_id || id;
        ELSE
          return_word_id := array_merge(return_word_id, word_ids);
        END IF;
      END IF;
    END LOOP;
  END IF;

  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;


-- Normalize a string and look up its name ids (full words).
CREATE OR REPLACE FUNCTION word_ids_from_name(lookup_word TEXT)
  RETURNS INTEGER[]
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_ids INTEGER[];
BEGIN
  lookup_token := ' '|| make_standard_name(lookup_word);
  SELECT array_agg(word_id) FROM word
    WHERE word_token = lookup_token and class is null and type is null
    INTO return_word_ids;
  RETURN return_word_ids;
END;
$$
LANGUAGE plpgsql STABLE STRICT;


CREATE OR REPLACE FUNCTION make_keywords(src HSTORE)
  RETURNS INTEGER[]
  AS $$
DECLARE
  result INTEGER[];
  s TEXT;
  w INTEGER;
  words TEXT[];
  value TEXT;
  j INTEGER;
BEGIN
  result := '{}'::INTEGER[];

  FOR value IN SELECT unnest(regexp_split_to_array(svals(src), E'[,;]')) LOOP
    -- full name
    s := make_standard_name(value);
    w := getorcreate_name_id(s, value);

    IF not(ARRAY[w] <@ result) THEN
      result := result || w;
    END IF;

    -- partial single-word terms
    words := string_to_array(s, ' ');
    IF array_upper(words, 1) IS NOT NULL THEN
      FOR j IN 1..array_upper(words, 1) LOOP
        IF (words[j] != '') THEN
          w = getorcreate_word_id(words[j]);
          IF w IS NOT NULL AND NOT (ARRAY[w] <@ result) THEN
            result := result || w;
          END IF;
        END IF;
      END LOOP;
    END IF;

    -- consider parts before an opening braket a full word as well
    words := regexp_split_to_array(value, E'[(]');
    IF array_upper(words, 1) > 1 THEN
      s := make_standard_name(words[1]);
      IF s != '' THEN
        w := getorcreate_name_id(s, words[1]);
        IF w IS NOT NULL AND NOT (ARRAY[w] <@ result) THEN
          result := result || w;
        END IF;
      END IF;
    END IF;

    s := regexp_replace(value, '市$', '');
    IF s != value THEN
      s := make_standard_name(s);
      IF s != '' THEN
        w := getorcreate_name_id(s, value);
        IF NOT (ARRAY[w] <@ result) THEN
          result := result || w;
        END IF;
      END IF;
    END IF;

  END LOOP;

  RETURN result;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION precompute_words(src TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  s TEXT;
  w INTEGER;
  words TEXT[];
  i INTEGER;
  j INTEGER;
BEGIN
  s := make_standard_name(src);
  w := getorcreate_name_id(s, src);

  w := getorcreate_word_id(s);

  words := string_to_array(s, ' ');
  IF array_upper(words, 1) IS NOT NULL THEN
    FOR j IN 1..array_upper(words, 1) LOOP
      IF (words[j] != '') THEN
        w := getorcreate_word_id(words[j]);
      END IF;
    END LOOP;
  END IF;

  words := regexp_split_to_array(src, E'[,;()]');
  IF array_upper(words, 1) != 1 THEN
    FOR j IN 1..array_upper(words, 1) LOOP
      s := make_standard_name(words[j]);
      IF s != '' THEN
        w := getorcreate_word_id(s);
      END IF;
    END LOOP;
  END IF;

  s := regexp_replace(src, '市$', '');
  IF s != src THEN
    s := make_standard_name(s);
    IF s != '' THEN
      w := getorcreate_name_id(s, src);
    END IF;
  END IF;

  RETURN 1;
END;
$$
LANGUAGE plpgsql;
