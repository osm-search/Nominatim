-- These functions query unified tables instead of partitions,
-- which allows TIGER data imports on frozen databases.

-- TODO: add reinstatiation of partition functions if needed
DROP FUNCTION IF EXISTS getNearestNamedRoadPlaceId(integer, geometry, jsonb) CASCADE;
DROP FUNCTION IF EXISTS find_road_with_postcode(integer, text) CASCADE;
DROP FUNCTION IF EXISTS getNearestRoadPlaceId(integer, geometry) CASCADE;
DROP FUNCTION IF EXISTS getAddressName(integer, geometry) CASCADE;
DROP FUNCTION IF EXISTS getNearestParallelRoadFeature(integer, geometry) CASCADE;


CREATE FUNCTION getNearestParallelRoadFeature(in_partition INTEGER,
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

  p1 := ST_LineInterpolatePoint(line, 0);
  p2 := ST_LineInterpolatePoint(line, 0.5);
  p3 := ST_LineInterpolatePoint(line, 1);

  search_diameter := 0.0005;
  WHILE search_diameter < 0.01 LOOP
    FOR r IN
      SELECT place_id FROM placex
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

END
$$
LANGUAGE plpgsql STABLE PARALLEL SAFE;


CREATE FUNCTION getNearestNamedRoadPlaceId(in_partition INTEGER,
                                           point GEOMETRY,
                                           token_info JSONB)
  RETURNS BIGINT AS $$
DECLARE
  parent BIGINT;
BEGIN
  IF not token_has_addr_street(token_info) THEN
    RETURN NULL;
  END IF;

  SELECT place_id INTO parent
    FROM search_name
    WHERE token_matches_street(token_info, name_vector)
          AND centroid && ST_Expand(point, 0.015)
          AND address_rank between 26 and 27
    ORDER BY ST_Distance(centroid, point) ASC LIMIT 1;

  RETURN parent;
END
$$
LANGUAGE plpgsql STABLE PARALLEL SAFE;


CREATE FUNCTION find_road_with_postcode(in_partition INTEGER, postcode TEXT)
  RETURNS BIGINT AS $$
DECLARE
  parent BIGINT;
BEGIN
  SELECT place_id INTO parent
    FROM placex
    WHERE postcode = postcode
          AND rank_address between 26 and 27
          AND class = 'highway'
    ORDER BY ST_Distance(centroid, 
                         (SELECT ST_Centroid(geometry) 
                          FROM placex WHERE postcode = postcode LIMIT 1)) ASC LIMIT 1;

  RETURN parent;
END
$$
LANGUAGE plpgsql STABLE PARALLEL SAFE;


CREATE FUNCTION getNearestRoadPlaceId(in_partition INTEGER, point GEOMETRY)
  RETURNS BIGINT AS $$
DECLARE
  parent BIGINT;
BEGIN
  SELECT place_id INTO parent
    FROM placex
    WHERE centroid && ST_Expand(point, 0.015)
          AND rank_address between 26 and 27
          AND class = 'highway'
    ORDER BY ST_Distance(centroid, point) ASC LIMIT 1;

  RETURN parent;
END
$$
LANGUAGE plpgsql STABLE PARALLEL SAFE;


CREATE FUNCTION getAddressName(in_partition INTEGER, point GEOMETRY)
  RETURNS TEXT AS $$
DECLARE
  name TEXT;
BEGIN
  SELECT name INTO name
    FROM search_name
    WHERE centroid && ST_Expand(point, 0.015)
          AND rank_address between 26 and 27
    ORDER BY ST_Distance(centroid, point) ASC LIMIT 1;

  RETURN name;
END
$$
LANGUAGE plpgsql STABLE PARALLEL SAFE;


