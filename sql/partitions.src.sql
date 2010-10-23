create type nearplace as (
  place_id bigint
);

create type nearfeature as (
  place_id bigint,
  keywords int[],
  rank_address integer,
  rank_search integer,
  distance float
);

-- start
CREATE TABLE location_area_large_-partition- () INHERITS (location_area_large);
CREATE INDEX idx_location_area_large_-partition-_geometry ON location_area_large_-partition- USING GIST (geometry);

CREATE TABLE location_area_roadnear_-partition- () INHERITS (location_area_roadnear);
CREATE INDEX idx_location_area_roadnear_-partition-_geometry ON location_area_roadnear_-partition- USING GIST (geometry);

CREATE TABLE location_area_roadfar_-partition- () INHERITS (location_area_roadfar);
CREATE INDEX idx_location_area_roadfar_-partition-_geometry ON location_area_roadfar_-partition- USING GIST (geometry);
-- end

create or replace function getNearRoads(in_partition TEXT, point GEOMETRY) RETURNS setof nearplace AS $$
DECLARE
  r nearplace%rowtype;
BEGIN

-- start
  IF in_partition = '-partition-' THEN
    FOR r IN SELECT place_id FROM location_area_large WHERE partition = '-partition-' and ST_Contains(geometry, point) LOOP
      RETURN NEXT r;
    END LOOP;
    RETURN;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql;

create or replace function getNearFeatures(in_partition TEXT, point GEOMETRY, maxrank INTEGER) RETURNS setof nearfeature AS $$
DECLARE
  r nearfeature%rowtype;
BEGIN

-- start
  IF in_partition = '-partition-' THEN
    FOR r IN SELECT
      place_id,
      keywords,
      rank_address,
      rank_search,
      ST_Distance(place_centroid, centroid) as distance
      FROM location_area_large
      WHERE ST_Contains(area, point) and location_area_large.rank_search < maxrank
      ORDER BY ST_Distance(place_centroid, centroid) ASC
    LOOP
      RETURN NEXT r;
    END LOOP;
    RETURN;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql;

create or replace function deleteLocationArea(in_partition TEXT, in_place_id bigint) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

-- start
  IF in_partition = '-partition-' THEN
    DELETE from location_area_large_-partition- WHERE place_id = in_place_id;
    DELETE from location_area_roadnear_-partition- WHERE place_id = in_place_id;
    DELETE from location_area_roadfar_-partition- WHERE place_id = in_place_id;
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;

  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function insertLocationAreaLarge(
  in_partition TEXT, in_place_id bigint, in_keywords INTEGER[], 
  in_rank_search INTEGER, in_rank_address INTEGER, in_estimate BOOLEAN, 
  in_centroid GEOMETRY, in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

-- start
  IF in_partition = '-partition-' THEN
    INSERT INTO location_area_large_-partition- values (in_partition, in_place_id, in_keywords, in_rank_search, in_rank_address, in_estimate, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function insertLocationAreaRoadNear(
  in_partition TEXT, in_place_id bigint, in_keywords INTEGER[], 
  in_rank_search INTEGER, in_rank_address INTEGER, in_estimate BOOLEAN, 
  in_centroid GEOMETRY, in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

-- start
  IF in_partition = '-partition-' THEN
    INSERT INTO location_area_roadnear_-partition- values (in_partition, in_place_id, in_keywords, in_rank_search, in_rank_address, in_estimate, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function insertLocationAreaRoadFar(
  in_partition TEXT, in_place_id bigint, in_keywords INTEGER[], 
  in_rank_search INTEGER, in_rank_address INTEGER, in_estimate BOOLEAN, 
  in_centroid GEOMETRY, in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

-- start
  IF in_partition = '-partition-' THEN
    INSERT INTO location_area_roadfar_-partition- values (in_partition, in_place_id, in_keywords, in_rank_search, in_rank_address, in_estimate, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;
