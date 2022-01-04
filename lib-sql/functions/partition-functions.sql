-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

DROP TYPE IF EXISTS nearfeaturecentr CASCADE;
CREATE TYPE nearfeaturecentr AS (
  place_id BIGINT,
  keywords int[],
  rank_address smallint,
  rank_search smallint,
  distance float,
  isguess boolean,
  postcode TEXT,
  centroid GEOMETRY
);

-- feature intersects geoemtry
-- for areas and linestrings they must touch at least along a line
CREATE OR REPLACE FUNCTION is_relevant_geometry(de9im TEXT, geom_type TEXT)
RETURNS BOOLEAN
AS $$
BEGIN
  IF substring(de9im from 1 for 2) != 'FF' THEN
    RETURN TRUE;
  END IF;

  IF geom_type = 'ST_Point' THEN
    RETURN substring(de9im from 4 for 1) = '0';
  END IF;

  IF geom_type in ('ST_LineString', 'ST_MultiLineString') THEN
    RETURN substring(de9im from 4 for 1) = '1';
  END IF;

  RETURN substring(de9im from 4 for 1) = '2';
END
$$ LANGUAGE plpgsql IMMUTABLE;

create or replace function getNearFeatures(in_partition INTEGER, feature GEOMETRY, maxrank INTEGER) RETURNS setof nearfeaturecentr AS $$
DECLARE
  r nearfeaturecentr%rowtype;
BEGIN

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    FOR r IN
      SELECT place_id, keywords, rank_address, rank_search,
             min(ST_Distance(feature, centroid)) as distance,
             isguess, postcode, centroid
      FROM location_area_large_{{ partition }}
      WHERE geometry && feature
        AND is_relevant_geometry(ST_Relate(geometry, feature), ST_GeometryType(feature))
        AND rank_address < maxrank
            -- Postcodes currently still use rank_search to define for which
            -- features they are relevant.
        AND not (rank_address in (5, 11) and rank_search > maxrank)
      GROUP BY place_id, keywords, rank_address, rank_search, isguess, postcode, centroid
    LOOP
      RETURN NEXT r;
    END LOOP;
    RETURN;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION get_address_place(in_partition SMALLINT, feature GEOMETRY,
                                             from_rank SMALLINT, to_rank SMALLINT,
                                             extent FLOAT, token_info JSONB, key TEXT)
  RETURNS nearfeaturecentr
  AS $$
DECLARE
  r nearfeaturecentr%rowtype;
BEGIN
{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
      SELECT place_id, keywords, rank_address, rank_search,
             min(ST_Distance(feature, centroid)) as distance,
             isguess, postcode, centroid INTO r
        FROM location_area_large_{{ partition }}
        WHERE geometry && ST_Expand(feature, extent)
              AND rank_address between from_rank and to_rank
              AND token_matches_address(token_info, key, keywords)
        GROUP BY place_id, keywords, rank_address, rank_search, isguess, postcode, centroid
        ORDER BY bool_or(ST_Intersects(geometry, feature)), distance LIMIT 1;
      RETURN r;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END;
$$
LANGUAGE plpgsql STABLE;


create or replace function deleteLocationArea(in_partition INTEGER, in_place_id BIGINT, in_rank_search INTEGER) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

  IF in_rank_search <= 4 THEN
    DELETE from location_area_country WHERE place_id = in_place_id;
    RETURN TRUE;
  END IF;

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    DELETE from location_area_large_{{ partition }} WHERE place_id = in_place_id;
    RETURN TRUE;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;

  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function insertLocationAreaLarge(
  in_partition INTEGER, in_place_id BIGINT, in_country_code VARCHAR(2), in_keywords INTEGER[],
  in_rank_search INTEGER, in_rank_address INTEGER, in_estimate BOOLEAN, postcode TEXT,
  in_centroid GEOMETRY, in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN
  IF in_rank_address = 0 THEN
    RETURN TRUE;
  END IF;

  IF in_rank_search <= 4 and not in_estimate THEN
    INSERT INTO location_area_country (place_id, country_code, geometry)
      values (in_place_id, in_country_code, in_geometry);
    RETURN TRUE;
  END IF;

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    INSERT INTO location_area_large_{{ partition }} (partition, place_id, country_code, keywords, rank_search, rank_address, isguess, postcode, centroid, geometry)
      values (in_partition, in_place_id, in_country_code, in_keywords, in_rank_search, in_rank_address, in_estimate, postcode, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getNearestNamedRoadPlaceId(in_partition INTEGER,
                                                      point GEOMETRY,
                                                      token_info JSONB)
  RETURNS BIGINT
  AS $$
DECLARE
  parent BIGINT;
BEGIN
  IF not token_has_addr_street(token_info) THEN
    RETURN NULL;
  END IF;

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    SELECT place_id FROM search_name_{{ partition }}
      INTO parent
      WHERE token_matches_street(token_info, name_vector)
            AND centroid && ST_Expand(point, 0.015)
            AND address_rank between 26 and 27
      ORDER BY ST_Distance(centroid, point) ASC limit 1;
    RETURN parent;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION getNearestNamedPlacePlaceId(in_partition INTEGER,
                                                       point GEOMETRY,
                                                       token_info JSONB)
  RETURNS BIGINT
  AS $$
DECLARE
  parent BIGINT;
BEGIN
  IF not token_has_addr_place(token_info) THEN
    RETURN NULL;
  END IF;

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    SELECT place_id
      INTO parent
      FROM search_name_{{ partition }}
      WHERE token_matches_place(token_info, name_vector)
            AND centroid && ST_Expand(point, 0.04)
            AND address_rank between 16 and 25
      ORDER BY ST_Distance(centroid, point) ASC limit 1;
    RETURN parent;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql STABLE;

create or replace function insertSearchName(
  in_partition INTEGER, in_place_id BIGINT, in_name_vector INTEGER[],
  in_rank_search INTEGER, in_rank_address INTEGER, in_geometry GEOMETRY)
RETURNS BOOLEAN AS $$
DECLARE
BEGIN
{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    DELETE FROM search_name_{{ partition }} values WHERE place_id = in_place_id;
    IF in_rank_address > 0 THEN
      INSERT INTO search_name_{{ partition }} (place_id, address_rank, name_vector, centroid)
        values (in_place_id, in_rank_address, in_name_vector, in_geometry);
    END IF;
    RETURN TRUE;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function deleteSearchName(in_partition INTEGER, in_place_id BIGINT) RETURNS BOOLEAN AS $$
DECLARE
BEGIN
{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    DELETE from search_name_{{ partition }} WHERE place_id = in_place_id;
    RETURN TRUE;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;

  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function insertLocationRoad(
  in_partition INTEGER, in_place_id BIGINT, in_country_code VARCHAR(2), in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    DELETE FROM location_road_{{ partition }} where place_id = in_place_id;
    INSERT INTO location_road_{{ partition }} (partition, place_id, country_code, geometry)
      values (in_partition, in_place_id, in_country_code, in_geometry);
    RETURN TRUE;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function deleteRoad(in_partition INTEGER, in_place_id BIGINT) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    DELETE FROM location_road_{{ partition }} where place_id = in_place_id;
    RETURN TRUE;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;

  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getNearestRoadPlaceId(in_partition INTEGER, point GEOMETRY)
  RETURNS BIGINT
  AS $$
DECLARE
  r RECORD;
  search_diameter FLOAT;
BEGIN

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    search_diameter := 0.00005;
    WHILE search_diameter < 0.1 LOOP
      FOR r IN
        SELECT place_id FROM location_road_{{ partition }}
          WHERE ST_DWithin(geometry, point, search_diameter)
          ORDER BY ST_Distance(geometry, point) ASC limit 1
      LOOP
        RETURN r.place_id;
      END LOOP;
      search_diameter := search_diameter * 2;
    END LOOP;
    RETURN NULL;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION getNearestParallelRoadFeature(in_partition INTEGER,
                                                         line GEOMETRY)
  RETURNS BIGINT
  AS $$
DECLARE
  r RECORD;
  search_diameter FLOAT;
  p1 GEOMETRY;
  p2 GEOMETRY;
  p3 GEOMETRY;
BEGIN

  IF ST_GeometryType(line) not in ('ST_LineString') THEN
    RETURN NULL;
  END IF;

  p1 := ST_LineInterpolatePoint(line,0);
  p2 := ST_LineInterpolatePoint(line,0.5);
  p3 := ST_LineInterpolatePoint(line,1);

{% for partition in db.partitions %}
  IF in_partition = {{ partition }} THEN
    search_diameter := 0.0005;
    WHILE search_diameter < 0.01 LOOP
      FOR r IN
        SELECT place_id FROM location_road_{{ partition }}
          WHERE ST_DWithin(line, geometry, search_diameter)
          ORDER BY (ST_distance(geometry, p1)+
                    ST_distance(geometry, p2)+
                    ST_distance(geometry, p3)) ASC limit 1
      LOOP
        RETURN r.place_id;
      END LOOP;
      search_diameter := search_diameter * 2;
    END LOOP;
    RETURN NULL;
  END IF;
{% endfor %}

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql STABLE;
