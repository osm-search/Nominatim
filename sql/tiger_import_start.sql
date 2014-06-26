DROP TABLE IF EXISTS location_property_tiger_import;
CREATE TABLE location_property_tiger_import () INHERITS (location_property);

CREATE OR REPLACE FUNCTION tigger_create_interpolation(linegeo GEOMETRY, in_startnumber INTEGER, 
  in_endnumber INTEGER, interpolationtype TEXT, 
  in_street TEXT, in_isin TEXT, in_postcode TEXT) RETURNS INTEGER
  AS $$
DECLARE
  
  startnumber INTEGER;
  endnumber INTEGER;
  stepsize INTEGER;
  housenum INTEGER;
  newpoints INTEGER;
  numberrange INTEGER;
  rangestartnumber INTEGER;
  place_centroid GEOMETRY;
  out_partition INTEGER;
  out_parent_place_id BIGINT;
  location RECORD;
  address_street_word_id INTEGER;  

BEGIN

  IF in_endnumber > in_startnumber THEN
    startnumber = in_startnumber;
    endnumber = in_endnumber;
  ELSE
    startnumber = in_endnumber;
    endnumber = in_startnumber;
  END IF;

  numberrange := endnumber - startnumber;
  rangestartnumber := startnumber;

  IF (interpolationtype = 'odd' AND startnumber%2 = 0) OR (interpolationtype = 'even' AND startnumber%2 = 1) THEN
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
    RAISE WARNING 'Road too short for number range % to % on %, % (%)',startnumber,endnumber,in_street,in_isin,
                  ST_length(linegeo)/(numberrange::float/stepsize::float);    
    RETURN 0;
  END IF;

  place_centroid := ST_Centroid(linegeo);
  out_partition := get_partition('us');
  out_parent_place_id := null;

  address_street_word_id := get_name_id(make_standard_name(in_street));
  IF address_street_word_id IS NOT NULL THEN
    FOR location IN SELECT * from getNearestNamedRoadFeature(out_partition, place_centroid, ARRAY[address_street_word_id]) LOOP
      out_parent_place_id := location.place_id;
    END LOOP;
  END IF;

  IF out_parent_place_id IS NULL THEN
    FOR location IN SELECT place_id FROM getNearestParellelRoadFeature(out_partition, linegeo) LOOP
      out_parent_place_id := location.place_id;
    END LOOP;    
  END IF;

  IF out_parent_place_id IS NULL THEN
    FOR location IN SELECT place_id FROM getNearestRoadFeature(out_partition, place_centroid) LOOP
      out_parent_place_id := location.place_id;
    END LOOP;    
  END IF;

  newpoints := 0;
  FOR housenum IN startnumber..endnumber BY stepsize LOOP
    insert into location_property_tiger_import (place_id, partition, parent_place_id, housenumber, postcode, centroid)
    values (nextval('seq_place'), out_partition, out_parent_place_id, housenum, in_postcode,
      ST_LineInterpolatePoint(linegeo, (housenum::float-rangestartnumber::float)/numberrange::float));
    newpoints := newpoints + 1;
  END LOOP;

  RETURN newpoints;
END;
$$
LANGUAGE plpgsql;
