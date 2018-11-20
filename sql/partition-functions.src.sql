create or replace function getNearFeatures(in_partition INTEGER, feature GEOMETRY, maxrank INTEGER, isin_tokens INT[]) RETURNS setof nearfeaturecentr AS $$
DECLARE
  r nearfeaturecentr%rowtype;
BEGIN

-- start
  IF in_partition = -partition- THEN
    FOR r IN 
      SELECT place_id, keywords, rank_address, rank_search, min(ST_Distance(feature, centroid)) as distance, isguess, postcode, centroid FROM (
        SELECT * FROM location_area_large_-partition- WHERE ST_Intersects(geometry, feature) and rank_search < maxrank
        UNION ALL
        SELECT * FROM location_area_country WHERE ST_Intersects(geometry, feature) and rank_search < maxrank
      ) as location_area
      GROUP BY place_id, keywords, rank_address, rank_search, isguess, postcode, centroid
      ORDER BY rank_address, isin_tokens && keywords desc, isguess asc,
        ST_Distance(feature, centroid) *
          CASE 
               WHEN rank_address = 16 AND rank_search = 15 THEN 0.2 -- capital city
               WHEN rank_address = 16 AND rank_search = 16 THEN 0.25 -- city
               WHEN rank_address = 16 AND rank_search = 17 THEN 0.5 -- town
               ELSE 1 END ASC -- everything else
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

create or replace function deleteLocationArea(in_partition INTEGER, in_place_id BIGINT, in_rank_search INTEGER) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

  IF in_rank_search <= 4 THEN
    DELETE from location_area_country WHERE place_id = in_place_id;
    RETURN TRUE;
  END IF;

-- start
  IF in_partition = -partition- THEN
    DELETE from location_area_large_-partition- WHERE place_id = in_place_id;
    RETURN TRUE;
  END IF;
-- end

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

  IF in_rank_search <= 4 THEN
    INSERT INTO location_area_country (partition, place_id, country_code, keywords, rank_search, rank_address, isguess, centroid, geometry)
      values (in_partition, in_place_id, in_country_code, in_keywords, in_rank_search, in_rank_address, in_estimate, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;

-- start
  IF in_partition = -partition- THEN
    INSERT INTO location_area_large_-partition- (partition, place_id, country_code, keywords, rank_search, rank_address, isguess, postcode, centroid, geometry)
      values (in_partition, in_place_id, in_country_code, in_keywords, in_rank_search, in_rank_address, in_estimate, postcode, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function getNearestNamedRoadFeature(in_partition INTEGER, point GEOMETRY, isin_token INTEGER[]) 
  RETURNS setof nearfeature AS $$
DECLARE
  r nearfeature%rowtype;
BEGIN

-- start
  IF in_partition = -partition- THEN
    FOR r IN 
      SELECT place_id, name_vector, address_rank, search_rank,
          ST_Distance(centroid, point) as distance, null as isguess
          FROM search_name_-partition-
          WHERE name_vector && isin_token
          AND ST_DWithin(centroid, point, 0.015)
          AND search_rank between 26 and 27
      ORDER BY distance ASC limit 1
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

create or replace function getNearestNamedPlaceFeature(in_partition INTEGER, point GEOMETRY, isin_token INTEGER[]) 
  RETURNS setof nearfeature AS $$
DECLARE
  r nearfeature%rowtype;
BEGIN

-- start
  IF in_partition = -partition- THEN
    FOR r IN 
      SELECT place_id, name_vector, address_rank, search_rank,
          ST_Distance(centroid, point) as distance, null as isguess
          FROM search_name_-partition-
          WHERE name_vector && isin_token
          AND ST_DWithin(centroid, point, 0.04)
          AND search_rank between 16 and 22
      ORDER BY distance ASC limit 1
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


create or replace function insertSearchName(
  in_partition INTEGER, in_place_id BIGINT, in_name_vector INTEGER[],
  in_rank_search INTEGER, in_rank_address INTEGER, in_geometry GEOMETRY)
RETURNS BOOLEAN AS $$
DECLARE
BEGIN
-- start
  IF in_partition = -partition- THEN
    DELETE FROM search_name_-partition- values WHERE place_id = in_place_id;
    IF in_rank_address > 0 THEN
      INSERT INTO search_name_-partition- (place_id, search_rank, address_rank, name_vector, centroid)
        values (in_place_id, in_rank_search, in_rank_address, in_name_vector, in_geometry);
    END IF;
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function deleteSearchName(in_partition INTEGER, in_place_id BIGINT) RETURNS BOOLEAN AS $$
DECLARE
BEGIN
-- start
  IF in_partition = -partition- THEN
    DELETE from search_name_-partition- WHERE place_id = in_place_id;
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;

  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function insertLocationRoad(
  in_partition INTEGER, in_place_id BIGINT, in_country_code VARCHAR(2), in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

-- start
  IF in_partition = -partition- THEN
    DELETE FROM location_road_-partition- where place_id = in_place_id;
    INSERT INTO location_road_-partition- (partition, place_id, country_code, geometry)
      values (in_partition, in_place_id, in_country_code, in_geometry);
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function deleteRoad(in_partition INTEGER, in_place_id BIGINT) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

-- start
  IF in_partition = -partition- THEN
    DELETE FROM location_road_-partition- where place_id = in_place_id;
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;

  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function getNearestRoadFeature(in_partition INTEGER, point GEOMETRY) RETURNS setof nearfeature AS $$
DECLARE
  r nearfeature%rowtype;
  search_diameter FLOAT;  
BEGIN

-- start
  IF in_partition = -partition- THEN
    search_diameter := 0.00005;
    WHILE search_diameter < 0.1 LOOP
      FOR r IN 
        SELECT place_id, null, null, null,
            ST_Distance(geometry, point) as distance, null as isguess
            FROM location_road_-partition-
            WHERE ST_DWithin(geometry, point, search_diameter) 
        ORDER BY distance ASC limit 1
      LOOP
        RETURN NEXT r;
        RETURN;
      END LOOP;
      search_diameter := search_diameter * 2;
    END LOOP;
    RETURN;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql;

create or replace function getNearestParellelRoadFeature(in_partition INTEGER, line GEOMETRY) RETURNS setof nearfeature AS $$
DECLARE
  r nearfeature%rowtype;
  search_diameter FLOAT;  
  p1 GEOMETRY;
  p2 GEOMETRY;
  p3 GEOMETRY;
BEGIN

  IF st_geometrytype(line) not in ('ST_LineString') THEN
    RETURN;
  END IF;

  p1 := ST_LineInterpolatePoint(line,0);
  p2 := ST_LineInterpolatePoint(line,0.5);
  p3 := ST_LineInterpolatePoint(line,1);

-- start
  IF in_partition = -partition- THEN
    search_diameter := 0.0005;
    WHILE search_diameter < 0.01 LOOP
      FOR r IN 
        SELECT place_id, null, null, null,
            ST_Distance(geometry, line) as distance, null as isguess
            FROM location_road_-partition-
            WHERE ST_DWithin(line, geometry, search_diameter)
            ORDER BY (ST_distance(geometry, p1)+
                      ST_distance(geometry, p2)+
                      ST_distance(geometry, p3)) ASC limit 1
      LOOP
        RETURN NEXT r;
        RETURN;
      END LOOP;
      search_diameter := search_diameter * 2;
    END LOOP;
    RETURN;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql;
