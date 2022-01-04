-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.
DROP TABLE IF EXISTS location_property_tiger_import;
CREATE TABLE location_property_tiger_import (linegeo GEOMETRY, place_id BIGINT, partition INTEGER, parent_place_id BIGINT, startnumber INTEGER, endnumber INTEGER, interpolationtype TEXT, postcode TEXT);

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
    startnumber = in_startnumber;
    endnumber = in_endnumber;
  ELSE
    startnumber = in_endnumber;
    endnumber = in_startnumber;
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
  IF numberrange > 0 AND (numberrange::float/stepsize::float > 500)
                    AND ST_length(linegeo)/(numberrange::float/stepsize::float) < 0.000001 THEN
    RAISE WARNING 'Road too short for number range % to % (%)',startnumber,endnumber,
                  ST_length(linegeo)/(numberrange::float/stepsize::float);
    RETURN 0;
  END IF;

  place_centroid := ST_Centroid(linegeo);
  out_partition := get_partition('us');

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

--insert street(line) into import table
insert into location_property_tiger_import (linegeo, place_id, partition, parent_place_id, startnumber, endnumber, interpolationtype, postcode)
values (linegeo, nextval('seq_place'), out_partition, out_parent_place_id, startnumber, endnumber, interpolationtype, in_postcode);

  RETURN 1;
END;
$$
LANGUAGE plpgsql;
