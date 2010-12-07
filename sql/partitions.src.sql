create type nearplace as (
  place_id integer
);

create type nearfeature as (
  place_id integer,
  keywords int[],
  rank_address integer,
  rank_search integer,
  distance float
);

CREATE TABLE location_area_country () INHERITS (location_area_large);
CREATE INDEX idx_location_area_country_place_id ON location_area_country USING BTREE (place_id);
CREATE INDEX idx_location_area_country_geometry ON location_area_country USING GIST (geometry);

CREATE TABLE search_name_country () INHERITS (search_name_blank);
CREATE INDEX idx_search_name_country_place_id ON search_name_country USING BTREE (place_id);
CREATE INDEX idx_search_name_country_centroid ON search_name_country USING GIST (centroid);
CREATE INDEX idx_search_name_country_name_vector ON search_name_country USING GIN (name_vector gin__int_ops);
CREATE INDEX idx_search_name_country_nameaddress_vector ON search_name_country USING GIN (nameaddress_vector gin__int_ops);

-- start
CREATE TABLE location_area_large_-partition- () INHERITS (location_area_large);
CREATE INDEX idx_location_area_large_-partition-_place_id ON location_area_large_-partition- USING BTREE (place_id);
CREATE INDEX idx_location_area_large_-partition-_geometry ON location_area_large_-partition- USING GIST (geometry);

CREATE TABLE search_name_-partition- () INHERITS (search_name_blank);
CREATE INDEX idx_search_name_-partition-_place_id ON search_name_-partition- USING BTREE (place_id);
CREATE INDEX idx_search_name_-partition-_centroid ON search_name_-partition- USING GIST (centroid);
CREATE INDEX idx_search_name_-partition-_name_vector ON search_name_-partition- USING GIN (name_vector gin__int_ops);
CREATE INDEX idx_search_name_-partition-_nameaddress_vector ON search_name_-partition- USING GIN (nameaddress_vector gin__int_ops);

CREATE TABLE location_property_-partition- () INHERITS (location_property);
CREATE INDEX idx_location_property_-partition-_place_id ON location_property_-partition- USING BTREE (place_id);
CREATE INDEX idx_location_property_-partition-_parent_place_id ON location_property_-partition- USING BTREE (parent_place_id);
CREATE INDEX idx_location_property_-partition-_housenumber_parent_place_id ON location_property_-partition- USING BTREE (parent_place_id, housenumber);
--CREATE INDEX idx_location_property_-partition-_centroid ON location_property_-partition- USING GIST (centroid);

-- end

create or replace function getNearFeatures(in_partition INTEGER, point GEOMETRY, maxrank INTEGER, isin_tokens INT[]) RETURNS setof nearfeature AS $$
DECLARE
  r nearfeature%rowtype;
BEGIN

-- start
  IF in_partition = -partition- THEN
    FOR r IN 
      SELECT place_id, keywords, rank_address, rank_search, ST_Distance(point, centroid) as distance FROM (
        SELECT * FROM location_area_large_-partition- WHERE ST_Contains(geometry, point) and rank_search < maxrank
        UNION ALL
        SELECT * FROM location_area_country WHERE ST_Contains(geometry, point) and rank_search < maxrank
      ) as location_area
      ORDER BY rank_address desc, isin_tokens && keywords desc, isguess asc, ST_Distance(point, centroid) * CASE WHEN rank_address = 16 AND rank_search = 16 THEN 0.25 WHEN rank_address = 16 AND rank_search = 17 THEN 0.5 ELSE 1 END ASC
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

create or replace function deleteLocationArea(in_partition INTEGER, in_place_id integer) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

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
  in_partition INTEGER, in_place_id integer, in_country_code VARCHAR(2), in_keywords INTEGER[], 
  in_rank_search INTEGER, in_rank_address INTEGER, in_estimate BOOLEAN, 
  in_centroid GEOMETRY, in_geometry GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

  IF in_rank_search <= 4 THEN
    DELETE FROM location_area_country where place_id = in_place_id;
    INSERT INTO location_area_country values (in_partition, in_place_id, in_country_code, in_keywords, in_rank_search, in_rank_address, in_estimate, in_centroid, in_geometry);
    RETURN TRUE;
  END IF;

-- start
  IF in_partition = -partition- THEN
    DELETE FROM location_area_large_-partition- where place_id = in_place_id;
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
          ST_Distance(centroid, point) as distance
          FROM search_name_-partition-
          WHERE name_vector @> ARRAY[isin_token]
          AND search_rank < maxrank
      UNION ALL
      SELECT place_id, name_vector, address_rank, search_rank,
          ST_Distance(centroid, point) as distance
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

create or replace function getNearestNamedRoadFeature(in_partition INTEGER, point GEOMETRY, isin_token INTEGER) RETURNS setof nearfeature AS $$
DECLARE
  r nearfeature%rowtype;
BEGIN

-- start
  IF in_partition = -partition- THEN
    FOR r IN 
      SELECT place_id, name_vector, address_rank, search_rank,
          ST_Distance(centroid, point) as distance
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

create or replace function insertSearchName(
  in_partition INTEGER, in_place_id integer, in_country_code VARCHAR(2), 
  in_name_vector INTEGER[], in_nameaddress_vector INTEGER[],
  in_rank_search INTEGER, in_rank_address INTEGER,
  in_centroid GEOMETRY) RETURNS BOOLEAN AS $$
DECLARE
BEGIN

  DELETE FROM search_name WHERE place_id = in_place_id;
  INSERT INTO search_name values (in_place_id, in_rank_search, in_rank_address, 0, in_country_code, 
    in_name_vector, in_nameaddress_vector, in_centroid);

  IF in_rank_search <= 4 THEN
    DELETE FROM search_name_country WHERE place_id = in_place_id;
    INSERT INTO search_name_country values (in_place_id, in_rank_search, in_rank_address, 0, in_country_code, 
      in_name_vector, in_nameaddress_vector, in_centroid);
    RETURN TRUE;
  END IF;

-- start
  IF in_partition = -partition- THEN
    DELETE FROM search_name_-partition- values WHERE place_id = in_place_id;
    INSERT INTO search_name_-partition- values (in_place_id, in_rank_search, in_rank_address, 0, in_country_code, 
      in_name_vector, in_nameaddress_vector, in_centroid);
    RETURN TRUE;
  END IF;
-- end

  RAISE EXCEPTION 'Unknown partition %', in_partition;
  RETURN FALSE;
END
$$
LANGUAGE plpgsql;

create or replace function deleteSearchName(in_partition INTEGER, in_place_id integer) RETURNS BOOLEAN AS $$
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
