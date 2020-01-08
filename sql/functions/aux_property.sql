-- Functions for adding external data (currently unused).

CREATE OR REPLACE FUNCTION aux_create_property(pointgeo GEOMETRY, in_housenumber TEXT,
                                               in_street TEXT, in_isin TEXT,
                                               in_postcode TEXT, in_countrycode char(2))
  RETURNS INTEGER
  AS $$
DECLARE

  newpoints INTEGER;
  place_centroid GEOMETRY;
  out_partition INTEGER;
  out_parent_place_id BIGINT;
  location RECORD;
  address_street_word_id INTEGER;
  out_postcode TEXT;

BEGIN

  place_centroid := ST_Centroid(pointgeo);
  out_partition := get_partition(in_countrycode);
  out_parent_place_id := null;

  address_street_word_id := get_name_id(make_standard_name(in_street));
  IF address_street_word_id IS NOT NULL THEN
    FOR location IN SELECT * from getNearestNamedRoadFeature(out_partition, place_centroid, address_street_word_id) LOOP
      out_parent_place_id := location.place_id;
    END LOOP;
  END IF;

  IF out_parent_place_id IS NULL THEN
    FOR location IN SELECT place_id FROM getNearestRoadFeature(out_partition, place_centroid) LOOP
      out_parent_place_id := location.place_id;
    END LOOP;
  END IF;

  out_postcode := in_postcode;
  IF out_postcode IS NULL THEN
    SELECT postcode from placex where place_id = out_parent_place_id INTO out_postcode;
  END IF;
  -- XXX look into postcode table

  newpoints := 0;
  insert into location_property_aux (place_id, partition, parent_place_id,
                                     housenumber, postcode, centroid)
    values (nextval('seq_place'), out_partition, out_parent_place_id,
            in_housenumber, out_postcode, place_centroid);
  newpoints := newpoints + 1;

  RETURN newpoints;
END;
$$
LANGUAGE plpgsql;

