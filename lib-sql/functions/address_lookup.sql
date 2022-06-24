-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- Functions for returning address information for a place.

DROP TYPE IF EXISTS addressline CASCADE;
CREATE TYPE addressline as (
  place_id BIGINT,
  osm_type CHAR(1),
  osm_id BIGINT,
  name HSTORE,
  class TEXT,
  type TEXT,
  place_type TEXT,
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

  -- as a fallback - take the last element since it is the default name
  RETURN trim((avals(name))[array_length(avals(name), 1)]);
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
    SELECT name,
       CASE WHEN place_id = for_place_id THEN 99 ELSE rank_address END as rank_address
    FROM get_addressdata(for_place_id, housenumber)
    WHERE isaddress order by rank_address desc
  LOOP
    currresult := trim(get_name_by_language(location.name, languagepref));
    IF currresult != prevresult AND currresult IS NOT NULL
       AND result[(100 - location.rank_address)] IS NULL
    THEN
      result[(100 - location.rank_address)] := currresult;
      prevresult := currresult;
    END IF;
  END LOOP;

  RETURN array_to_string(result,', ');
END;
$$
LANGUAGE plpgsql STABLE;

DROP TYPE IF EXISTS addressdata_place;
CREATE TYPE addressdata_place AS (
  place_id BIGINT,
  country_code VARCHAR(2),
  housenumber TEXT,
  postcode TEXT,
  class TEXT,
  type TEXT,
  name HSTORE,
  address HSTORE,
  centroid GEOMETRY
);

-- Compute the list of address parts for the given place.
--
-- If in_housenumber is greator or equal 0, look for an interpolation.
CREATE OR REPLACE FUNCTION get_addressdata(in_place_id BIGINT, in_housenumber INTEGER)
  RETURNS setof addressline
  AS $$
DECLARE
  place addressdata_place;
  location RECORD;
  country RECORD;
  current_rank_address INTEGER;
  location_isaddress BOOLEAN;
BEGIN
  -- The place in question might not have a direct entry in place_addressline.
  -- Look for the parent of such places then and save it in place.

  -- first query osmline (interpolation lines)
  IF in_housenumber >= 0 THEN
    SELECT parent_place_id as place_id, country_code,
           in_housenumber as housenumber, postcode,
           'place' as class, 'house' as type,
           null as name, null as address,
           ST_Centroid(linegeo) as centroid
      INTO place
      FROM location_property_osmline
      WHERE place_id = in_place_id
            AND in_housenumber between startnumber and endnumber;
  END IF;

  --then query tiger data
  {% if config.get_bool('USE_US_TIGER_DATA') %}
  IF place IS NULL AND in_housenumber >= 0 THEN
    SELECT parent_place_id as place_id, 'us' as country_code,
           in_housenumber as housenumber, postcode,
           'place' as class, 'house' as type,
           null as name, null as address,
           ST_Centroid(linegeo) as centroid
      INTO place
      FROM location_property_tiger
      WHERE place_id = in_place_id
            AND in_housenumber between startnumber and endnumber;
  END IF;
  {% endif %}

  -- postcode table
  IF place IS NULL THEN
    SELECT parent_place_id as place_id, country_code,
           null::text as housenumber, postcode,
           'place' as class, 'postcode' as type,
           null as name, null as address,
           null as centroid
      INTO place
      FROM location_postcode
      WHERE place_id = in_place_id;
  END IF;

  -- POI objects in the placex table
  IF place IS NULL THEN
    SELECT parent_place_id as place_id, country_code,
           coalesce(address->'housenumber',
                    address->'streetnumber',
                    address->'conscriptionnumber')::text as housenumber,
           postcode,
           class, type,
           name, address,
           centroid
      INTO place
      FROM placex
      WHERE place_id = in_place_id and rank_search > 27;
  END IF;

  -- If place is still NULL at this point then the object has its own
  -- entry in place_address line. However, still check if there is not linked
  -- place we should be using instead.
  IF place IS NULL THEN
    select coalesce(linked_place_id, place_id) as place_id,  country_code,
           null::text as housenumber, postcode,
           class, type,
           null as name, address,
           null as centroid
      INTO place
      FROM placex where place_id = in_place_id;
  END IF;

--RAISE WARNING '% % % %',searchcountrycode, searchhousenumber, searchpostcode;

  -- --- Return the record for the base entry.

  FOR location IN
    SELECT placex.place_id, osm_type, osm_id, name,
           coalesce(extratags->'linked_place', extratags->'place') as place_type,
           class, type, admin_level,
           CASE WHEN rank_address = 0 THEN 100
                WHEN rank_address = 11 THEN 5
                ELSE rank_address END as rank_address,
           country_code
      FROM placex
      WHERE place_id = place.place_id
  LOOP
--RAISE WARNING '%',location;
    -- mix in default names for countries
    IF location.rank_address = 4 and place.country_code is not NULL THEN
      FOR country IN
        SELECT coalesce(name, ''::hstore) as name FROM country_name
          WHERE country_code = place.country_code LIMIT 1
      LOOP
        place.name := country.name || place.name;
      END LOOP;
    END IF;

    IF location.rank_address < 4 THEN
      -- no country locations for ranks higher than country
      place.country_code := NULL::varchar(2);
    ELSEIF place.country_code IS NULL AND location.country_code IS NOT NULL THEN
      place.country_code := location.country_code;
    END IF;

    RETURN NEXT ROW(location.place_id, location.osm_type, location.osm_id,
                    location.name, location.class, location.type,
                    location.place_type,
                    location.admin_level, true,
                    location.type not in ('postcode', 'postal_code'),
                    location.rank_address, 0)::addressline;

    current_rank_address := location.rank_address;
  END LOOP;

  -- --- Return records for address parts.

  FOR location IN
    SELECT placex.place_id, osm_type, osm_id, name, class, type,
           coalesce(extratags->'linked_place', extratags->'place') as place_type,
           admin_level, fromarea, isaddress,
           CASE WHEN rank_address = 11 THEN 5 ELSE rank_address END as rank_address,
           distance, country_code, postcode
      FROM place_addressline join placex on (address_place_id = placex.place_id)
      WHERE place_addressline.place_id IN (place.place_id, in_place_id)
            AND linked_place_id is null
            AND (placex.country_code IS NULL OR place.country_code IS NULL
                 OR placex.country_code = place.country_code)
      ORDER BY rank_address desc,
               (place_addressline.place_id = in_place_id) desc,
               (CASE WHEN coalesce((avals(name) && avals(place.address)), False) THEN 2
                     WHEN isaddress THEN 0
                     WHEN fromarea
                          and place.centroid is not null
                          and ST_Contains(geometry, place.centroid) THEN 1
                     ELSE -1 END) desc,
               fromarea desc, distance asc, rank_search desc
  LOOP
    -- RAISE WARNING '%',location;
    location_isaddress := location.rank_address != current_rank_address;

    IF place.country_code IS NULL AND location.country_code IS NOT NULL THEN
      place.country_code := location.country_code;
    END IF;
    IF location.type in ('postcode', 'postal_code')
       AND place.postcode is not null
    THEN
      -- If the place had a postcode assigned, take this one only
      -- into consideration when it is an area and the place does not have
      -- a postcode itself.
      IF location.fromarea AND location.isaddress
         AND (place.address is null or not place.address ? 'postcode')
      THEN
        place.postcode := null; -- remove the less exact postcode
      ELSE
        location_isaddress := false;
      END IF;
    END IF;
    RETURN NEXT ROW(location.place_id, location.osm_type, location.osm_id,
                    location.name, location.class, location.type,
                    location.place_type,
                    location.admin_level, location.fromarea,
                    location_isaddress,
                    location.rank_address,
                    location.distance)::addressline;

    current_rank_address := location.rank_address;
  END LOOP;

  -- If no country was included yet, add the name information from country_name.
  IF current_rank_address > 4 THEN
    FOR location IN
      SELECT name || coalesce(derived_name, ''::hstore) as name FROM country_name
        WHERE country_code = place.country_code LIMIT 1
    LOOP
--RAISE WARNING '% % %',current_rank_address,searchcountrycode,countryname;
      RETURN NEXT ROW(null, null, null, location.name, 'place', 'country', NULL,
                      null, true, true, 4, 0)::addressline;
    END LOOP;
  END IF;

  -- Finally add some artificial rows.
  IF place.country_code IS NOT NULL THEN
    location := ROW(null, null, null, hstore('ref', place.country_code),
                    'place', 'country_code', null, null, true, false, 4, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF place.name IS NOT NULL THEN
    location := ROW(in_place_id, null, null, place.name, place.class,
                    place.type, null, null, true, true, 29, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF place.housenumber IS NOT NULL THEN
    location := ROW(null, null, null, hstore('ref', place.housenumber),
                    'place', 'house_number', null, null, true, true, 28, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF place.address is not null and place.address ? '_unlisted_place' THEN
    RETURN NEXT ROW(null, null, null, hstore('name', place.address->'_unlisted_place'),
                    'place', 'locality', null, null, true, true, 25, 0)::addressline;
  END IF;

  IF place.postcode is not null THEN
    location := ROW(null, null, null, hstore('ref', place.postcode), 'place',
                    'postcode', null, null, false, true, 5, 0)::addressline;
    RETURN NEXT location;
  ELSEIF place.address is not null and place.address ? 'postcode'
         and not place.address->'postcode' SIMILAR TO '%(,|;)%' THEN
    location := ROW(null, null, null, hstore('ref', place.address->'postcode'), 'place',
                    'postcode', null, null, false, true, 5, 0)::addressline;
    RETURN NEXT location;
  END IF;

  RETURN;
END;
$$
LANGUAGE plpgsql STABLE;
