-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- Functions for interpreting wkipedia/wikidata tags and computing importance.

DROP TYPE IF EXISTS wikipedia_article_match CASCADE;
CREATE TYPE wikipedia_article_match as (
  language TEXT,
  title TEXT,
  importance FLOAT
);

DROP TYPE IF EXISTS place_importance CASCADE;
CREATE TYPE place_importance as (
  importance FLOAT,
  wikipedia TEXT
);


-- See: http://stackoverflow.com/questions/6410088/how-can-i-mimic-the-php-urldecode-function-in-postgresql
CREATE OR REPLACE FUNCTION decode_url_part(p varchar)
  RETURNS varchar
  AS $$
SELECT convert_from(CAST(E'\\x' || array_to_string(ARRAY(
    SELECT CASE WHEN length(r.m[1]) = 1 THEN encode(convert_to(r.m[1], 'SQL_ASCII'), 'hex') ELSE substring(r.m[1] from 2 for 2) END
    FROM regexp_matches($1, '%[0-9a-f][0-9a-f]|.', 'gi') AS r(m)
), '') AS bytea), 'UTF8');
$$ 
LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION catch_decode_url_part(p varchar)
  RETURNS varchar
  AS $$
DECLARE
BEGIN
  RETURN decode_url_part(p);
EXCEPTION
  WHEN others THEN return null;
END;
$$
LANGUAGE plpgsql IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION get_wikipedia_match(extratags HSTORE, country_code varchar(2))
  RETURNS wikipedia_article_match
  AS $$
DECLARE
  langs TEXT[];
  i INT;
  wiki_article TEXT;
  wiki_article_title TEXT;
  wiki_article_language TEXT;
  result wikipedia_article_match;
BEGIN
  langs := ARRAY['english','country','ar','bg','ca','cs','da','de','en','es','eo','eu','fa','fr','ko','hi','hr','id','it','he','lt','hu','ms','nl','ja','no','pl','pt','kk','ro','ru','sk','sl','sr','fi','sv','tr','uk','vi','vo','war','zh'];
  i := 1;
  WHILE langs[i] IS NOT NULL LOOP
    wiki_article := extratags->(case when langs[i] in ('english','country') THEN 'wikipedia' ELSE 'wikipedia:'||langs[i] END);
    IF wiki_article is not null THEN
      wiki_article := regexp_replace(wiki_article,E'^(.*?)([a-z]{2,3}).wikipedia.org/wiki/',E'\\2:');
      wiki_article := regexp_replace(wiki_article,E'^(.*?)([a-z]{2,3}).wikipedia.org/w/index.php\\?title=',E'\\2:');
      wiki_article := regexp_replace(wiki_article,E'^(.*?)/([a-z]{2,3})/wiki/',E'\\2:');
      --wiki_article := regexp_replace(wiki_article,E'^(.*?)([a-z]{2,3})[=:]',E'\\2:');
      wiki_article := replace(wiki_article,' ','_');
      IF strpos(wiki_article, ':') IN (3,4) THEN
        wiki_article_language := lower(trim(split_part(wiki_article, ':', 1)));
        wiki_article_title := trim(substr(wiki_article, strpos(wiki_article, ':')+1));
      ELSE
        wiki_article_title := trim(wiki_article);
        wiki_article_language := CASE WHEN langs[i] = 'english' THEN 'en' WHEN langs[i] = 'country' THEN get_country_language_code(country_code) ELSE langs[i] END;
      END IF;

      select wikipedia_article.language,wikipedia_article.title,wikipedia_article.importance
        from wikipedia_article 
        where language = wiki_article_language and 
        (title = wiki_article_title OR title = catch_decode_url_part(wiki_article_title) OR title = replace(catch_decode_url_part(wiki_article_title),E'\\',''))
      UNION ALL
      select wikipedia_article.language,wikipedia_article.title,wikipedia_article.importance
        from wikipedia_redirect join wikipedia_article on (wikipedia_redirect.language = wikipedia_article.language and wikipedia_redirect.to_title = wikipedia_article.title)
        where wikipedia_redirect.language = wiki_article_language and 
        (from_title = wiki_article_title OR from_title = catch_decode_url_part(wiki_article_title) OR from_title = replace(catch_decode_url_part(wiki_article_title),E'\\',''))
      order by importance desc limit 1 INTO result;

      IF result.language is not null THEN
        return result;
      END IF;
    END IF;
    i := i + 1;
  END LOOP;
  RETURN NULL;
END;
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION get_osm_views(centroid GEOMETRY)
  RETURNS BIGINT
  AS $$
DECLARE
  result BIGINT;
BEGIN
  SELECT ST_Value(osm_views.rast, centroid)
  FROM osm_views
  WHERE ST_Intersects(ST_ConvexHull(osm_views.rast), centroid) LIMIT 1 INTO result;

  return COALESCE(result, 0);
END;
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION normalize_osm_views(views BIGINT)
  RETURNS FLOAT
  AS $$
  DECLARE
    normalized_osm_views FLOAT;
    max_views BIGINT;
  BEGIN
    IF views > 0 THEN
      -- Get the highest view count to use it in normalizing the data
      SELECT max_views_count FROM osm_views_stat INTO max_views;
      normalized_osm_views := (LOG(views))/(LOG(max_views));
    ELSE
      normalized_osm_views := 0.0;
    END IF;

    RETURN normalized_osm_views;
  END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION compute_importance(extratags HSTORE,
                                              country_code varchar(2),
                                              osm_type varchar(1), osm_id BIGINT,
                                              centroid GEOMETRY)
  RETURNS place_importance
  AS $$
DECLARE
  match RECORD;
  result place_importance;
  osm_views_exists BIGINT;
  views BIGINT;
BEGIN
 -- check if osm_views table exists
 SELECT COUNT(table_name)
   INTO osm_views_exists
 FROM information_schema.tables
 WHERE table_schema LIKE 'public' AND 
       table_type LIKE 'BASE TABLE' AND
       table_name = 'osm_views';

  -- add importance by OSM views if osm_views table exists
  IF osm_views_exists THEN
    views := get_osm_views(centroid);
    result.importance := normalize_osm_views(views) * 0.35;
  END IF;

  -- add importance by wiki data if the place has one
  FOR match IN SELECT * FROM get_wikipedia_match(extratags, country_code)
               WHERE language is not NULL
  LOOP
    result.importance := COALESCE(result.importance, 0) + match.importance * 0.65;
    result.wikipedia := match.language || ':' || match.title;
    RETURN result;
  END LOOP;

  IF extratags ? 'wikidata' THEN
    FOR match IN SELECT * FROM wikipedia_article
                  WHERE wd_page_title = extratags->'wikidata'
                  ORDER BY language = 'en' DESC, langcount DESC LIMIT 1 LOOP
      result.importance := COALESCE(result.importance, 0) + match.importance * 0.65;
      result.wikipedia := match.language || ':' || match.title;
      RETURN result;
    END LOOP;
  END IF;

  RETURN result;
END;
$$
LANGUAGE plpgsql;

