-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.
DROP TABLE IF EXISTS location_property_tiger_import;
CREATE TABLE location_property_tiger_import (
  linegeo GEOMETRY,
  place_id BIGINT,
  partition INTEGER,
  parent_place_id BIGINT,
  startnumber INTEGER,
  endnumber INTEGER,
  step SMALLINT,
  postcode TEXT);


-- Lookup functions for tiger import when update 
-- informations are dropped (see gh-issue #2463)
CREATE OR REPLACE FUNCTION getNearestNamedRoadPlaceIdSlow(in_centroid GEOMETRY,
                                                      in_token_info JSONB)
  RETURNS BIGINT
  AS $$
DECLARE
  out_place_id BIGINT;

BEGIN
  SELECT place_id INTO out_place_id 
    FROM search_name
    WHERE 
        -- finds rows where name_vector shares elements with search tokens.
        token_matches_street(in_token_info, name_vector)
        -- limits search area
        AND centroid && ST_Expand(in_centroid, 0.015) 
        AND address_rank BETWEEN 26 AND 27
    ORDER BY ST_Distance(centroid, in_centroid) ASC 
    LIMIT 1;

  RETURN out_place_id;
END
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION getNearestParallelRoadFeatureSlow(line GEOMETRY)
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

    search_diameter := 0.0005;
    WHILE search_diameter < 0.01 LOOP
      FOR r IN
        SELECT place_id FROM placex
          WHERE ST_DWithin(line, geometry, search_diameter)
          AND rank_address BETWEEN 26 AND 27
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
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION getNearestRoadPlaceIdSlow(point GEOMETRY)
  RETURNS BIGINT
  AS $$
DECLARE
  r RECORD;
  search_diameter FLOAT;
BEGIN
    search_diameter := 0.00005;
    WHILE search_diameter < 0.1 LOOP
      FOR r IN
        SELECT place_id FROM placex
          WHERE ST_DWithin(geometry, point, search_diameter)
          AND rank_address BETWEEN 26 AND 27
          ORDER BY ST_Distance(geometry, point) ASC limit 1
      LOOP
        RETURN r.place_id;
      END LOOP;
      search_diameter := search_diameter * 2;
    END LOOP;
    RETURN NULL;
END
$$
LANGUAGE plpgsql;


-- Tiger import function
CREATE OR REPLACE FUNCTION tiger_line_import(linegeo GEOMETRY, in_startnumber INTEGER,
                                             in_endnumber INTEGER, interpolationtype TEXT,
                                             token_info JSONB, in_postcode TEXT) RETURNS INTEGER
  AS $$
DECLARE
  startnumber INTEGER;
  endnumber INTEGER;
  stepsize INTEGER;
  numberrange INTEGER;
  place_centroid GEOMETRY;
  out_partition INTEGER;
  out_parent_place_id BIGINT;
  location RECORD;

BEGIN

  IF in_endnumber > in_startnumber THEN
    startnumber := in_startnumber;
    endnumber := in_endnumber;
  ELSE
    startnumber := in_endnumber;
    endnumber := in_startnumber;
    linegeo := ST_Reverse(linegeo);
  END IF;

  IF startnumber < 0 THEN
    RAISE WARNING 'Negative house number range (% to %)', startnumber, endnumber;
    RETURN 0;
  END IF;

  numberrange := endnumber - startnumber;

  IF (interpolationtype = 'odd' AND startnumber % 2 = 0) OR (interpolationtype = 'even' AND startnumber % 2 = 1) THEN
    startnumber := startnumber + 1;
    stepsize := 2;
  ELSE
    IF (interpolationtype = 'odd' OR interpolationtype = 'even') THEN
      stepsize := 2;
    ELSE -- everything else assumed to be 'all'
      stepsize := 1;
    END IF;
  END IF;

  -- Filter out really broken tiger data
  IF numberrange > 0
     and numberrange::float/stepsize::float > 500
     and ST_length(linegeo)/(numberrange::float/stepsize::float) < 0.000001
  THEN
    RAISE WARNING 'Road too short for number range % to % (%)',startnumber,endnumber,
                  ST_length(linegeo)/(numberrange::float/stepsize::float);
    RETURN 0;
  END IF;

  place_centroid := ST_Centroid(linegeo);
  out_partition := get_partition('us');

  -- HYBRID LOOKUP LOGIC (see gh-issue #2463)
  -- if partition tables exist, use them for fast spatial lookups
  {% if 'location_road_0' in db.tables %}
    out_parent_place_id := getNearestNamedRoadPlaceId(out_partition, place_centroid,
                                                    token_info);

    IF out_parent_place_id IS NULL THEN
      SELECT getNearestParallelRoadFeature(out_partition, linegeo)
        INTO out_parent_place_id;
    END IF;

    IF out_parent_place_id IS NULL THEN
      SELECT getNearestRoadPlaceId(out_partition, place_centroid)
        INTO out_parent_place_id;
    END IF;

  -- When updatable information has been dropped:
  -- Partition tables no longer exist, but search_name still persists.
  {% elif 'search_name' in db.tables %}
    -- Fallback: Look up in 'search_name' table 
    -- though spatial lookups here can be slower.
    out_parent_place_id := getNearestNamedRoadPlaceIdSlow(place_centroid, token_info);

    IF out_parent_place_id IS NULL THEN
      out_parent_place_id := getNearestParallelRoadFeatureSlow(linegeo);
    END IF;

    IF out_parent_place_id IS NULL THEN
      out_parent_place_id := getNearestRoadPlaceIdSlow(place_centroid);
    END IF;
  {% endif %}

  -- If parent was found, insert street(line) into import table
  IF out_parent_place_id IS NOT NULL THEN
    INSERT INTO location_property_tiger_import (linegeo, place_id, partition,
                                                parent_place_id, startnumber, endnumber,
                                                step, postcode)
    VALUES (linegeo, nextval('seq_place'), out_partition,
            out_parent_place_id, startnumber, endnumber,
            stepsize, in_postcode);

    RETURN 1;
  END IF;
  RETURN 0;

END;
$$
LANGUAGE plpgsql;
