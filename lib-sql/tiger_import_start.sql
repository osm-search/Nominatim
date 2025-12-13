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
CREATE OR REPLACE FUNCTION lookup_road_in_search_name(
    in_centroid GEOMETRY, 
    in_token_info JSONB)
  RETURNS BIGINT
  AS $$
DECLARE
  out_place_id BIGINT;
  search_tokens INTEGER[];

BEGIN
  -- extract tokens
  in_token_info := COALESCE(in_token_info, '[]'::jsonb);

-- Convert JSONB array to PostgreSQL Integer Array
  SELECT ARRAY(
      SELECT jsonb_array_elements_text(
          CASE WHEN jsonb_typeof(in_token_info) = 'array' THEN in_token_info
          ELSE '[]'::jsonb END -- if NULL
      )::int
  ) INTO search_tokens;

  IF array_length(search_tokens, 1) IS NULL THEN
    RETURN NULL;
  END IF;


  SELECT place_id INTO out_place_id 
    FROM search_name
    WHERE 
        -- finds rows where name_vector shares elements with search tokens.
        name_vector && search_tokens
        -- limits search area
        AND centroid && ST_Expand(in_centroid, 0.015) 
        AND address_rank BETWEEN 26 AND 27
    ORDER BY ST_Distance(centroid, in_centroid) ASC 
    LIMIT 1;

  RETURN out_place_id;
END;
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
    out_parent_place_id := getNearestNamedRoadPlaceId(
      out_partition, place_centroid, token_info
    );

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
    RAISE WARNING 'Database frozen. Performing fallback tiger import lookup without partition tables';
    -- Fallback: Look up in 'search_name' table 
    -- though spatial lookups here can be slower.
    out_parent_place_id := lookup_road_in_search_name(place_centroid, token_info);
  {% else %}
    RAISE EXCEPTION 'Cannot perform tiger import: required tables are missing';
    RETURN 0;
  {% endif %}

--insert street(line) into import table
insert into location_property_tiger_import (linegeo, place_id, partition,
                                            parent_place_id, startnumber, endnumber,
                                            step, postcode)
values (linegeo, nextval('seq_place'), out_partition,
        out_parent_place_id, startnumber, endnumber,
        stepsize, in_postcode);

  RETURN 1;
END;
$$
LANGUAGE plpgsql;
