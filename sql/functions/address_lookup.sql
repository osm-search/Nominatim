-- Functions for returning address information for a place.

DROP TYPE IF EXISTS addressline CASCADE;
CREATE TYPE addressline as (
  place_id BIGINT,
  osm_type CHAR(1),
  osm_id BIGINT,
  name HSTORE,
  class TEXT,
  type TEXT,
  admin_level INTEGER,
  fromarea BOOLEAN,
  isaddress BOOLEAN,
  rank_address INTEGER,
  distance FLOAT
);


CREATE OR REPLACE FUNCTION get_name_by_language(name hstore, languagepref TEXT[])
  RETURNS TEXT
  AS $$
DECLARE
  result TEXT;
BEGIN
  IF name is null THEN
    RETURN null;
  END IF;

  FOR j IN 1..array_upper(languagepref,1) LOOP
    IF name ? languagepref[j] THEN
      result := trim(name->languagepref[j]);
      IF result != '' THEN
        return result;
      END IF;
    END IF;
  END LOOP;

  -- anything will do as a fallback - just take the first name type thing there is
  RETURN trim((avals(name))[1]);
END;
$$
LANGUAGE plpgsql IMMUTABLE;


--housenumber only needed for tiger data
CREATE OR REPLACE FUNCTION get_address_by_language(for_place_id BIGINT,
                                                   housenumber INTEGER,
                                                   languagepref TEXT[])
  RETURNS TEXT
  AS $$
DECLARE
  result TEXT[];
  currresult TEXT;
  prevresult TEXT;
  location RECORD;
BEGIN

  result := '{}';
  prevresult := '';

  FOR location IN
    SELECT * FROM get_addressdata(for_place_id, housenumber)
    WHERE isaddress order by rank_address desc
  LOOP
    currresult := trim(get_name_by_language(location.name, languagepref));
    IF currresult != prevresult AND currresult IS NOT NULL
       AND result[(100 - location.rank_address)] IS NULL
    THEN
      result[(100 - location.rank_address)] := trim(get_name_by_language(location.name, languagepref));
      prevresult := currresult;
    END IF;
  END LOOP;

  RETURN array_to_string(result,', ');
END;
$$
LANGUAGE plpgsql STABLE;


-- Compute the list of address parts for the given place.
--
-- If in_housenumber is greator or equal 0, look for an interpolation.
CREATE OR REPLACE FUNCTION get_addressdata(in_place_id BIGINT, in_housenumber INTEGER)
  RETURNS setof addressline
  AS $$
DECLARE
  for_place_id BIGINT;
  result TEXT[];
  search TEXT[];
  found INTEGER;
  location RECORD;
  countrylocation RECORD;
  searchcountrycode varchar(2);
  searchhousenumber TEXT;
  searchhousename HSTORE;
  searchrankaddress INTEGER;
  searchpostcode TEXT;
  postcode_isaddress BOOL;
  searchclass TEXT;
  searchtype TEXT;
  countryname HSTORE;
BEGIN
  -- The place ein question might not have a direct entry in place_addressline.
  -- Look for the parent of such places then and save if in for_place_id.

  postcode_isaddress := true;

  -- first query osmline (interpolation lines)
  IF in_housenumber >= 0 THEN
    SELECT parent_place_id, country_code, in_housenumber::text, 30, postcode,
           null, 'place', 'house'
      FROM location_property_osmline
      WHERE place_id = in_place_id AND in_housenumber>=startnumber
            AND in_housenumber <= endnumber
      INTO for_place_id, searchcountrycode, searchhousenumber, searchrankaddress,
           searchpostcode, searchhousename, searchclass, searchtype;
  END IF;

  --then query tiger data
  -- %NOTIGERDATA% IF 0 THEN
  IF for_place_id IS NULL AND in_housenumber >= 0 THEN
    SELECT parent_place_id, 'us', in_housenumber::text, 30, postcode, null,
           'place', 'house'
      FROM location_property_tiger
      WHERE place_id = in_place_id AND in_housenumber >= startnumber
            AND in_housenumber <= endnumber
      INTO for_place_id, searchcountrycode, searchhousenumber, searchrankaddress,
           searchpostcode, searchhousename, searchclass, searchtype;
  END IF;
  -- %NOTIGERDATA% END IF;

  -- %NOAUXDATA% IF 0 THEN
  IF for_place_id IS NULL THEN
    SELECT parent_place_id, 'us', housenumber, 30, postcode, null, 'place', 'house'
      FROM location_property_aux
      WHERE place_id = in_place_id
      INTO for_place_id,searchcountrycode, searchhousenumber, searchrankaddress,
           searchpostcode, searchhousename, searchclass, searchtype;
  END IF;
  -- %NOAUXDATA% END IF;

  -- postcode table
  IF for_place_id IS NULL THEN
    SELECT parent_place_id, country_code, rank_search, postcode, 'place', 'postcode'
      FROM location_postcode
      WHERE place_id = in_place_id
      INTO for_place_id, searchcountrycode, searchrankaddress, searchpostcode,
           searchclass, searchtype;
  END IF;

  -- POI objects in the placex table
  IF for_place_id IS NULL THEN
    SELECT parent_place_id, country_code, housenumber, rank_search, postcode,
           name, class, type
      FROM placex
      WHERE place_id = in_place_id and rank_search > 27
      INTO for_place_id, searchcountrycode, searchhousenumber, searchrankaddress,
           searchpostcode, searchhousename, searchclass, searchtype;
  END IF;

  -- If for_place_id is still NULL at this point then the object has its own
  -- entry in place_address line. However, still check if there is not linked
  -- place we should be using instead.
  IF for_place_id IS NULL THEN
    select coalesce(linked_place_id, place_id),  country_code,
           housenumber, rank_search, postcode, null
      from placex where place_id = in_place_id
      INTO for_place_id, searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode, searchhousename;
  END IF;

--RAISE WARNING '% % % %',searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode;

  found := 1000; -- the lowest rank_address included

  -- Return the record for the base entry.
  FOR location IN
    SELECT placex.place_id, osm_type, osm_id, name,
           class, type, admin_level,
           type not in ('postcode', 'postal_code') as isaddress,
           CASE WHEN rank_address = 0 THEN 100
                WHEN rank_address = 11 THEN 5
                ELSE rank_address END as rank_address,
           0 as distance, country_code, postcode
      FROM placex
      WHERE place_id = for_place_id
  LOOP
--RAISE WARNING '%',location;
    IF searchcountrycode IS NULL AND location.country_code IS NOT NULL THEN
      searchcountrycode := location.country_code;
    END IF;
    IF location.rank_address < 4 THEN
      -- no country locations for ranks higher than country
      searchcountrycode := NULL;
    END IF;
    countrylocation := ROW(location.place_id, location.osm_type, location.osm_id,
                           location.name, location.class, location.type,
                           location.admin_level, true, location.isaddress,
                           location.rank_address, location.distance)::addressline;
    RETURN NEXT countrylocation;
    found := location.rank_address;
  END LOOP;

  FOR location IN
    SELECT placex.place_id, osm_type, osm_id, name,
           CASE WHEN extratags ? 'place' THEN 'place' ELSE class END as class,
           CASE WHEN extratags ? 'place' THEN extratags->'place' ELSE type END as type,
           admin_level, fromarea, isaddress,
           CASE WHEN rank_address = 11 THEN 5 ELSE rank_address END as rank_address,
           distance, country_code, postcode
      FROM place_addressline join placex on (address_place_id = placex.place_id)
      WHERE place_addressline.place_id = for_place_id
            AND (cached_rank_address >= 4 AND cached_rank_address < searchrankaddress)
            AND linked_place_id is null
            AND (placex.country_code IS NULL OR searchcountrycode IS NULL
                 OR placex.country_code = searchcountrycode)
      ORDER BY rank_address desc, isaddress desc, fromarea desc,
               distance asc, rank_search desc
  LOOP
--RAISE WARNING '%',location;
    IF searchcountrycode IS NULL AND location.country_code IS NOT NULL THEN
      searchcountrycode := location.country_code;
    END IF;
    IF location.type in ('postcode', 'postal_code') THEN
      postcode_isaddress := false;
      IF location.osm_type != 'R' THEN
        location.isaddress := FALSE;
      END IF;
    END IF;
    countrylocation := ROW(location.place_id, location.osm_type, location.osm_id,
                           location.name, location.class, location.type,
                           location.admin_level, location.fromarea,
                           location.isaddress, location.rank_address,
                           location.distance)::addressline;
    RETURN NEXT countrylocation;
    found := location.rank_address;
  END LOOP;

  -- If no country was included yet, add the name information from country_name.
  IF found > 4 THEN
    SELECT name FROM country_name
      WHERE country_code = searchcountrycode LIMIT 1 INTO countryname;
--RAISE WARNING '% % %',found,searchcountrycode,countryname;
    IF countryname IS NOT NULL THEN
      location := ROW(null, null, null, countryname, 'place', 'country',
                      null, true, true, 4, 0)::addressline;
      RETURN NEXT location;
    END IF;
  END IF;

  -- Finally add some artificial rows.
  IF searchcountrycode IS NOT NULL THEN
    location := ROW(null, null, null, hstore('ref', searchcountrycode),
                    'place', 'country_code', null, true, false, 4, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchhousename IS NOT NULL THEN
    location := ROW(in_place_id, null, null, searchhousename, searchclass,
                    searchtype, null, true, true, 29, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchhousenumber IS NOT NULL THEN
    location := ROW(in_place_id, null, null, hstore('ref', searchhousenumber),
                    'place', 'house_number', null, true, true, 28, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchpostcode IS NOT NULL THEN
    location := ROW(null, null, null, hstore('ref', searchpostcode), 'place',
                    'postcode', null, false, postcode_isaddress, 5, 0)::addressline;
    RETURN NEXT location;
  END IF;

  RETURN;
END;
$$
LANGUAGE plpgsql STABLE;
