-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- Assorted helper functions for the triggers.

CREATE OR REPLACE FUNCTION geometry_sector(partition INTEGER, place geometry)
  RETURNS INTEGER
  AS $$
DECLARE
  NEWgeometry geometry;
BEGIN
--  RAISE WARNING '%',place;
  NEWgeometry := ST_PointOnSurface(place);
  RETURN (partition*1000000) + (500-ST_X(NEWgeometry)::integer)*1000 + (500-ST_Y(NEWgeometry)::integer);
END;
$$
LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION array_merge(a INTEGER[], b INTEGER[])
  RETURNS INTEGER[]
  AS $$
DECLARE
  i INTEGER;
  r INTEGER[];
BEGIN
  IF array_upper(a, 1) IS NULL THEN
    RETURN b;
  END IF;
  IF array_upper(b, 1) IS NULL THEN
    RETURN a;
  END IF;
  r := a;
  FOR i IN 1..array_upper(b, 1) LOOP  
    IF NOT (ARRAY[b[i]] <@ r) THEN
      r := r || b[i];
    END IF;
  END LOOP;
  RETURN r;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

-- Return the node members with a given label from a relation member list
-- as a set.
--
-- \param members      Member list in osm2pgsql middle format.
-- \param memberLabels Array of labels to accept.
--
-- \returns Set of OSM ids of nodes that are found.
--
CREATE OR REPLACE FUNCTION get_rel_node_members(members TEXT[],
                                                memberLabels TEXT[])
  RETURNS SETOF BIGINT
  AS $$
DECLARE
  i INTEGER;
BEGIN
  FOR i IN 1..ARRAY_UPPER(members,1) BY 2 LOOP
    IF members[i+1] = ANY(memberLabels)
       AND upper(substring(members[i], 1, 1))::char(1) = 'N'
    THEN
      RETURN NEXT substring(members[i], 2)::bigint;
    END IF;
  END LOOP;

  RETURN;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

-- Copy 'name' to or from the default language.
--
-- \param country_code     Country code of the object being named.
-- \param[inout] name      List of names of the object.
--
-- If the country named by country_code has a single default language,
-- then a `name` tag is copied to `name:<country_code>` if this tag does
-- not yet exist and vice versa.
CREATE OR REPLACE FUNCTION add_default_place_name(country_code VARCHAR(2),
                                                  INOUT name HSTORE)
  AS $$
DECLARE
  default_language VARCHAR(10);
BEGIN
  IF name is not null AND array_upper(akeys(name),1) > 1 THEN
    default_language := get_country_language_code(country_code);
    IF default_language IS NOT NULL THEN
      IF name ? 'name' AND NOT name ? ('name:'||default_language) THEN
        name := name || hstore(('name:'||default_language), (name -> 'name'));
      ELSEIF name ? ('name:'||default_language) AND NOT name ? 'name' THEN
        name := name || hstore('name', (name -> ('name:'||default_language)));
      END IF;
    END IF;
  END IF;
END;
$$
LANGUAGE plpgsql IMMUTABLE;


-- Find the nearest artificial postcode for the given geometry.
-- TODO For areas there should not be more than two inside the geometry.
CREATE OR REPLACE FUNCTION get_nearest_postcode(country VARCHAR(2), geom GEOMETRY)
  RETURNS TEXT
  AS $$
DECLARE
  outcode TEXT;
  cnt INTEGER;
BEGIN
    -- If the geometry is an area then only one postcode must be within
    -- that area, otherwise consider the area as not having a postcode.
    IF ST_GeometryType(geom) in ('ST_Polygon','ST_MultiPolygon') THEN
        SELECT min(postcode), count(*) FROM
              (SELECT postcode FROM location_postcode
                WHERE ST_Contains(geom, location_postcode.geometry) LIMIT 2) sub
          INTO outcode, cnt;

        IF cnt = 1 THEN
            RETURN outcode;
        ELSE
            RETURN null;
        END IF;
    END IF;

    SELECT postcode FROM location_postcode
     WHERE ST_DWithin(geom, location_postcode.geometry, 0.05)
          AND location_postcode.country_code = country
     ORDER BY ST_Distance(geom, location_postcode.geometry) LIMIT 1
    INTO outcode;

    RETURN outcode;
END;
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION get_country_code(place geometry)
  RETURNS TEXT
  AS $$
DECLARE
  place_centre GEOMETRY;
  nearcountry RECORD;
BEGIN
  place_centre := ST_PointOnSurface(place);

-- RAISE WARNING 'get_country_code, start: %', ST_AsText(place_centre);

  -- Try for a OSM polygon
  FOR nearcountry IN
    SELECT country_code from location_area_country
    WHERE country_code is not null and st_covers(geometry, place_centre) limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

-- RAISE WARNING 'osm fallback: %', ST_AsText(place_centre);

  -- Try for OSM fallback data
  -- The order is to deal with places like HongKong that are 'states' within another polygon
  FOR nearcountry IN
    SELECT country_code from country_osm_grid
    WHERE st_covers(geometry, place_centre) order by area asc limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

-- RAISE WARNING 'near osm fallback: %', ST_AsText(place_centre);

  RETURN NULL;
END;
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION get_country_language_code(search_country_code VARCHAR(2))
  RETURNS TEXT
  AS $$
DECLARE
  nearcountry RECORD;
BEGIN
  FOR nearcountry IN
    SELECT distinct country_default_language_code from country_name
    WHERE country_code = search_country_code limit 1
  LOOP
    RETURN lower(nearcountry.country_default_language_code);
  END LOOP;
  RETURN NULL;
END;
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION get_partition(in_country_code VARCHAR(10))
  RETURNS INTEGER
  AS $$
DECLARE
  nearcountry RECORD;
BEGIN
  FOR nearcountry IN
    SELECT partition from country_name where country_code = in_country_code
  LOOP
    RETURN nearcountry.partition;
  END LOOP;
  RETURN 0;
END;
$$
LANGUAGE plpgsql STABLE;


-- Find the parent of an address with addr:street/addr:place tag.
--
-- \param token_info Naming info with the address information.
-- \param partition  Partition where to search the parent.
-- \param centroid   Location of the address.
--
-- \return Place ID of the parent if one was found, NULL otherwise.
CREATE OR REPLACE FUNCTION find_parent_for_address(token_info JSONB,
                                                   partition SMALLINT,
                                                   centroid GEOMETRY)
  RETURNS BIGINT
  AS $$
DECLARE
  parent_place_id BIGINT;
BEGIN
  -- Check for addr:street attributes
  parent_place_id := getNearestNamedRoadPlaceId(partition, centroid, token_info);
  IF parent_place_id is not null THEN
    {% if debug %}RAISE WARNING 'Get parent from addr:street: %', parent_place_id;{% endif %}
    RETURN parent_place_id;
  END IF;

  -- Check for addr:place attributes.
  parent_place_id := getNearestNamedPlacePlaceId(partition, centroid, token_info);
  {% if debug %}RAISE WARNING 'Get parent from addr:place: %', parent_place_id;{% endif %}
  RETURN parent_place_id;
END;
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION delete_location(OLD_place_id BIGINT)
  RETURNS BOOLEAN
  AS $$
DECLARE
BEGIN
  DELETE FROM location_area where place_id = OLD_place_id;
-- TODO:location_area
  RETURN true;
END;
$$
LANGUAGE plpgsql;

-- Create a bounding box with an extent computed from the radius (in meters)
-- which in turn is derived from the given search rank.
CREATE OR REPLACE FUNCTION place_node_fuzzy_area(geom GEOMETRY, rank_search INTEGER)
  RETURNS GEOMETRY
  AS $$
DECLARE
  radius FLOAT := 500;
BEGIN
  IF rank_search <= 16 THEN -- city
    radius := 15000;
  ELSIF rank_search <= 18 THEN -- town
    radius := 4000;
  ELSIF rank_search <= 19 THEN -- village
    radius := 2000;
  ELSIF rank_search  <= 20 THEN -- hamlet
    radius := 1000;
  END IF;

  RETURN ST_Envelope(ST_Collect(
                     ST_Project(geom::geography, radius, 0.785398)::geometry,
                     ST_Project(geom::geography, radius, 3.9269908)::geometry));
END;
$$
LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION add_location(place_id BIGINT, country_code varchar(2),
                                        partition INTEGER, keywords INTEGER[],
                                        rank_search INTEGER, rank_address INTEGER,
                                        in_postcode TEXT, geometry GEOMETRY,
                                        centroid GEOMETRY)
  RETURNS BOOLEAN
  AS $$
DECLARE
  locationid INTEGER;
  secgeo GEOMETRY;
  postcode TEXT;
BEGIN
  PERFORM deleteLocationArea(partition, place_id, rank_search);

  -- add postcode only if it contains a single entry, i.e. ignore postcode lists
  postcode := NULL;
  IF in_postcode is not null AND in_postcode not similar to '%(,|;)%' THEN
      postcode := upper(trim (in_postcode));
  END IF;

  IF ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') THEN
    FOR secgeo IN select split_geometry(geometry) AS geom LOOP
      PERFORM insertLocationAreaLarge(partition, place_id, country_code, keywords, rank_search, rank_address, false, postcode, centroid, secgeo);
    END LOOP;

  ELSEIF ST_GeometryType(geometry) = 'ST_Point' THEN
    secgeo := place_node_fuzzy_area(geometry, rank_search);
    PERFORM insertLocationAreaLarge(partition, place_id, country_code, keywords, rank_search, rank_address, true, postcode, centroid, secgeo);

  END IF;

  RETURN true;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION quad_split_geometry(geometry GEOMETRY, maxarea FLOAT,
                                               maxdepth INTEGER)
  RETURNS SETOF GEOMETRY
  AS $$
DECLARE
  xmin FLOAT;
  ymin FLOAT;
  xmax FLOAT;
  ymax FLOAT;
  xmid FLOAT;
  ymid FLOAT;
  secgeo GEOMETRY;
  secbox GEOMETRY;
  seg INTEGER;
  geo RECORD;
  area FLOAT;
  remainingdepth INTEGER;
  added INTEGER;
BEGIN

--  RAISE WARNING 'quad_split_geometry: maxarea=%, depth=%',maxarea,maxdepth;

  IF (ST_GeometryType(geometry) not in ('ST_Polygon','ST_MultiPolygon') OR NOT ST_IsValid(geometry)) THEN
    RETURN NEXT geometry;
    RETURN;
  END IF;

  remainingdepth := maxdepth - 1;
  area := ST_AREA(geometry);
  IF remainingdepth < 1 OR area < maxarea THEN
    RETURN NEXT geometry;
    RETURN;
  END IF;

  xmin := st_xmin(geometry);
  xmax := st_xmax(geometry);
  ymin := st_ymin(geometry);
  ymax := st_ymax(geometry);
  secbox := ST_SetSRID(ST_MakeBox2D(ST_Point(ymin,xmin),ST_Point(ymax,xmax)),4326);

  -- if the geometry completely covers the box don't bother to slice any more
  IF ST_AREA(secbox) = area THEN
    RETURN NEXT geometry;
    RETURN;
  END IF;

  xmid := (xmin+xmax)/2;
  ymid := (ymin+ymax)/2;

  added := 0;
  FOR seg IN 1..4 LOOP

    IF seg = 1 THEN
      secbox := ST_SetSRID(ST_MakeBox2D(ST_Point(xmin,ymin),ST_Point(xmid,ymid)),4326);
    END IF;
    IF seg = 2 THEN
      secbox := ST_SetSRID(ST_MakeBox2D(ST_Point(xmin,ymid),ST_Point(xmid,ymax)),4326);
    END IF;
    IF seg = 3 THEN
      secbox := ST_SetSRID(ST_MakeBox2D(ST_Point(xmid,ymin),ST_Point(xmax,ymid)),4326);
    END IF;
    IF seg = 4 THEN
      secbox := ST_SetSRID(ST_MakeBox2D(ST_Point(xmid,ymid),ST_Point(xmax,ymax)),4326);
    END IF;

    IF st_intersects(geometry, secbox) THEN
      secgeo := st_intersection(geometry, secbox);
      IF NOT ST_IsEmpty(secgeo) AND ST_GeometryType(secgeo) in ('ST_Polygon','ST_MultiPolygon') THEN
        FOR geo IN select quad_split_geometry(secgeo, maxarea, remainingdepth) as geom LOOP
          IF NOT ST_IsEmpty(geo.geom) AND ST_GeometryType(geo.geom) in ('ST_Polygon','ST_MultiPolygon') THEN
            added := added + 1;
            RETURN NEXT geo.geom;
          END IF;
        END LOOP;
      END IF;
    END IF;
  END LOOP;

  RETURN;
END;
$$
LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION split_geometry(geometry GEOMETRY)
  RETURNS SETOF GEOMETRY
  AS $$
DECLARE
  geo RECORD;
BEGIN
  -- 10000000000 is ~~ 1x1 degree
  FOR geo IN select quad_split_geometry(geometry, 0.25, 20) as geom LOOP
    RETURN NEXT geo.geom;
  END LOOP;
  RETURN;
END;
$$
LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION place_force_delete(placeid BIGINT)
  RETURNS BOOLEAN
  AS $$
DECLARE
    osmid BIGINT;
    osmtype character(1);
    pclass text;
    ptype text;
BEGIN
  SELECT osm_type, osm_id, class, type FROM placex WHERE place_id = placeid INTO osmtype, osmid, pclass, ptype;
  DELETE FROM import_polygon_delete where osm_type = osmtype and osm_id = osmid and class = pclass and type = ptype;
  DELETE FROM import_polygon_error where osm_type = osmtype and osm_id = osmid and class = pclass and type = ptype;
  -- force delete by directly entering it into the to-be-deleted table
  INSERT INTO place_to_be_deleted (osm_type, osm_id, class, type, deferred)
         VALUES(osmtype, osmid, pclass, ptype, false);
  PERFORM flush_deleted_places();

  RETURN TRUE;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION place_force_update(placeid BIGINT)
  RETURNS BOOLEAN
  AS $$
DECLARE
  placegeom GEOMETRY;
  geom GEOMETRY;
  diameter FLOAT;
  rank SMALLINT;
BEGIN
  UPDATE placex SET indexed_status = 2 WHERE place_id = placeid;

  SELECT geometry, rank_address INTO placegeom, rank
    FROM placex WHERE place_id = placeid;

  IF placegeom IS NOT NULL AND ST_IsValid(placegeom) THEN
    IF ST_GeometryType(placegeom) in ('ST_Polygon','ST_MultiPolygon')
       AND rank > 0
    THEN
      FOR geom IN SELECT split_geometry(placegeom) LOOP
        UPDATE placex SET indexed_status = 2
         WHERE ST_Intersects(geom, placex.geometry)
               and indexed_status = 0
               and ((rank_address = 0 and rank_search > rank) or rank_address > rank)
               and (rank_search < 28 or name is not null or (rank >= 16 and address ? 'place'));
      END LOOP;
    ELSE
        diameter := update_place_diameter(rank);
        IF diameter > 0 THEN
          IF rank >= 26 THEN
            -- roads may cause reparenting for >27 rank places
            update placex set indexed_status = 2 where indexed_status = 0 and rank_search > rank and ST_DWithin(placex.geometry, placegeom, diameter);
          ELSEIF rank >= 16 THEN
            -- up to rank 16, street-less addresses may need reparenting
            update placex set indexed_status = 2 where indexed_status = 0 and rank_search > rank and ST_DWithin(placex.geometry, placegeom, diameter) and (rank_search < 28 or name is not null or address ? 'place');
          ELSE
            -- for all other places the search terms may change as well
            update placex set indexed_status = 2 where indexed_status = 0 and rank_search > rank and ST_DWithin(placex.geometry, placegeom, diameter) and (rank_search < 28 or name is not null);
          END IF;
        END IF;
    END IF;
    RETURN TRUE;
  END IF;

  RETURN FALSE;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION flush_deleted_places()
  RETURNS INTEGER
  AS $$
BEGIN
  -- deleting large polygons can have a massive effect on the system - require manual intervention to let them through
  INSERT INTO import_polygon_delete (osm_type, osm_id, class, type)
    SELECT osm_type, osm_id, class, type FROM place_to_be_deleted WHERE deferred;

  -- delete from place table
  ALTER TABLE place DISABLE TRIGGER place_before_delete;
  DELETE FROM place USING place_to_be_deleted
    WHERE place.osm_type = place_to_be_deleted.osm_type
          and place.osm_id = place_to_be_deleted.osm_id
          and place.class = place_to_be_deleted.class
          and place.type = place_to_be_deleted.type
          and not deferred;
  ALTER TABLE place ENABLE TRIGGER place_before_delete;

  -- Mark for delete in the placex table
  UPDATE placex SET indexed_status = 100 FROM place_to_be_deleted
    WHERE placex.osm_type = 'N' and place_to_be_deleted.osm_type = 'N'
          and placex.osm_id = place_to_be_deleted.osm_id
          and placex.class = place_to_be_deleted.class
          and placex.type = place_to_be_deleted.type
          and not deferred;
  UPDATE placex SET indexed_status = 100 FROM place_to_be_deleted
    WHERE placex.osm_type = 'W' and place_to_be_deleted.osm_type = 'W'
          and placex.osm_id = place_to_be_deleted.osm_id
          and placex.class = place_to_be_deleted.class
          and placex.type = place_to_be_deleted.type
          and not deferred;
  UPDATE placex SET indexed_status = 100 FROM place_to_be_deleted
    WHERE placex.osm_type = 'R' and place_to_be_deleted.osm_type = 'R'
          and placex.osm_id = place_to_be_deleted.osm_id
          and placex.class = place_to_be_deleted.class
          and placex.type = place_to_be_deleted.type
          and not deferred;

   -- Mark for delete in interpolations
   UPDATE location_property_osmline SET indexed_status = 100 FROM place_to_be_deleted
    WHERE place_to_be_deleted.osm_type = 'W'
          and place_to_be_deleted.class = 'place'
          and place_to_be_deleted.type = 'houses'
          and location_property_osmline.osm_id = place_to_be_deleted.osm_id
          and not deferred;

   -- Clear todo list.
   TRUNCATE TABLE place_to_be_deleted;

   RETURN NULL;
END;
$$ LANGUAGE plpgsql;
