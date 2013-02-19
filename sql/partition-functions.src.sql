create or replace function getNearFeatures(in_partition INTEGER, point GEOMETRY, maxrank INTEGER, isin_tokens INT[]) RETURNS setof nearfeaturecentr AS $$
DECLARE
  r nearfeaturecentr%rowtype;
BEGIN

-- start
  IF in_partition = -partition- THEN
    FOR r IN 
      SELECT place_id, keywords, rank_address, rank_search, min(ST_Distance(point, centroid)) as distance, isguess, centroid FROM (
        SELECT * FROM location_area_large_-partition- WHERE ST_Contains(geometry, point) and rank_search < maxrank
        UNION ALL
        SELECT * FROM location_area_country WHERE ST_Contains(geometry, point) and rank_search < maxrank
      ) as location_area
      GROUP BY place_id, keywords, rank_address, rank_search, isguess, centroid
      ORDER BY rank_address, isin_tokens && keywords desc, isguess asc,
        ST_Distance(point, centroid) * 
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
  in_rank_search INTEGER, in_rank_address INTEGER, in_estimate BOOLEAN, 
  in_centroid GEOMETRY, in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

  IF in_rank_search <= 4 THEN
    INSERT INTO location_area_country values (in_partition, in_place_id, in_country_code, in_keywords, in_rank_search, in_rank_address, in_estimate, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;

-- start
  IF in_partition = -partition- THEN
    INSERT INTO location_area_large_-partition- values (in_partition, in_place_id, in_country_code, in_keywords, in_rank_search, in_rank_address, in_estimate, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function getNearestNamedFeature(in_partition INTEGER, point GEOMETRY, maxrank INTEGER, isin_token INTEGER) RETURNS setof nearfeature AS $$
DECLARE
  r nearfeature%rowtype;
BEGIN

-- start
  IF in_partition = -partition- THEN
    FOR r IN 
      SELECT place_id, name_vector, address_rank, search_rank,
          ST_Distance(centroid, point) as distance, null as isguess
          FROM search_name_-partition-
          WHERE name_vector @> ARRAY[isin_token]
          AND search_rank < maxrank
      UNION ALL
      SELECT place_id, name_vector, address_rank, search_rank,
          ST_Distance(centroid, point) as distance, null as isguess
          FROM search_name_country
          WHERE name_vector @> ARRAY[isin_token]
          AND search_rank < maxrank
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

create or replace function getNearestNamedRoadFeature(in_partition INTEGER, point GEOMETRY, isin_token INTEGER) 
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
          WHERE name_vector @> ARRAY[isin_token]
          AND ST_DWithin(centroid, point, 0.01) 
          AND search_rank between 22 and 27
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

create or replace function getNearestPostcode(in_partition INTEGER, point GEOMETRY) 
  RETURNS TEXT AS $$
DECLARE
  out_postcode TEXT;
BEGIN

-- start
  IF in_partition = -partition- THEN
    SELECT postcode
        FROM location_area_large_-partition- join placex using (place_id)
        WHERE st_contains(location_area_large_-partition-.geometry, point)
        AND class = 'place' and type = 'postcode' 
      ORDER BY st_distance(location_area_large_-partition-.centroid, point) ASC limit 1
      INTO out_postcode;
    RETURN out_postcode;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
END
$$
LANGUAGE plpgsql;

create or replace function insertSearchName(
  in_partition INTEGER, in_place_id BIGINT, in_country_code VARCHAR(2), 
  in_name_vector INTEGER[], in_nameaddress_vector INTEGER[],
  in_rank_search INTEGER, in_rank_address INTEGER, in_importance FLOAT,
  in_centroid GEOMETRY, in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

  DELETE FROM search_name WHERE place_id = in_place_id;
  INSERT INTO search_name values (in_place_id, in_rank_search, in_rank_address, in_importance, in_country_code, 
    in_name_vector, in_nameaddress_vector, in_centroid);

  IF in_rank_search <= 4 THEN
    DELETE FROM search_name_country WHERE place_id = in_place_id;
    INSERT INTO search_name_country values (in_place_id, in_rank_search, in_rank_address, 
      in_name_vector, in_geometry);
    RETURN TRUE;
  END IF;

-- start
  IF in_partition = -partition- THEN
    DELETE FROM search_name_-partition- values WHERE place_id = in_place_id;
    INSERT INTO search_name_-partition- values (in_place_id, in_rank_search, in_rank_address, 
      in_name_vector, in_geometry);
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

  DELETE from search_name WHERE place_id = in_place_id;
  DELETE from search_name_country WHERE place_id = in_place_id;

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
    INSERT INTO location_road_-partition- values (in_partition, in_place_id, in_country_code, in_geometry);
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

  p1 := ST_Line_Interpolate_Point(line,0);
  p2 := ST_Line_Interpolate_Point(line,0.5);
  p3 := ST_Line_Interpolate_Point(line,1);

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
