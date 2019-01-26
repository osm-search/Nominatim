-- Splits the line at the given point and returns the two parts
-- in a multilinestring.
CREATE OR REPLACE FUNCTION split_line_on_node(line GEOMETRY, point GEOMETRY)
RETURNS GEOMETRY
  AS $$
BEGIN
  RETURN ST_Split(ST_Snap(line, point, 0.0005), point);
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION geometry_sector(partition INTEGER, place geometry) RETURNS INTEGER
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

CREATE OR REPLACE FUNCTION transliteration(text) RETURNS text
  AS '{modulepath}/nominatim.so', 'transliteration'
LANGUAGE c IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION gettokenstring(text) RETURNS text
  AS '{modulepath}/nominatim.so', 'gettokenstring'
LANGUAGE c IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION make_standard_name(name TEXT) RETURNS TEXT
  AS $$
DECLARE
  o TEXT;
BEGIN
  o := public.gettokenstring(public.transliteration(name));
  RETURN trim(substr(o,1,length(o)));
END;
$$
LANGUAGE 'plpgsql' IMMUTABLE;

-- returns NULL if the word is too common
CREATE OR REPLACE FUNCTION getorcreate_word_id(lookup_word TEXT) 
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
  count INTEGER;
BEGIN
  lookup_token := trim(lookup_word);
  SELECT min(word_id), max(search_name_count) FROM word WHERE word_token = lookup_token and class is null and type is null into return_word_id, count;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, null, null, null, null, 0);
  ELSE
    IF count > get_maxwordfreq() THEN
      return_word_id := NULL;
    END IF;
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_housenumber_id(lookup_word TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and class='place' and type='house' into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, null, 'place', 'house', null, 0);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_postcode_id(postcode TEXT)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  lookup_word TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_word := upper(trim(postcode));
  lookup_token := ' ' || make_standard_name(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and class='place' and type='postcode' into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, lookup_word, 'place', 'postcode', null, 0);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_country(lookup_word TEXT, lookup_country_code varchar(2))
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and country_code=lookup_country_code into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, null, null, null, lookup_country_code, 0);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_amenity(lookup_word TEXT, normalized_word TEXT, lookup_class text, lookup_type text)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and word=normalized_word and class=lookup_class and type = lookup_type into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, normalized_word, lookup_class, lookup_type, null, 0);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_amenityoperator(lookup_word TEXT, normalized_word TEXT, lookup_class text, lookup_type text, op text)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and word=normalized_word and class=lookup_class and type = lookup_type and operator = op into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, normalized_word, lookup_class, lookup_type, null, 0, op);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_name_id(lookup_word TEXT, src_word TEXT) 
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  nospace_lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and class is null and type is null into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, src_word, null, null, null, 0);
--    nospace_lookup_token := replace(replace(lookup_token, '-',''), ' ','');
--    IF ' '||nospace_lookup_token != lookup_token THEN
--      INSERT INTO word VALUES (return_word_id, '-'||nospace_lookup_token, null, src_word, null, null, null, 0, null);
--    END IF;
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_name_id(lookup_word TEXT) 
  RETURNS INTEGER
  AS $$
DECLARE
BEGIN
  RETURN getorcreate_name_id(lookup_word, '');
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_word_id(lookup_word TEXT) 
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and class is null and type is null into return_word_id;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_name_id(lookup_word TEXT) 
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and class is null and type is null into return_word_id;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_name_ids(lookup_word TEXT)
  RETURNS INTEGER[]
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_ids INTEGER[];
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT array_agg(word_id) FROM word WHERE word_token = lookup_token and class is null and type is null into return_word_ids;
  RETURN return_word_ids;
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

CREATE OR REPLACE FUNCTION reverse_place_diameter(rank_search SMALLINT)
  RETURNS FLOAT
  AS $$
BEGIN
  IF rank_search <= 4 THEN
    RETURN 5.0;
  ELSIF rank_search <= 8 THEN
    RETURN 1.8;
  ELSIF rank_search <= 12 THEN
    RETURN 0.6;
  ELSIF rank_search <= 17 THEN
    RETURN 0.16;
  ELSIF rank_search <= 18 THEN
    RETURN 0.08;
  ELSIF rank_search <= 19 THEN
    RETURN 0.04;
  END IF;

  RETURN 0.02;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_postcode_rank(country_code VARCHAR(2), postcode TEXT,
                                      OUT rank_search SMALLINT, OUT rank_address SMALLINT)
AS $$
DECLARE
  part TEXT;
BEGIN
    rank_search := 30;
    rank_address := 30;
    postcode := upper(postcode);

    IF country_code = 'gb' THEN
        IF postcode ~ '^([A-Z][A-Z]?[0-9][0-9A-Z]? [0-9][A-Z][A-Z])$' THEN
            rank_search := 25;
            rank_address := 5;
        ELSEIF postcode ~ '^([A-Z][A-Z]?[0-9][0-9A-Z]? [0-9])$' THEN
            rank_search := 23;
            rank_address := 5;
        ELSEIF postcode ~ '^([A-Z][A-Z]?[0-9][0-9A-Z])$' THEN
            rank_search := 21;
            rank_address := 5;
        END IF;

    ELSEIF country_code = 'sg' THEN
        IF postcode ~ '^([0-9]{6})$' THEN
            rank_search := 25;
            rank_address := 11;
        END IF;

    ELSEIF country_code = 'de' THEN
        IF postcode ~ '^([0-9]{5})$' THEN
            rank_search := 21;
            rank_address := 11;
        END IF;

    ELSE
        -- Guess at the postcode format and coverage (!)
        IF postcode ~ '^[A-Z0-9]{1,5}$' THEN -- Probably too short to be very local
            rank_search := 21;
            rank_address := 11;
        ELSE
            -- Does it look splitable into and area and local code?
            part := substring(postcode from '^([- :A-Z0-9]+)([- :][A-Z0-9]+)$');

            IF part IS NOT NULL THEN
                rank_search := 25;
                rank_address := 11;
            ELSEIF postcode ~ '^[- :A-Z0-9]{6,}$' THEN
                rank_search := 21;
                rank_address := 11;
            END IF;
        END IF;
    END IF;

END;
$$
LANGUAGE plpgsql IMMUTABLE;

-- Find the nearest artificial postcode for the given geometry.
-- TODO For areas there should not be more than two inside the geometry.
CREATE OR REPLACE FUNCTION get_nearest_postcode(country VARCHAR(2), geom GEOMETRY) RETURNS TEXT
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
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION create_country(src HSTORE, lookup_country_code varchar(2)) RETURNS VOID
  AS $$
DECLARE
  s TEXT;
  w INTEGER;
  words TEXT[];
  item RECORD;
  j INTEGER;
BEGIN
  FOR item IN SELECT (each(src)).* LOOP

    s := make_standard_name(item.value);
    w := getorcreate_country(s, lookup_country_code);

    words := regexp_split_to_array(item.value, E'[,;()]');
    IF array_upper(words, 1) != 1 THEN
      FOR j IN 1..array_upper(words, 1) LOOP
        s := make_standard_name(words[j]);
        IF s != '' THEN
          w := getorcreate_country(s, lookup_country_code);
        END IF;
      END LOOP;
    END IF;
  END LOOP;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION make_keywords(src HSTORE) RETURNS INTEGER[]
  AS $$
DECLARE
  result INTEGER[];
  s TEXT;
  w INTEGER;
  words TEXT[];
  item RECORD;
  j INTEGER;
BEGIN
  result := '{}'::INTEGER[];

  FOR item IN SELECT (each(src)).* LOOP

    s := make_standard_name(item.value);

    w := getorcreate_name_id(s, item.value);

    IF not(ARRAY[w] <@ result) THEN
      result := result || w;
    END IF;

    w := getorcreate_word_id(s);

    IF w IS NOT NULL AND NOT (ARRAY[w] <@ result) THEN
      result := result || w;
    END IF;

    words := string_to_array(s, ' ');
    IF array_upper(words, 1) IS NOT NULL THEN
      FOR j IN 1..array_upper(words, 1) LOOP
        IF (words[j] != '') THEN
          w = getorcreate_word_id(words[j]);
          IF w IS NOT NULL AND NOT (ARRAY[w] <@ result) THEN
            result := result || w;
          END IF;
        END IF;
      END LOOP;
    END IF;

    words := regexp_split_to_array(item.value, E'[,;()]');
    IF array_upper(words, 1) != 1 THEN
      FOR j IN 1..array_upper(words, 1) LOOP
        s := make_standard_name(words[j]);
        IF s != '' THEN
          w := getorcreate_word_id(s);
          IF w IS NOT NULL AND NOT (ARRAY[w] <@ result) THEN
            result := result || w;
          END IF;
        END IF;
      END LOOP;
    END IF;

    s := regexp_replace(item.value, '市$', '');
    IF s != item.value THEN
      s := make_standard_name(s);
      IF s != '' THEN
        w := getorcreate_name_id(s, item.value);
        IF NOT (ARRAY[w] <@ result) THEN
          result := result || w;
        END IF;
      END IF;
    END IF;

  END LOOP;

  RETURN result;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION make_keywords(src TEXT) RETURNS INTEGER[]
  AS $$
DECLARE
  result INTEGER[];
  s TEXT;
  w INTEGER;
  words TEXT[];
  i INTEGER;
  j INTEGER;
BEGIN
  result := '{}'::INTEGER[];

  s := make_standard_name(src);
  w := getorcreate_name_id(s, src);

  IF NOT (ARRAY[w] <@ result) THEN
    result := result || w;
  END IF;

  w := getorcreate_word_id(s);

  IF w IS NOT NULL AND NOT (ARRAY[w] <@ result) THEN
    result := result || w;
  END IF;

  words := string_to_array(s, ' ');
  IF array_upper(words, 1) IS NOT NULL THEN
    FOR j IN 1..array_upper(words, 1) LOOP
      IF (words[j] != '') THEN
        w = getorcreate_word_id(words[j]);
        IF w IS NOT NULL AND NOT (ARRAY[w] <@ result) THEN
          result := result || w;
        END IF;
      END IF;
    END LOOP;
  END IF;

  words := regexp_split_to_array(src, E'[,;()]');
  IF array_upper(words, 1) != 1 THEN
    FOR j IN 1..array_upper(words, 1) LOOP
      s := make_standard_name(words[j]);
      IF s != '' THEN
        w := getorcreate_word_id(s);
        IF w IS NOT NULL AND NOT (ARRAY[w] <@ result) THEN
          result := result || w;
        END IF;
      END IF;
    END LOOP;
  END IF;

  s := regexp_replace(src, '市$', '');
  IF s != src THEN
    s := make_standard_name(s);
    IF s != '' THEN
      w := getorcreate_name_id(s, src);
      IF NOT (ARRAY[w] <@ result) THEN
        result := result || w;
      END IF;
    END IF;
  END IF;

  RETURN result;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_country_code(place geometry) RETURNS TEXT
  AS $$
DECLARE
  place_centre GEOMETRY;
  nearcountry RECORD;
BEGIN
  place_centre := ST_PointOnSurface(place);

-- RAISE WARNING 'get_country_code, start: %', ST_AsText(place_centre);

  -- Try for a OSM polygon
  FOR nearcountry IN select country_code from location_area_country where country_code is not null and not isguess and st_covers(geometry, place_centre) limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

-- RAISE WARNING 'osm fallback: %', ST_AsText(place_centre);

  -- Try for OSM fallback data
  -- The order is to deal with places like HongKong that are 'states' within another polygon
  FOR nearcountry IN select country_code from country_osm_grid where st_covers(geometry, place_centre) order by area asc limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

-- RAISE WARNING 'near osm fallback: %', ST_AsText(place_centre);

  -- 
  FOR nearcountry IN select country_code from country_osm_grid where st_dwithin(geometry, place_centre, 0.5) order by st_distance(geometry, place_centre) asc, area asc limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

  RETURN NULL;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_country_language_code(search_country_code VARCHAR(2)) RETURNS TEXT
  AS $$
DECLARE
  nearcountry RECORD;
BEGIN
  FOR nearcountry IN select distinct country_default_language_code from country_name where country_code = search_country_code limit 1
  LOOP
    RETURN lower(nearcountry.country_default_language_code);
  END LOOP;
  RETURN NULL;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_country_language_codes(search_country_code VARCHAR(2)) RETURNS TEXT[]
  AS $$
DECLARE
  nearcountry RECORD;
BEGIN
  FOR nearcountry IN select country_default_language_codes from country_name where country_code = search_country_code limit 1
  LOOP
    RETURN lower(nearcountry.country_default_language_codes);
  END LOOP;
  RETURN NULL;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_partition(in_country_code VARCHAR(10)) RETURNS INTEGER
  AS $$
DECLARE
  nearcountry RECORD;
BEGIN
  FOR nearcountry IN select partition from country_name where country_code = in_country_code
  LOOP
    RETURN nearcountry.partition;
  END LOOP;
  RETURN 0;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION delete_location(OLD_place_id BIGINT) RETURNS BOOLEAN
  AS $$
DECLARE
BEGIN
  DELETE FROM location_area where place_id = OLD_place_id;
-- TODO:location_area
  RETURN true;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_location(
    place_id BIGINT,
    country_code varchar(2),
    partition INTEGER,
    keywords INTEGER[],
    rank_search INTEGER,
    rank_address INTEGER,
    in_postcode TEXT,
    geometry GEOMETRY
  ) 
  RETURNS BOOLEAN
  AS $$
DECLARE
  locationid INTEGER;
  centroid GEOMETRY;
  diameter FLOAT;
  x BOOLEAN;
  splitGeom RECORD;
  secgeo GEOMETRY;
  postcode TEXT;
BEGIN

  IF rank_search > 25 THEN
    RAISE EXCEPTION 'Adding location with rank > 25 (% rank %)', place_id, rank_search;
  END IF;

  x := deleteLocationArea(partition, place_id, rank_search);

  -- add postcode only if it contains a single entry, i.e. ignore postcode lists
  postcode := NULL;
  IF in_postcode is not null AND in_postcode not similar to '%(,|;)%' THEN
      postcode := upper(trim (in_postcode));
  END IF;

  IF ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') THEN
    centroid := ST_Centroid(geometry);

    FOR secgeo IN select split_geometry(geometry) AS geom LOOP
      x := insertLocationAreaLarge(partition, place_id, country_code, keywords, rank_search, rank_address, false, postcode, centroid, secgeo);
    END LOOP;

  ELSE

    diameter := 0.02;
    IF rank_address = 0 THEN
      diameter := 0.02;
    ELSEIF rank_search <= 14 THEN
      diameter := 1.2;
    ELSEIF rank_search <= 15 THEN
      diameter := 1;
    ELSEIF rank_search <= 16 THEN
      diameter := 0.5;
    ELSEIF rank_search <= 17 THEN
      diameter := 0.2;
    ELSEIF rank_search <= 21 THEN
      diameter := 0.05;
    ELSEIF rank_search = 25 THEN
      diameter := 0.005;
    END IF;

--    RAISE WARNING 'adding % diameter %', place_id, diameter;

    secgeo := ST_Buffer(geometry, diameter);
    x := insertLocationAreaLarge(partition, place_id, country_code, keywords, rank_search, rank_address, true, postcode, ST_Centroid(geometry), secgeo);

  END IF;

  RETURN true;
END;
$$
LANGUAGE plpgsql;


-- find the parent road of the cut road parts
CREATE OR REPLACE FUNCTION get_interpolation_parent(wayid BIGINT, street TEXT, place TEXT,
                                                    partition INTEGER, centroid GEOMETRY, geom GEOMETRY)
RETURNS BIGINT AS $$
DECLARE
  addr_street TEXT;
  addr_place TEXT;
  parent_place_id BIGINT;
  address_street_word_ids INTEGER[];

  waynodes BIGINT[];

  location RECORD;
BEGIN
  addr_street = street;
  addr_place = place;

  IF addr_street is null and addr_place is null THEN
    select nodes from planet_osm_ways where id = wayid INTO waynodes;
    FOR location IN SELECT placex.address from placex
                    where osm_type = 'N' and osm_id = ANY(waynodes)
                          and placex.address is not null
                          and (placex.address ? 'street' or placex.address ? 'place')
                          and indexed_status < 100
                    limit 1 LOOP
      addr_street = location.address->'street';
      addr_place = location.address->'place';
    END LOOP;
  END IF;

  IF addr_street IS NOT NULL THEN
    address_street_word_ids := get_name_ids(make_standard_name(addr_street));
    IF address_street_word_ids IS NOT NULL THEN
      FOR location IN SELECT place_id from getNearestNamedRoadFeature(partition, centroid, address_street_word_ids) LOOP
        parent_place_id := location.place_id;
      END LOOP;
    END IF;
  END IF;

  IF parent_place_id IS NULL AND addr_place IS NOT NULL THEN
    address_street_word_ids := get_name_ids(make_standard_name(addr_place));
    IF address_street_word_ids IS NOT NULL THEN
      FOR location IN SELECT place_id from getNearestNamedPlaceFeature(partition, centroid, address_street_word_ids) LOOP
        parent_place_id := location.place_id;
      END LOOP;
    END IF;
  END IF;

  IF parent_place_id is null THEN
    FOR location IN SELECT place_id FROM placex
        WHERE ST_DWithin(geom, placex.geometry, 0.001) and placex.rank_search = 26
        ORDER BY (ST_distance(placex.geometry, ST_LineInterpolatePoint(geom,0))+
                  ST_distance(placex.geometry, ST_LineInterpolatePoint(geom,0.5))+
                  ST_distance(placex.geometry, ST_LineInterpolatePoint(geom,1))) ASC limit 1
    LOOP
      parent_place_id := location.place_id;
    END LOOP;
  END IF;

  IF parent_place_id is null THEN
    RETURN 0;
  END IF;

  RETURN parent_place_id;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION osmline_insert() RETURNS TRIGGER
  AS $$
BEGIN
  NEW.place_id := nextval('seq_place');
  NEW.indexed_date := now();

  IF NEW.indexed_status IS NULL THEN
      IF NEW.address is NULL OR NOT NEW.address ? 'interpolation'
         OR NEW.address->'interpolation' NOT IN ('odd', 'even', 'all') THEN
          -- other interpolation types than odd/even/all (e.g. numeric ones) are not supported
          RETURN NULL;
      END IF;

      NEW.indexed_status := 1; --STATUS_NEW
      NEW.country_code := lower(get_country_code(NEW.linegeo));

      NEW.partition := get_partition(NEW.country_code);
      NEW.geometry_sector := geometry_sector(NEW.partition, NEW.linegeo);
  END IF;

  RETURN NEW;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION placex_insert() RETURNS TRIGGER
  AS $$
DECLARE
  i INTEGER;
  postcode TEXT;
  result BOOLEAN;
  is_area BOOLEAN;
  country_code VARCHAR(2);
  default_language VARCHAR(10);
  diameter FLOAT;
  classtable TEXT;
  classtype TEXT;
BEGIN
  --DEBUG: RAISE WARNING '% % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;

  NEW.place_id := nextval('seq_place');
  NEW.indexed_status := 1; --STATUS_NEW

  NEW.country_code := lower(get_country_code(NEW.geometry));

  NEW.partition := get_partition(NEW.country_code);
  NEW.geometry_sector := geometry_sector(NEW.partition, NEW.geometry);

  -- copy 'name' to or from the default language (if there is a default language)
  IF NEW.name is not null AND array_upper(akeys(NEW.name),1) > 1 THEN
    default_language := get_country_language_code(NEW.country_code);
    IF default_language IS NOT NULL THEN
      IF NEW.name ? 'name' AND NOT NEW.name ? ('name:'||default_language) THEN
        NEW.name := NEW.name || hstore(('name:'||default_language), (NEW.name -> 'name'));
      ELSEIF NEW.name ? ('name:'||default_language) AND NOT NEW.name ? 'name' THEN
        NEW.name := NEW.name || hstore('name', (NEW.name -> ('name:'||default_language)));
      END IF;
    END IF;
  END IF;

  IF NEW.osm_type = 'X' THEN
    -- E'X'ternal records should already be in the right format so do nothing
  ELSE
    is_area := ST_GeometryType(NEW.geometry) IN ('ST_Polygon','ST_MultiPolygon');

    IF NEW.class in ('place','boundary')
       AND NEW.type in ('postcode','postal_code') THEN

      IF NEW.address IS NULL OR NOT NEW.address ? 'postcode' THEN
          -- most likely just a part of a multipolygon postcode boundary, throw it away
          RETURN NULL;
      END IF;

      NEW.name := hstore('ref', NEW.address->'postcode');

      SELECT * FROM get_postcode_rank(NEW.country_code, NEW.address->'postcode')
        INTO NEW.rank_search, NEW.rank_address;

      IF NOT is_area THEN
          NEW.rank_address := 0;
      END IF;
    ELSEIF NEW.class = 'boundary' AND NOT is_area THEN
        return NULL;
    ELSEIF NEW.class = 'boundary' AND NEW.type = 'administrative'
           AND NEW.admin_level <= 4 AND NEW.osm_type = 'W' THEN
        return NULL;
    ELSEIF NEW.class = 'railway' AND NEW.type in ('rail') THEN
        return NULL;
    ELSEIF NEW.osm_type = 'N' AND NEW.class = 'highway' THEN
        NEW.rank_search = 30;
        NEW.rank_address = 0;
    ELSEIF NEW.class = 'landuse' AND NOT is_area THEN
        NEW.rank_search = 30;
        NEW.rank_address = 0;
    ELSE
      -- do table lookup stuff
      IF NEW.class = 'boundary' and NEW.type = 'administrative' THEN
        classtype = NEW.type || NEW.admin_level::TEXT;
      ELSE
        classtype = NEW.type;
      END IF;
      SELECT l.rank_search, l.rank_address FROM address_levels l
       WHERE (l.country_code = NEW.country_code or l.country_code is NULL)
             AND l.class = NEW.class AND (l.type = classtype or l.type is NULL)
       ORDER BY l.country_code, l.class, l.type LIMIT 1
        INTO NEW.rank_search, NEW.rank_address;

      IF NEW.rank_search is NULL THEN
        NEW.rank_search := 30;
      END IF;

      IF NEW.rank_address is NULL THEN
        NEW.rank_address := 30;
      END IF;
    END IF;

    -- some postcorrections
    IF NEW.class = 'place' THEN
      IF NEW.type in ('continent', 'sea', 'country', 'state') AND NEW.osm_type = 'N' THEN
        NEW.rank_address := 0;
      END IF;
    ELSEIF NEW.class = 'waterway' AND NEW.osm_type = 'R' THEN
        -- Slightly promote waterway relations so that they are processed
        -- before their members.
        NEW.rank_search := NEW.rank_search - 1;
    END IF;

    IF (NEW.extratags -> 'capital') = 'yes' THEN
      NEW.rank_search := NEW.rank_search - 1;
    END IF;

  END IF;

  -- a country code make no sense below rank 4 (country)
  IF NEW.rank_search < 4 THEN
    NEW.country_code := NULL;
  END IF;

-- Block import below rank 22
--  IF NEW.rank_search > 22 THEN
--    RETURN NULL;
--  END IF;

  --DEBUG: RAISE WARNING 'placex_insert:END: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;

  RETURN NEW; -- %DIFFUPDATES% The following is not needed until doing diff updates, and slows the main index process down

  IF NEW.rank_address > 0 THEN
    IF (ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon') AND ST_IsValid(NEW.geometry)) THEN
      -- Performance: We just can't handle re-indexing for country level changes
      IF st_area(NEW.geometry) < 1 THEN
        -- mark items within the geometry for re-indexing
  --    RAISE WARNING 'placex poly insert: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;

        -- work around bug in postgis, this may have been fixed in 2.0.0 (see http://trac.osgeo.org/postgis/ticket/547)
        update placex set indexed_status = 2 where (st_covers(NEW.geometry, placex.geometry) OR ST_Intersects(NEW.geometry, placex.geometry)) 
         AND rank_search > NEW.rank_search and indexed_status = 0 and ST_geometrytype(placex.geometry) = 'ST_Point' and (rank_search < 28 or name is not null or (NEW.rank_search >= 16 and address ? 'place'));
        update placex set indexed_status = 2 where (st_covers(NEW.geometry, placex.geometry) OR ST_Intersects(NEW.geometry, placex.geometry)) 
         AND rank_search > NEW.rank_search and indexed_status = 0 and ST_geometrytype(placex.geometry) != 'ST_Point' and (rank_search < 28 or name is not null or (NEW.rank_search >= 16 and address ? 'place'));
      END IF;
    ELSE
      -- mark nearby items for re-indexing, where 'nearby' depends on the features rank_search and is a complete guess :(
      diameter := 0;
      -- 16 = city, anything higher than city is effectively ignored (polygon required!)
      IF NEW.type='postcode' THEN
        diameter := 0.05;
      ELSEIF NEW.rank_search < 16 THEN
        diameter := 0;
      ELSEIF NEW.rank_search < 18 THEN
        diameter := 0.1;
      ELSEIF NEW.rank_search < 20 THEN
        diameter := 0.05;
      ELSEIF NEW.rank_search = 21 THEN
        diameter := 0.001;
      ELSEIF NEW.rank_search < 24 THEN
        diameter := 0.02;
      ELSEIF NEW.rank_search < 26 THEN
        diameter := 0.002; -- 100 to 200 meters
      ELSEIF NEW.rank_search < 28 THEN
        diameter := 0.001; -- 50 to 100 meters
      END IF;
      IF diameter > 0 THEN
  --      RAISE WARNING 'placex point insert: % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,diameter;
        IF NEW.rank_search >= 26 THEN
          -- roads may cause reparenting for >27 rank places
          update placex set indexed_status = 2 where indexed_status = 0 and rank_search > NEW.rank_search and ST_DWithin(placex.geometry, NEW.geometry, diameter);
          -- reparenting also for OSM Interpolation Lines (and for Tiger?)
          update location_property_osmline set indexed_status = 2 where indexed_status = 0 and ST_DWithin(location_property_osmline.linegeo, NEW.geometry, diameter);
        ELSEIF NEW.rank_search >= 16 THEN
          -- up to rank 16, street-less addresses may need reparenting
          update placex set indexed_status = 2 where indexed_status = 0 and rank_search > NEW.rank_search and ST_DWithin(placex.geometry, NEW.geometry, diameter) and (rank_search < 28 or name is not null or address ? 'place');
        ELSE
          -- for all other places the search terms may change as well
          update placex set indexed_status = 2 where indexed_status = 0 and rank_search > NEW.rank_search and ST_DWithin(placex.geometry, NEW.geometry, diameter) and (rank_search < 28 or name is not null);
        END IF;
      END IF;
    END IF;
  END IF;


   -- add to tables for special search
   -- Note: won't work on initial import because the classtype tables
   -- do not yet exist. It won't hurt either.
  classtable := 'place_classtype_' || NEW.class || '_' || NEW.type;
  SELECT count(*)>0 FROM pg_tables WHERE tablename = classtable and schemaname = current_schema() INTO result;
  IF result THEN
    EXECUTE 'INSERT INTO ' || classtable::regclass || ' (place_id, centroid) VALUES ($1,$2)' 
    USING NEW.place_id, ST_Centroid(NEW.geometry);
  END IF;

  RETURN NEW;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION osmline_update() RETURNS 
TRIGGER
  AS $$
DECLARE
  place_centroid GEOMETRY;
  waynodes BIGINT[];
  prevnode RECORD;
  nextnode RECORD;
  startnumber INTEGER;
  endnumber INTEGER;
  housenum INTEGER;
  linegeo GEOMETRY;
  splitline GEOMETRY;
  sectiongeo GEOMETRY;
  interpol_postcode TEXT;
  postcode TEXT;
BEGIN
  -- deferred delete
  IF OLD.indexed_status = 100 THEN
    delete from location_property_osmline where place_id = OLD.place_id;
    RETURN NULL;
  END IF;

  IF NEW.indexed_status != 0 OR OLD.indexed_status = 0 THEN
    RETURN NEW;
  END IF;

  NEW.interpolationtype = NEW.address->'interpolation';

  place_centroid := ST_PointOnSurface(NEW.linegeo);
  NEW.parent_place_id = get_interpolation_parent(NEW.osm_id, NEW.address->'street',
                                                 NEW.address->'place',
                                                 NEW.partition, place_centroid, NEW.linegeo);

  IF NEW.address is not NULL AND NEW.address ? 'postcode' AND NEW.address->'postcode' not similar to '%(,|;)%' THEN
    interpol_postcode := NEW.address->'postcode';
    housenum := getorcreate_postcode_id(NEW.address->'postcode');
  ELSE
    interpol_postcode := NULL;
  END IF;

  -- if the line was newly inserted, split the line as necessary
  IF OLD.indexed_status = 1 THEN
      select nodes from planet_osm_ways where id = NEW.osm_id INTO waynodes;

      IF array_upper(waynodes, 1) IS NULL THEN
        RETURN NEW;
      END IF;

      linegeo := NEW.linegeo;
      startnumber := NULL;

      FOR nodeidpos in 1..array_upper(waynodes, 1) LOOP

        select osm_id, address, geometry
          from place where osm_type = 'N' and osm_id = waynodes[nodeidpos]::BIGINT
                           and address is not NULL and address ? 'housenumber' limit 1 INTO nextnode;
        --RAISE NOTICE 'Nextnode.place_id: %s', nextnode.place_id;
        IF nextnode.osm_id IS NOT NULL THEN
          --RAISE NOTICE 'place_id is not null';
          IF nodeidpos > 1 and nodeidpos < array_upper(waynodes, 1) THEN
            -- Make sure that the point is actually on the line. That might
            -- be a bit paranoid but ensures that the algorithm still works
            -- should osm2pgsql attempt to repair geometries.
            splitline := split_line_on_node(linegeo, nextnode.geometry);
            sectiongeo := ST_GeometryN(splitline, 1);
            linegeo := ST_GeometryN(splitline, 2);
          ELSE
            sectiongeo = linegeo;
          END IF;
          endnumber := substring(nextnode.address->'housenumber','[0-9]+')::integer;

          IF startnumber IS NOT NULL AND endnumber IS NOT NULL
             AND startnumber != endnumber
             AND ST_GeometryType(sectiongeo) = 'ST_LineString' THEN

            IF (startnumber > endnumber) THEN
              housenum := endnumber;
              endnumber := startnumber;
              startnumber := housenum;
              sectiongeo := ST_Reverse(sectiongeo);
            END IF;

            -- determine postcode
            postcode := coalesce(interpol_postcode,
                                 prevnode.address->'postcode',
                                 nextnode.address->'postcode',
                                 postcode);

            IF postcode is NULL THEN
                SELECT placex.postcode FROM placex WHERE place_id = NEW.parent_place_id INTO postcode;
            END IF;
            IF postcode is NULL THEN
                postcode := get_nearest_postcode(NEW.country_code, nextnode.geometry);
            END IF;

            IF NEW.startnumber IS NULL THEN
                NEW.startnumber := startnumber;
                NEW.endnumber := endnumber;
                NEW.linegeo := sectiongeo;
                NEW.postcode := upper(trim(postcode));
             ELSE
              insert into location_property_osmline
                     (linegeo, partition, osm_id, parent_place_id,
                      startnumber, endnumber, interpolationtype,
                      address, postcode, country_code,
                      geometry_sector, indexed_status)
              values (sectiongeo, NEW.partition, NEW.osm_id, NEW.parent_place_id,
                      startnumber, endnumber, NEW.interpolationtype,
                      NEW.address, postcode,
                      NEW.country_code, NEW.geometry_sector, 0);
             END IF;
          END IF;

          -- early break if we are out of line string,
          -- might happen when a line string loops back on itself
          IF ST_GeometryType(linegeo) != 'ST_LineString' THEN
              RETURN NEW;
          END IF;

          startnumber := substring(nextnode.address->'housenumber','[0-9]+')::integer;
          prevnode := nextnode;
        END IF;
      END LOOP;
  END IF;

  -- marking descendants for reparenting is not needed, because there are
  -- actually no descendants for interpolation lines
  RETURN NEW;
END;
$$
LANGUAGE plpgsql;

-- Trigger for updates of location_postcode
--
-- Computes the parent object the postcode most likely refers to.
-- This will be the place that determines the address displayed when
-- searching for this postcode.
CREATE OR REPLACE FUNCTION postcode_update() RETURNS
TRIGGER
  AS $$
DECLARE
  partition SMALLINT;
  location RECORD;
BEGIN
    IF NEW.indexed_status != 0 OR OLD.indexed_status = 0 THEN
        RETURN NEW;
    END IF;

    NEW.indexed_date = now();

    partition := get_partition(NEW.country_code);

    SELECT * FROM get_postcode_rank(NEW.country_code, NEW.postcode)
      INTO NEW.rank_search, NEW.rank_address;

    NEW.parent_place_id = 0;
    FOR location IN
      SELECT place_id
        FROM getNearFeatures(partition, NEW.geometry, NEW.rank_search, '{}'::int[])
        WHERE NOT isguess ORDER BY rank_address DESC LIMIT 1
    LOOP
        NEW.parent_place_id = location.place_id;
    END LOOP;

    RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION placex_update() RETURNS
TRIGGER
  AS $$
DECLARE

  place_centroid GEOMETRY;

  search_maxdistance FLOAT[];
  search_mindistance FLOAT[];
  address_havelevel BOOLEAN[];

  i INTEGER;
  iMax FLOAT;
  location RECORD;
  way RECORD;
  relation RECORD;
  relation_members TEXT[];
  relMember RECORD;
  linkedplacex RECORD;
  addr_item RECORD;
  search_diameter FLOAT;
  search_prevdiameter FLOAT;
  search_maxrank INTEGER;
  address_maxrank INTEGER;
  address_street_word_id INTEGER;
  address_street_word_ids INTEGER[];
  parent_place_id_rank BIGINT;

  addr_street TEXT;
  addr_place TEXT;

  isin TEXT[];
  isin_tokens INT[];

  location_rank_search INTEGER;
  location_distance FLOAT;
  location_parent GEOMETRY;
  location_isaddress BOOLEAN;
  location_keywords INTEGER[];

  default_language TEXT;
  name_vector INTEGER[];
  nameaddress_vector INTEGER[];

  linked_node_id BIGINT;
  linked_importance FLOAT;
  linked_wikipedia TEXT;

  result BOOLEAN;
BEGIN
  -- deferred delete
  IF OLD.indexed_status = 100 THEN
    --DEBUG: RAISE WARNING 'placex_update delete % %',NEW.osm_type,NEW.osm_id;
    delete from placex where place_id = OLD.place_id;
    RETURN NULL;
  END IF;

  IF NEW.indexed_status != 0 OR OLD.indexed_status = 0 THEN
    RETURN NEW;
  END IF;

  --DEBUG: RAISE WARNING 'placex_update % % (%)',NEW.osm_type,NEW.osm_id,NEW.place_id;

  NEW.indexed_date = now();

  IF NOT %REVERSE-ONLY% THEN
    DELETE from search_name WHERE place_id = NEW.place_id;
  END IF;
  result := deleteSearchName(NEW.partition, NEW.place_id);
  DELETE FROM place_addressline WHERE place_id = NEW.place_id;
  result := deleteRoad(NEW.partition, NEW.place_id);
  result := deleteLocationArea(NEW.partition, NEW.place_id, NEW.rank_search);
  UPDATE placex set linked_place_id = null, indexed_status = 2
         where linked_place_id = NEW.place_id;
  -- update not necessary for osmline, cause linked_place_id does not exist

  IF NEW.linked_place_id is not null THEN
    --DEBUG: RAISE WARNING 'place already linked to %', NEW.linked_place_id;
    RETURN NEW;
  END IF;

  --DEBUG: RAISE WARNING 'Copy over address tags';
  IF NEW.address is not NULL THEN
      IF NEW.address ? 'conscriptionnumber' THEN
        i := getorcreate_housenumber_id(make_standard_name(NEW.address->'conscriptionnumber'));
        IF NEW.address ? 'streetnumber' THEN
            i := getorcreate_housenumber_id(make_standard_name(NEW.address->'streetnumber'));
            NEW.housenumber := (NEW.address->'conscriptionnumber') || '/' || (NEW.address->'streetnumber');
        ELSE
            NEW.housenumber := NEW.address->'conscriptionnumber';
        END IF;
      ELSEIF NEW.address ? 'streetnumber' THEN
        NEW.housenumber := NEW.address->'streetnumber';
        i := getorcreate_housenumber_id(make_standard_name(NEW.address->'streetnumber'));
      ELSEIF NEW.address ? 'housenumber' THEN
        NEW.housenumber := NEW.address->'housenumber';
        i := getorcreate_housenumber_id(make_standard_name(NEW.housenumber));
      END IF;

      addr_street := NEW.address->'street';
      addr_place := NEW.address->'place';

      IF NEW.address ? 'postcode' and NEW.address->'postcode' not similar to '%(,|;)%' THEN
        i := getorcreate_postcode_id(NEW.address->'postcode');
      END IF;
  END IF;

  -- Speed up searches - just use the centroid of the feature
  -- cheaper but less acurate
  place_centroid := ST_PointOnSurface(NEW.geometry);
  NEW.centroid := null;
  NEW.postcode := null;
  --DEBUG: RAISE WARNING 'Computing preliminary centroid at %',ST_AsText(place_centroid);

  -- recalculate country and partition
  IF NEW.rank_search = 4 AND NEW.address is not NULL AND NEW.address ? 'country' THEN
    -- for countries, believe the mapped country code,
    -- so that we remain in the right partition if the boundaries
    -- suddenly expand.
    NEW.country_code := lower(NEW.address->'country');
    NEW.partition := get_partition(lower(NEW.country_code));
    IF NEW.partition = 0 THEN
      NEW.country_code := lower(get_country_code(place_centroid));
      NEW.partition := get_partition(NEW.country_code);
    END IF;
  ELSE
    IF NEW.rank_search >= 4 THEN
      NEW.country_code := lower(get_country_code(place_centroid));
    ELSE
      NEW.country_code := NULL;
    END IF;
    NEW.partition := get_partition(NEW.country_code);
  END IF;
  --DEBUG: RAISE WARNING 'Country updated: "%"', NEW.country_code;

  -- waterway ways are linked when they are part of a relation and have the same class/type
  IF NEW.osm_type = 'R' and NEW.class = 'waterway' THEN
      FOR relation_members IN select members from planet_osm_rels r where r.id = NEW.osm_id and r.parts != array[]::bigint[]
      LOOP
          FOR i IN 1..array_upper(relation_members, 1) BY 2 LOOP
              IF relation_members[i+1] in ('', 'main_stream', 'side_stream') AND substring(relation_members[i],1,1) = 'w' THEN
                --DEBUG: RAISE WARNING 'waterway parent %, child %/%', NEW.osm_id, i, relation_members[i];
                FOR linked_node_id IN SELECT place_id FROM placex
                  WHERE osm_type = 'W' and osm_id = substring(relation_members[i],2,200)::bigint
                  and class = NEW.class and type in ('river', 'stream', 'canal', 'drain', 'ditch')
                  and ( relation_members[i+1] != 'side_stream' or NEW.name->'name' = name->'name')
                LOOP
                  UPDATE placex SET linked_place_id = NEW.place_id WHERE place_id = linked_node_id;
                END LOOP;
              END IF;
          END LOOP;
      END LOOP;
      --DEBUG: RAISE WARNING 'Waterway processed';
  END IF;

  -- Adding ourselves to the list simplifies address calculations later
  INSERT INTO place_addressline (place_id, address_place_id, fromarea, isaddress, distance, cached_rank_address)
    VALUES (NEW.place_id, NEW.place_id, true, true, 0, NEW.rank_address); 

  -- What level are we searching from
  search_maxrank := NEW.rank_search;

  -- Thought this wasn't needed but when we add new languages to the country_name table
  -- we need to update the existing names
  IF NEW.name is not null AND array_upper(akeys(NEW.name),1) > 1 THEN
    default_language := get_country_language_code(NEW.country_code);
    IF default_language IS NOT NULL THEN
      IF NEW.name ? 'name' AND NOT NEW.name ? ('name:'||default_language) THEN
        NEW.name := NEW.name || hstore(('name:'||default_language), (NEW.name -> 'name'));
      ELSEIF NEW.name ? ('name:'||default_language) AND NOT NEW.name ? 'name' THEN
        NEW.name := NEW.name || hstore('name', (NEW.name -> ('name:'||default_language)));
      END IF;
    END IF;
  END IF;
  --DEBUG: RAISE WARNING 'Local names updated';

  -- Initialise the name vector using our name
  name_vector := make_keywords(NEW.name);
  nameaddress_vector := '{}'::int[];

  FOR i IN 1..28 LOOP
    address_havelevel[i] := false;
  END LOOP;

  NEW.importance := null;
  select language||':'||title,importance from get_wikipedia_match(NEW.extratags, NEW.country_code) INTO NEW.wikipedia,NEW.importance;
  IF NEW.importance IS NULL THEN
    select language||':'||title,importance from wikipedia_article where osm_type = NEW.osm_type and osm_id = NEW.osm_id order by importance desc limit 1 INTO NEW.wikipedia,NEW.importance;
  END IF;

--DEBUG: RAISE WARNING 'Importance computed from wikipedia: %', NEW.importance;

  -- ---------------------------------------------------------------------------
  -- For low level elements we inherit from our parent road
  IF (NEW.rank_search > 27 OR (NEW.type = 'postcode' AND NEW.rank_search = 25)) THEN

    --DEBUG: RAISE WARNING 'finding street for % %', NEW.osm_type, NEW.osm_id;

    -- We won't get a better centroid, besides these places are too small to care
    NEW.centroid := place_centroid;

    NEW.parent_place_id := null;

    -- if we have a POI and there is no address information,
    -- see if we can get it from a surrounding building
    IF NEW.osm_type = 'N' AND addr_street IS NULL AND addr_place IS NULL
       AND NEW.housenumber IS NULL THEN
      FOR location IN select address from placex where ST_Covers(geometry, place_centroid)
            and address is not null
            and (address ? 'housenumber' or address ? 'street' or address ? 'place')
            and rank_search > 28 AND ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon')
            limit 1
      LOOP
        NEW.housenumber := location.address->'housenumber';
        addr_street := location.address->'street';
        addr_place := location.address->'place';
        --DEBUG: RAISE WARNING 'Found surrounding building % %', location.osm_type, location.osm_id;
      END LOOP;
    END IF;

    -- We have to find our parent road.
    -- Copy data from linked items (points on ways, addr:street links, relations)

    -- Is this object part of a relation?
    FOR relation IN select * from planet_osm_rels where parts @> ARRAY[NEW.osm_id] and members @> ARRAY[lower(NEW.osm_type)||NEW.osm_id]
    LOOP
      -- At the moment we only process one type of relation - associatedStreet
      IF relation.tags @> ARRAY['associatedStreet'] THEN
        FOR i IN 1..array_upper(relation.members, 1) BY 2 LOOP
          IF NEW.parent_place_id IS NULL AND relation.members[i+1] = 'street' THEN
--RAISE WARNING 'node in relation %',relation;
            SELECT place_id from placex where osm_type = 'W'
              and osm_id = substring(relation.members[i],2,200)::bigint
              and rank_search = 26 and name is not null INTO NEW.parent_place_id;
          END IF;
        END LOOP;
      END IF;
    END LOOP;
    --DEBUG: RAISE WARNING 'Checked for street relation (%)', NEW.parent_place_id;

    -- Note that addr:street links can only be indexed once the street itself is indexed
    IF NEW.parent_place_id IS NULL AND addr_street IS NOT NULL THEN
      address_street_word_ids := get_name_ids(make_standard_name(addr_street));
      IF address_street_word_ids IS NOT NULL THEN
        SELECT place_id from getNearestNamedRoadFeature(NEW.partition, place_centroid, address_street_word_ids) INTO NEW.parent_place_id;
      END IF;
    END IF;
    --DEBUG: RAISE WARNING 'Checked for addr:street (%)', NEW.parent_place_id;

    IF NEW.parent_place_id IS NULL AND addr_place IS NOT NULL THEN
      address_street_word_ids := get_name_ids(make_standard_name(addr_place));
      IF address_street_word_ids IS NOT NULL THEN
        SELECT place_id from getNearestNamedPlaceFeature(NEW.partition, place_centroid, address_street_word_ids) INTO NEW.parent_place_id;
      END IF;
    END IF;
    --DEBUG: RAISE WARNING 'Checked for addr:place (%)', NEW.parent_place_id;

    -- Is this node part of an interpolation?
    IF NEW.parent_place_id IS NULL AND NEW.osm_type = 'N' THEN
      SELECT q.parent_place_id FROM location_property_osmline q, planet_osm_ways x
        WHERE q.linegeo && NEW.geometry and x.id = q.osm_id and NEW.osm_id = any(x.nodes)
        LIMIT 1 INTO NEW.parent_place_id;
    END IF;
    --DEBUG: RAISE WARNING 'Checked for interpolation (%)', NEW.parent_place_id;

    -- Is this node part of a way?
    IF NEW.parent_place_id IS NULL AND NEW.osm_type = 'N' THEN

      FOR location IN
        SELECT p.place_id, p.osm_id, p.rank_search, p.address from placex p, planet_osm_ways w
         WHERE p.osm_type = 'W' and p.rank_search >= 26 and p.geometry && NEW.geometry and w.id = p.osm_id and NEW.osm_id = any(w.nodes)
      LOOP
        --DEBUG: RAISE WARNING 'Node is part of way % ', location.osm_id;

        -- Way IS a road then we are on it - that must be our road
        IF location.rank_search < 28 THEN
--RAISE WARNING 'node in way that is a street %',location;
          NEW.parent_place_id := location.place_id;
          EXIT;
        END IF;
        --DEBUG: RAISE WARNING 'Checked if way is street (%)', NEW.parent_place_id;

        -- If the way mentions a street or place address, try that for parenting.
        IF location.address is not null THEN
          IF location.address ? 'street' THEN
            address_street_word_ids := get_name_ids(make_standard_name(location.address->'street'));
            IF address_street_word_ids IS NOT NULL THEN
              SELECT place_id from getNearestNamedRoadFeature(NEW.partition, place_centroid, address_street_word_ids) INTO NEW.parent_place_id;
              EXIT WHEN NEW.parent_place_id is not NULL;
            END IF;
          END IF;
          --DEBUG: RAISE WARNING 'Checked for addr:street in way (%)', NEW.parent_place_id;

          IF location.address ? 'place' THEN
            address_street_word_ids := get_name_ids(make_standard_name(location.address->'place'));
            IF address_street_word_ids IS NOT NULL THEN
              SELECT place_id from getNearestNamedPlaceFeature(NEW.partition, place_centroid, address_street_word_ids) INTO NEW.parent_place_id;
              EXIT WHEN NEW.parent_place_id is not NULL;
            END IF;
          END IF;
        --DEBUG: RAISE WARNING 'Checked for addr:place in way (%)', NEW.parent_place_id;
        END IF;

        -- Is the WAY part of a relation
        FOR relation IN select * from planet_osm_rels where parts @> ARRAY[location.osm_id] and members @> ARRAY['w'||location.osm_id]
        LOOP
          -- At the moment we only process one type of relation - associatedStreet
          IF relation.tags @> ARRAY['associatedStreet'] AND array_upper(relation.members, 1) IS NOT NULL THEN
            FOR i IN 1..array_upper(relation.members, 1) BY 2 LOOP
              IF NEW.parent_place_id IS NULL AND relation.members[i+1] = 'street' THEN
--RAISE WARNING 'node in way that is in a relation %',relation;
                SELECT place_id from placex where osm_type='W' and osm_id = substring(relation.members[i],2,200)::bigint 
                  and rank_search = 26 and name is not null INTO NEW.parent_place_id;
              END IF;
            END LOOP;
          END IF;
        END LOOP;
        EXIT WHEN NEW.parent_place_id is not null;
        --DEBUG: RAISE WARNING 'Checked for street relation in way (%)', NEW.parent_place_id;

      END LOOP;
    END IF;

    -- Still nothing, just use the nearest road
    IF NEW.parent_place_id IS NULL THEN
      SELECT place_id FROM getNearestRoadFeature(NEW.partition, place_centroid) INTO NEW.parent_place_id;
    END IF;
    --DEBUG: RAISE WARNING 'Checked for nearest way (%)', NEW.parent_place_id;


    -- If we didn't find any road fallback to standard method
    IF NEW.parent_place_id IS NOT NULL THEN

      -- Get the details of the parent road
      SELECT p.country_code, p.postcode FROM placex p
       WHERE p.place_id = NEW.parent_place_id INTO location;

      NEW.country_code := location.country_code;
      --DEBUG: RAISE WARNING 'Got parent details from search name';

      -- determine postcode
      IF NEW.rank_search > 4 THEN
          IF NEW.address is not null AND NEW.address ? 'postcode' THEN
              NEW.postcode = upper(trim(NEW.address->'postcode'));
          ELSE
             NEW.postcode := location.postcode;
          END IF;
          IF NEW.postcode is null THEN
            NEW.postcode := get_nearest_postcode(NEW.country_code, place_centroid);
          END IF;
      END IF;

      -- If there is no name it isn't searchable, don't bother to create a search record
      IF NEW.name is NULL THEN
        --DEBUG: RAISE WARNING 'Not a searchable place % %', NEW.osm_type, NEW.osm_id;
        return NEW;
      END IF;

      -- Performance, it would be more acurate to do all the rest of the import
      -- process but it takes too long
      -- Just be happy with inheriting from parent road only
      IF NEW.rank_search <= 25 and NEW.rank_address > 0 THEN
        result := add_location(NEW.place_id, NEW.country_code, NEW.partition, name_vector, NEW.rank_search, NEW.rank_address, upper(trim(NEW.address->'postcode')), NEW.geometry);
        --DEBUG: RAISE WARNING 'Place added to location table';
      END IF;

      result := insertSearchName(NEW.partition, NEW.place_id, name_vector,
                                 NEW.rank_search, NEW.rank_address, NEW.geometry);

      IF NOT %REVERSE-ONLY% THEN
          -- Merge address from parent
          SELECT s.name_vector, s.nameaddress_vector FROM search_name s
           WHERE s.place_id = NEW.parent_place_id INTO location;

          nameaddress_vector := array_merge(nameaddress_vector,
                                            location.nameaddress_vector);
          nameaddress_vector := array_merge(nameaddress_vector, location.name_vector);

          INSERT INTO search_name (place_id, search_rank, address_rank,
                                   importance, country_code, name_vector,
                                   nameaddress_vector, centroid)
                 VALUES (NEW.place_id, NEW.rank_search, NEW.rank_address,
                         NEW.importance, NEW.country_code, name_vector,
                         nameaddress_vector, place_centroid);
          --DEBUG: RAISE WARNING 'Place added to search table';
        END IF;

      return NEW;
    END IF;

  END IF;

  -- ---------------------------------------------------------------------------
  -- Full indexing
  --DEBUG: RAISE WARNING 'Using full index mode for % %', NEW.osm_type, NEW.osm_id;

  IF NEW.osm_type = 'R' AND NEW.rank_search < 26 THEN

    -- see if we have any special relation members
    select members from planet_osm_rels where id = NEW.osm_id INTO relation_members;
    --DEBUG: RAISE WARNING 'Got relation members';

    IF relation_members IS NOT NULL THEN
      FOR relMember IN select get_osm_rel_members(relation_members,ARRAY['label']) as member LOOP
        --DEBUG: RAISE WARNING 'Found label member %', relMember.member;

        FOR linkedPlacex IN select * from placex where osm_type = upper(substring(relMember.member,1,1))::char(1) 
          and osm_id = substring(relMember.member,2,10000)::bigint
          and class = 'place' order by rank_search desc limit 1 LOOP

          -- If we don't already have one use this as the centre point of the geometry
          IF NEW.centroid IS NULL THEN
            NEW.centroid := coalesce(linkedPlacex.centroid,st_centroid(linkedPlacex.geometry));
          END IF;

          -- merge in the label name, re-init word vector
          IF NOT linkedPlacex.name IS NULL THEN
            NEW.name := linkedPlacex.name || NEW.name;
            name_vector := array_merge(name_vector, make_keywords(linkedPlacex.name));
          END IF;

          -- merge in extra tags
          NEW.extratags := hstore(linkedPlacex.class, linkedPlacex.type) || coalesce(linkedPlacex.extratags, ''::hstore) || coalesce(NEW.extratags, ''::hstore);

          -- mark the linked place (excludes from search results)
          UPDATE placex set linked_place_id = NEW.place_id where place_id = linkedPlacex.place_id;

          -- keep a note of the node id in case we need it for wikipedia in a bit
          linked_node_id := linkedPlacex.osm_id;
          select language||':'||title,importance from get_wikipedia_match(linkedPlacex.extratags, NEW.country_code) INTO linked_wikipedia,linked_importance;
          --DEBUG: RAISE WARNING 'Linked label member';
        END LOOP;

      END LOOP;

      IF NEW.centroid IS NULL THEN

        FOR relMember IN select get_osm_rel_members(relation_members,ARRAY['admin_center','admin_centre']) as member LOOP
          --DEBUG: RAISE WARNING 'Found admin_center member %', relMember.member;

          FOR linkedPlacex IN select * from placex where osm_type = upper(substring(relMember.member,1,1))::char(1) 
            and osm_id = substring(relMember.member,2,10000)::bigint
            and class = 'place' order by rank_search desc limit 1 LOOP

            -- For an admin centre we also want a name match - still not perfect, for example 'new york, new york'
            -- But that can be fixed by explicitly setting the label in the data
            IF make_standard_name(NEW.name->'name') = make_standard_name(linkedPlacex.name->'name') 
              AND NEW.rank_address = linkedPlacex.rank_address THEN

              -- If we don't already have one use this as the centre point of the geometry
              IF NEW.centroid IS NULL THEN
                NEW.centroid := coalesce(linkedPlacex.centroid,st_centroid(linkedPlacex.geometry));
              END IF;

              -- merge in the name, re-init word vector
              IF NOT linkedPlacex.name IS NULL THEN
                NEW.name := linkedPlacex.name || NEW.name;
                name_vector := make_keywords(NEW.name);
              END IF;

              -- merge in extra tags
              NEW.extratags := hstore(linkedPlacex.class, linkedPlacex.type) || coalesce(linkedPlacex.extratags, ''::hstore) || coalesce(NEW.extratags, ''::hstore);

              -- mark the linked place (excludes from search results)
              UPDATE placex set linked_place_id = NEW.place_id where place_id = linkedPlacex.place_id;

              -- keep a note of the node id in case we need it for wikipedia in a bit
              linked_node_id := linkedPlacex.osm_id;
              select language||':'||title,importance from get_wikipedia_match(linkedPlacex.extratags, NEW.country_code) INTO linked_wikipedia,linked_importance;
              --DEBUG: RAISE WARNING 'Linked admin_center';
            END IF;

          END LOOP;

        END LOOP;

      END IF;
    END IF;

  END IF;

  -- Name searches can be done for ways as well as relations
  IF NEW.osm_type in ('W','R') AND NEW.rank_search < 26 AND NEW.rank_address > 0 THEN

    -- not found one yet? how about doing a name search
    IF NEW.centroid IS NULL AND (NEW.name->'name') is not null and make_standard_name(NEW.name->'name') != '' THEN

      --DEBUG: RAISE WARNING 'Looking for nodes with matching names';
      FOR linkedPlacex IN select placex.* from placex WHERE
        make_standard_name(name->'name') = make_standard_name(NEW.name->'name')
        AND placex.rank_address = NEW.rank_address
        AND placex.place_id != NEW.place_id
        AND placex.osm_type = 'N'::char(1) AND placex.rank_search < 26
        AND st_covers(NEW.geometry, placex.geometry)
      LOOP
        --DEBUG: RAISE WARNING 'Found matching place node %', linkedPlacex.osm_id;
        -- If we don't already have one use this as the centre point of the geometry
        IF NEW.centroid IS NULL THEN
          NEW.centroid := coalesce(linkedPlacex.centroid,st_centroid(linkedPlacex.geometry));
        END IF;

        -- merge in the name, re-init word vector
        NEW.name := linkedPlacex.name || NEW.name;
        name_vector := make_keywords(NEW.name);

        -- merge in extra tags
        NEW.extratags := hstore(linkedPlacex.class, linkedPlacex.type) || coalesce(linkedPlacex.extratags, ''::hstore) || coalesce(NEW.extratags, ''::hstore);

        -- mark the linked place (excludes from search results)
        UPDATE placex set linked_place_id = NEW.place_id where place_id = linkedPlacex.place_id;

        -- keep a note of the node id in case we need it for wikipedia in a bit
        linked_node_id := linkedPlacex.osm_id;
        select language||':'||title,importance from get_wikipedia_match(linkedPlacex.extratags, NEW.country_code) INTO linked_wikipedia,linked_importance;
        --DEBUG: RAISE WARNING 'Linked named place';
      END LOOP;
    END IF;

    IF NEW.centroid IS NOT NULL THEN
      place_centroid := NEW.centroid;
      -- Place might have had only a name tag before but has now received translations
      -- from the linked place. Make sure a name tag for the default language exists in
      -- this case. 
      IF NEW.name is not null AND array_upper(akeys(NEW.name),1) > 1 THEN
        default_language := get_country_language_code(NEW.country_code);
        IF default_language IS NOT NULL THEN
          IF NEW.name ? 'name' AND NOT NEW.name ? ('name:'||default_language) THEN
            NEW.name := NEW.name || hstore(('name:'||default_language), (NEW.name -> 'name'));
          ELSEIF NEW.name ? ('name:'||default_language) AND NOT NEW.name ? 'name' THEN
            NEW.name := NEW.name || hstore('name', (NEW.name -> ('name:'||default_language)));
          END IF;
        END IF;
      END IF;
      --DEBUG: RAISE WARNING 'Names updated from linked places';
    END IF;

    -- Use the maximum importance if a one could be computed from the linked object.
    IF linked_importance is not null AND
        (NEW.importance is null or NEW.importance < linked_importance) THEN
        NEW.importance = linked_importance;
    END IF;

    -- Still null? how about looking it up by the node id
    IF NEW.importance IS NULL THEN
      --DEBUG: RAISE WARNING 'Looking up importance by linked node id';
      select language||':'||title,importance from wikipedia_article where osm_type = 'N'::char(1) and osm_id = linked_node_id order by importance desc limit 1 INTO NEW.wikipedia,NEW.importance;
    END IF;

  END IF;

  -- make sure all names are in the word table
  IF NEW.admin_level = 2 AND NEW.class = 'boundary' AND NEW.type = 'administrative' AND NEW.country_code IS NOT NULL AND NEW.osm_type = 'R' THEN
    perform create_country(NEW.name, lower(NEW.country_code));
    --DEBUG: RAISE WARNING 'Country names updated';
  END IF;

  NEW.parent_place_id = 0;
  parent_place_id_rank = 0;


  -- convert address store to array of tokenids
  --DEBUG: RAISE WARNING 'Starting address search';
  isin_tokens := '{}'::int[];
  IF NEW.address IS NOT NULL THEN
    FOR addr_item IN SELECT * FROM each(NEW.address)
    LOOP
      IF addr_item.key IN ('city', 'tiger:county', 'state', 'suburb', 'province', 'district', 'region', 'county', 'municipality', 'hamlet', 'village', 'subdistrict', 'town', 'neighbourhood', 'quarter', 'parish') THEN
        address_street_word_id := get_name_id(make_standard_name(addr_item.value));
        IF address_street_word_id IS NOT NULL AND NOT(ARRAY[address_street_word_id] <@ isin_tokens) THEN
          isin_tokens := isin_tokens || address_street_word_id;
        END IF;
        IF NOT %REVERSE-ONLY% THEN
          address_street_word_id := get_word_id(make_standard_name(addr_item.value));
          IF address_street_word_id IS NOT NULL THEN
            nameaddress_vector := array_merge(nameaddress_vector, ARRAY[address_street_word_id]);
          END IF;
        END IF;
      END IF;
      IF addr_item.key = 'is_in' THEN
        -- is_in items need splitting
        isin := regexp_split_to_array(addr_item.value, E'[;,]');
        IF array_upper(isin, 1) IS NOT NULL THEN
          FOR i IN 1..array_upper(isin, 1) LOOP
            address_street_word_id := get_name_id(make_standard_name(isin[i]));
            IF address_street_word_id IS NOT NULL AND NOT(ARRAY[address_street_word_id] <@ isin_tokens) THEN
              isin_tokens := isin_tokens || address_street_word_id;
            END IF;

            -- merge word into address vector
            IF NOT %REVERSE-ONLY% THEN
              address_street_word_id := get_word_id(make_standard_name(isin[i]));
              IF address_street_word_id IS NOT NULL THEN
                nameaddress_vector := array_merge(nameaddress_vector, ARRAY[address_street_word_id]);
              END IF;
            END IF;
          END LOOP;
        END IF;
      END IF;
    END LOOP;
  END IF;
  IF NOT %REVERSE-ONLY% THEN
    nameaddress_vector := array_merge(nameaddress_vector, isin_tokens);
  END IF;

-- RAISE WARNING 'ISIN: %', isin_tokens;

  -- Process area matches
  location_rank_search := 0;
  location_distance := 0;
  location_parent := NULL;
  -- added ourself as address already
  address_havelevel[NEW.rank_address] := true;
  --DEBUG: RAISE WARNING '  getNearFeatures(%,''%'',%,''%'')',NEW.partition, place_centroid, search_maxrank, isin_tokens;
  FOR location IN
    SELECT * from getNearFeatures(NEW.partition,
                                  CASE WHEN NEW.rank_search >= 26
                                             AND NEW.rank_search < 30
                                       THEN NEW.geometry
                                       ELSE place_centroid END,
                                  search_maxrank, isin_tokens)
  LOOP
    IF location.rank_address != location_rank_search THEN
      location_rank_search := location.rank_address;
      IF location.isguess THEN
        location_distance := location.distance * 1.5;
      ELSE
        IF location.rank_address <= 12 THEN
          -- for county and above, if we have an area consider that exact
          -- (It would be nice to relax the constraint for places close to
          --  the boundary but we'd need the exact geometry for that. Too
          --  expensive.)
          location_distance = 0;
        ELSE
          -- Below county level remain slightly fuzzy.
          location_distance := location.distance * 0.5;
        END IF;
      END IF;
    ELSE
      CONTINUE WHEN location.keywords <@ location_keywords;
    END IF;

    IF location.distance < location_distance OR NOT location.isguess THEN
      location_keywords := location.keywords;

      location_isaddress := NOT address_havelevel[location.rank_address];
      IF location_isaddress AND location.isguess AND location_parent IS NOT NULL THEN
          location_isaddress := ST_Contains(location_parent,location.centroid);
      END IF;

      -- RAISE WARNING '% isaddress: %', location.place_id, location_isaddress;
      -- Add it to the list of search terms
      IF NOT %REVERSE-ONLY% AND location.rank_search > 4 THEN
          nameaddress_vector := array_merge(nameaddress_vector, location.keywords::integer[]);
      END IF;
      INSERT INTO place_addressline (place_id, address_place_id, fromarea, isaddress, distance, cached_rank_address)
        VALUES (NEW.place_id, location.place_id, true, location_isaddress, location.distance, location.rank_address);

      IF location_isaddress THEN
        -- add postcode if we have one
        -- (If multiple postcodes are available, we end up with the highest ranking one.)
        IF location.postcode is not null THEN
            NEW.postcode = location.postcode;
        END IF;

        address_havelevel[location.rank_address] := true;
        IF NOT location.isguess THEN
          SELECT geometry FROM placex WHERE place_id = location.place_id INTO location_parent;
        END IF;

        IF location.rank_address > parent_place_id_rank THEN
          NEW.parent_place_id = location.place_id;
          parent_place_id_rank = location.rank_address;
        END IF;

      END IF;

    --DEBUG: RAISE WARNING '  Terms: (%) %',location, nameaddress_vector;

    END IF;

  END LOOP;
  --DEBUG: RAISE WARNING 'address computed';

  IF NEW.address is not null AND NEW.address ? 'postcode' 
     AND NEW.address->'postcode' not similar to '%(,|;)%' THEN
    NEW.postcode := upper(trim(NEW.address->'postcode'));
  END IF;

  IF NEW.postcode is null AND NEW.rank_search > 8 THEN
    NEW.postcode := get_nearest_postcode(NEW.country_code, NEW.geometry);
  END IF;

  -- if we have a name add this to the name search table
  IF NEW.name IS NOT NULL THEN

    IF NEW.rank_search <= 25 and NEW.rank_address > 0 THEN
      result := add_location(NEW.place_id, NEW.country_code, NEW.partition, name_vector, NEW.rank_search, NEW.rank_address, upper(trim(NEW.address->'postcode')), NEW.geometry);
      --DEBUG: RAISE WARNING 'added to location (full)';
    END IF;

    IF NEW.rank_search between 26 and 27 and NEW.class = 'highway' THEN
      result := insertLocationRoad(NEW.partition, NEW.place_id, NEW.country_code, NEW.geometry);
      --DEBUG: RAISE WARNING 'insert into road location table (full)';
    END IF;

    result := insertSearchName(NEW.partition, NEW.place_id, name_vector,
                               NEW.rank_search, NEW.rank_address, NEW.geometry);
    --DEBUG: RAISE WARNING 'added to search name (full)';

    IF NOT %REVERSE-ONLY% THEN
        INSERT INTO search_name (place_id, search_rank, address_rank,
                                 importance, country_code, name_vector,
                                 nameaddress_vector, centroid)
               VALUES (NEW.place_id, NEW.rank_search, NEW.rank_address,
                       NEW.importance, NEW.country_code, name_vector,
                       nameaddress_vector, place_centroid);
    END IF;

  END IF;

  -- If we've not managed to pick up a better one - default centroid
  IF NEW.centroid IS NULL THEN
    NEW.centroid := place_centroid;
  END IF;

  --DEBUG: RAISE WARNING 'place update % % finsihed.', NEW.osm_type, NEW.osm_id;

  RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION placex_delete() RETURNS TRIGGER
  AS $$
DECLARE
  b BOOLEAN;
  classtable TEXT;
BEGIN
  -- RAISE WARNING 'placex_delete % %',OLD.osm_type,OLD.osm_id;

  update placex set linked_place_id = null, indexed_status = 2 where linked_place_id = OLD.place_id and indexed_status = 0;
  --DEBUG: RAISE WARNING 'placex_delete:01 % %',OLD.osm_type,OLD.osm_id;
  update placex set linked_place_id = null where linked_place_id = OLD.place_id;
  --DEBUG: RAISE WARNING 'placex_delete:02 % %',OLD.osm_type,OLD.osm_id;

  IF OLD.rank_address < 30 THEN

    -- mark everything linked to this place for re-indexing
    --DEBUG: RAISE WARNING 'placex_delete:03 % %',OLD.osm_type,OLD.osm_id;
    UPDATE placex set indexed_status = 2 from place_addressline where address_place_id = OLD.place_id 
      and placex.place_id = place_addressline.place_id and indexed_status = 0 and place_addressline.isaddress;

    --DEBUG: RAISE WARNING 'placex_delete:04 % %',OLD.osm_type,OLD.osm_id;
    DELETE FROM place_addressline where address_place_id = OLD.place_id;

    --DEBUG: RAISE WARNING 'placex_delete:05 % %',OLD.osm_type,OLD.osm_id;
    b := deleteRoad(OLD.partition, OLD.place_id);

    --DEBUG: RAISE WARNING 'placex_delete:06 % %',OLD.osm_type,OLD.osm_id;
    update placex set indexed_status = 2 where parent_place_id = OLD.place_id and indexed_status = 0;
    --DEBUG: RAISE WARNING 'placex_delete:07 % %',OLD.osm_type,OLD.osm_id;
    -- reparenting also for OSM Interpolation Lines (and for Tiger?)
    update location_property_osmline set indexed_status = 2 where indexed_status = 0 and parent_place_id = OLD.place_id;

  END IF;

  --DEBUG: RAISE WARNING 'placex_delete:08 % %',OLD.osm_type,OLD.osm_id;

  IF OLD.rank_address < 26 THEN
    b := deleteLocationArea(OLD.partition, OLD.place_id, OLD.rank_search);
  END IF;

  --DEBUG: RAISE WARNING 'placex_delete:09 % %',OLD.osm_type,OLD.osm_id;

  IF OLD.name is not null THEN
    IF NOT %REVERSE-ONLY% THEN
      DELETE from search_name WHERE place_id = OLD.place_id;
    END IF;
    b := deleteSearchName(OLD.partition, OLD.place_id);
  END IF;

  --DEBUG: RAISE WARNING 'placex_delete:10 % %',OLD.osm_type,OLD.osm_id;

  DELETE FROM place_addressline where place_id = OLD.place_id;

  --DEBUG: RAISE WARNING 'placex_delete:11 % %',OLD.osm_type,OLD.osm_id;

  -- remove from tables for special search
  classtable := 'place_classtype_' || OLD.class || '_' || OLD.type;
  SELECT count(*)>0 FROM pg_tables WHERE tablename = classtable and schemaname = current_schema() INTO b;
  IF b THEN
    EXECUTE 'DELETE FROM ' || classtable::regclass || ' WHERE place_id = $1' USING OLD.place_id;
  END IF;

  --DEBUG: RAISE WARNING 'placex_delete:12 % %',OLD.osm_type,OLD.osm_id;

  RETURN OLD;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION place_delete() RETURNS TRIGGER
  AS $$
DECLARE
  has_rank BOOLEAN;
BEGIN

  --DEBUG: RAISE WARNING 'delete: % % % %',OLD.osm_type,OLD.osm_id,OLD.class,OLD.type;

  -- deleting large polygons can have a massive effect on the system - require manual intervention to let them through
  IF st_area(OLD.geometry) > 2 and st_isvalid(OLD.geometry) THEN
    SELECT bool_or(not (rank_address = 0 or rank_address > 26)) as ranked FROM placex WHERE osm_type = OLD.osm_type and osm_id = OLD.osm_id and class = OLD.class and type = OLD.type INTO has_rank;
    IF has_rank THEN
      insert into import_polygon_delete (osm_type, osm_id, class, type) values (OLD.osm_type,OLD.osm_id,OLD.class,OLD.type);
      RETURN NULL;
    END IF;
  END IF;

  -- mark for delete
  UPDATE placex set indexed_status = 100 where osm_type = OLD.osm_type and osm_id = OLD.osm_id and class = OLD.class and type = OLD.type;

  -- interpolations are special
  IF OLD.osm_type='W' and OLD.class = 'place' and OLD.type = 'houses' THEN
    UPDATE location_property_osmline set indexed_status = 100 where osm_id = OLD.osm_id; -- osm_id = wayid (=old.osm_id)
  END IF;

  RETURN OLD;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION place_insert() RETURNS TRIGGER
  AS $$
DECLARE
  i INTEGER;
  existing RECORD;
  existingplacex RECORD;
  existingline RECORD;
  existinggeometry GEOMETRY;
  existingplace_id BIGINT;
  result BOOLEAN;
  partition INTEGER;
BEGIN

  --DEBUG: RAISE WARNING '-----------------------------------------------------------------------------------';
  --DEBUG: RAISE WARNING 'place_insert: % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,st_area(NEW.geometry);
  -- filter wrong tupels
  IF ST_IsEmpty(NEW.geometry) OR NOT ST_IsValid(NEW.geometry) OR ST_X(ST_Centroid(NEW.geometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEW.geometry))::text in ('NaN','Infinity','-Infinity') THEN  
    INSERT INTO import_polygon_error (osm_type, osm_id, class, type, name, country_code, updated, errormessage, prevgeometry, newgeometry)
      VALUES (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name, NEW.address->'country', now(), ST_IsValidReason(NEW.geometry), null, NEW.geometry);
--    RAISE WARNING 'Invalid Geometry: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;
    RETURN null;
  END IF;

  -- decide, whether it is an osm interpolation line => insert intoosmline, or else just placex
  IF NEW.class='place' and NEW.type='houses' and NEW.osm_type='W' and ST_GeometryType(NEW.geometry) = 'ST_LineString' THEN
    -- Have we already done this place?
    select * from place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type INTO existing;

    -- Get the existing place_id
    select * from location_property_osmline where osm_id = NEW.osm_id INTO existingline;

    -- Handle a place changing type by removing the old data (this trigger is executed BEFORE INSERT of the NEW tupel)
    IF existing.osm_type IS NULL THEN
      DELETE FROM place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class;
    END IF;

    DELETE from import_polygon_error where osm_type = NEW.osm_type and osm_id = NEW.osm_id;
    DELETE from import_polygon_delete where osm_type = NEW.osm_type and osm_id = NEW.osm_id;

    -- update method for interpolation lines: delete all old interpolation lines with same osm_id (update on place) and insert the new one(s) (they can be split up, if they have > 2 nodes)
    IF existingline.osm_id IS NOT NULL THEN
      delete from location_property_osmline where osm_id = NEW.osm_id;
    END IF;

    -- for interpolations invalidate all nodes on the line
    update placex p set indexed_status = 2
      from planet_osm_ways w
      where w.id = NEW.osm_id and p.osm_type = 'N' and p.osm_id = any(w.nodes);


    INSERT INTO location_property_osmline (osm_id, address, linegeo)
      VALUES (NEW.osm_id, NEW.address, NEW.geometry);


    IF existing.osm_type IS NULL THEN
      return NEW;
    END IF;

    IF coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
       OR (coalesce(existing.extratags, ''::hstore) != coalesce(NEW.extratags, ''::hstore))
       OR existing.geometry::text != NEW.geometry::text
       THEN

      update place set 
        name = NEW.name,
        address = NEW.address,
        extratags = NEW.extratags,
        admin_level = NEW.admin_level,
        geometry = NEW.geometry
        where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type;
    END IF;

    RETURN NULL;

  ELSE -- insert to placex

    -- Patch in additional country names
    IF NEW.admin_level = 2 AND NEW.type = 'administrative'
          AND NEW.address is not NULL AND NEW.address ? 'country' THEN
        SELECT name FROM country_name WHERE country_code = lower(NEW.address->'country') INTO existing;
        IF existing.name IS NOT NULL THEN
            NEW.name = existing.name || NEW.name;
        END IF;
    END IF;
      
    -- Have we already done this place?
    select * from place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type INTO existing;

    -- Get the existing place_id
    select * from placex where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type INTO existingplacex;

    -- Handle a place changing type by removing the old data
    -- My generated 'place' types are causing havok because they overlap with real keys
    -- TODO: move them to their own special purpose key/class to avoid collisions
    IF existing.osm_type IS NULL THEN
      DELETE FROM place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class;
    END IF;

    --DEBUG: RAISE WARNING 'Existing: %',existing.osm_id;
    --DEBUG: RAISE WARNING 'Existing PlaceX: %',existingplacex.place_id;

    -- Log and discard 
    IF existing.geometry is not null AND st_isvalid(existing.geometry) 
      AND st_area(existing.geometry) > 0.02
      AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon')
      AND st_area(NEW.geometry) < st_area(existing.geometry)*0.5
      THEN
      INSERT INTO import_polygon_error (osm_type, osm_id, class, type, name, country_code, updated, errormessage, prevgeometry, newgeometry)
        VALUES (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name, NEW.address->'country', now(), 
        'Area reduced from '||st_area(existing.geometry)||' to '||st_area(NEW.geometry), existing.geometry, NEW.geometry);
      RETURN null;
    END IF;

    DELETE from import_polygon_error where osm_type = NEW.osm_type and osm_id = NEW.osm_id;
    DELETE from import_polygon_delete where osm_type = NEW.osm_type and osm_id = NEW.osm_id;

    -- To paraphrase, if there isn't an existing item, OR if the admin level has changed
    IF existingplacex.osm_type IS NULL OR
        (existingplacex.class = 'boundary' AND
          ((coalesce(existingplacex.admin_level, 15) != coalesce(NEW.admin_level, 15) AND existingplacex.type = 'administrative') OR
          (existingplacex.type != NEW.type)))
    THEN

      IF existingplacex.osm_type IS NOT NULL THEN
        -- sanity check: ignore admin_level changes on places with too many active children
        -- or we end up reindexing entire countries because somebody accidentally deleted admin_level
        --LIMIT INDEXING: SELECT count(*) FROM (SELECT 'a' FROM placex , place_addressline where address_place_id = existingplacex.place_id and placex.place_id = place_addressline.place_id and indexed_status = 0 and place_addressline.isaddress LIMIT 100001) sub INTO i;
        --LIMIT INDEXING: IF i > 100000 THEN
        --LIMIT INDEXING:  RETURN null;
        --LIMIT INDEXING: END IF;
      END IF;

      IF existing.osm_type IS NOT NULL THEN
        -- pathological case caused by the triggerless copy into place during initial import
        -- force delete even for large areas, it will be reinserted later
        UPDATE place set geometry = ST_SetSRID(ST_Point(0,0), 4326) where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type;
        DELETE from place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type;
      END IF;

      -- No - process it as a new insertion (hopefully of low rank or it will be slow)
      insert into placex (osm_type, osm_id, class, type, name,
                          admin_level, address, extratags, geometry)
        values (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name,
                NEW.admin_level, NEW.address, NEW.extratags, NEW.geometry);

      --DEBUG: RAISE WARNING 'insert done % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,NEW.name;

      RETURN NEW;
    END IF;

    -- Special case for polygon shape changes because they tend to be large and we can be a bit clever about how we handle them
    IF existing.geometry::text != NEW.geometry::text 
       AND ST_GeometryType(existing.geometry) in ('ST_Polygon','ST_MultiPolygon')
       AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon') 
       THEN 

      -- Get the version of the geometry actually used (in placex table)
      select geometry from placex where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type into existinggeometry;

      -- Performance limit
      IF st_area(NEW.geometry) < 0.000000001 AND st_area(existinggeometry) < 1 THEN

        -- re-index points that have moved in / out of the polygon, could be done as a single query but postgres gets the index usage wrong
        update placex set indexed_status = 2 where indexed_status = 0 and 
            (st_covers(NEW.geometry, placex.geometry) OR ST_Intersects(NEW.geometry, placex.geometry))
            AND NOT (st_covers(existinggeometry, placex.geometry) OR ST_Intersects(existinggeometry, placex.geometry))
            AND rank_search > existingplacex.rank_search AND (rank_search < 28 or name is not null);

        update placex set indexed_status = 2 where indexed_status = 0 and 
            (st_covers(existinggeometry, placex.geometry) OR ST_Intersects(existinggeometry, placex.geometry))
            AND NOT (st_covers(NEW.geometry, placex.geometry) OR ST_Intersects(NEW.geometry, placex.geometry))
            AND rank_search > existingplacex.rank_search AND (rank_search < 28 or name is not null);

      END IF;

    END IF;


    IF coalesce(existing.name::text, '') != coalesce(NEW.name::text, '')
       OR coalesce(existing.extratags::text, '') != coalesce(NEW.extratags::text, '')
       OR coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
       OR coalesce(existing.admin_level, 15) != coalesce(NEW.admin_level, 15)
       OR existing.geometry::text != NEW.geometry::text
       THEN

      update place set 
        name = NEW.name,
        address = NEW.address,
        extratags = NEW.extratags,
        admin_level = NEW.admin_level,
        geometry = NEW.geometry
        where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type;


      IF NEW.class in ('place','boundary') AND NEW.type in ('postcode','postal_code') THEN
          IF NEW.address is NULL OR NOT NEW.address ? 'postcode' THEN
              -- postcode was deleted, no longer retain in placex
              DELETE FROM placex where place_id = existingplacex.place_id;
              RETURN NULL;
          END IF;

          NEW.name := hstore('ref', NEW.address->'postcode');
      END IF;

      IF NEW.class in ('boundary')
         AND ST_GeometryType(NEW.geometry) not in ('ST_Polygon','ST_MultiPolygon') THEN
          DELETE FROM placex where place_id = existingplacex.place_id;
          RETURN NULL;
      END IF;

      update placex set 
        name = NEW.name,
        address = NEW.address,
        parent_place_id = null,
        extratags = NEW.extratags,
        admin_level = NEW.admin_level,
        indexed_status = 2,
        geometry = NEW.geometry
        where place_id = existingplacex.place_id;

      -- if a node(=>house), which is part of a interpolation line, changes (e.g. the street attribute) => mark this line for reparenting 
      -- (already here, because interpolation lines are reindexed before nodes, so in the second call it would be too late)
      IF NEW.osm_type='N' and NEW.class='place' and NEW.type='house' THEN
          -- Is this node part of an interpolation line? search for it in location_property_osmline and mark the interpolation line for reparenting
          update location_property_osmline p set indexed_status = 2 from planet_osm_ways w where p.linegeo && NEW.geometry and p.osm_id = w.id and NEW.osm_id = any(w.nodes);
      END IF;

      -- linked places should get potential new naming and addresses
      IF existingplacex.linked_place_id is not NULL THEN
        update placex x set
          name = p.name,
          extratags = p.extratags,
          indexed_status = 2
        from place p
        where x.place_id = existingplacex.linked_place_id
              and x.indexed_status = 0
              and x.osm_type = p.osm_type
              and x.osm_id = p.osm_id
              and x.class = p.class;
      END IF;

    END IF;

    -- Abort the add (we modified the existing place instead)
    RETURN NULL;
  END IF;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_name_by_language(name hstore, languagepref TEXT[]) RETURNS TEXT
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
CREATE OR REPLACE FUNCTION get_address_by_language(for_place_id BIGINT, housenumber INTEGER, languagepref TEXT[]) RETURNS TEXT
  AS $$
DECLARE
  result TEXT[];
  currresult TEXT;
  prevresult TEXT;
  location RECORD;
BEGIN

  result := '{}';
  prevresult := '';

  FOR location IN select * from get_addressdata(for_place_id, housenumber) where isaddress order by rank_address desc LOOP
    currresult := trim(get_name_by_language(location.name, languagepref));
    IF currresult != prevresult AND currresult IS NOT NULL AND result[(100 - location.rank_address)] IS NULL THEN
      result[(100 - location.rank_address)] := trim(get_name_by_language(location.name, languagepref));
      prevresult := currresult;
    END IF;
  END LOOP;

  RETURN array_to_string(result,', ');
END;
$$
LANGUAGE plpgsql;

DROP TYPE IF EXISTS addressline CASCADE;
create type addressline as (
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

CREATE OR REPLACE FUNCTION get_addressdata(in_place_id BIGINT, in_housenumber INTEGER) RETURNS setof addressline 
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
  searchclass TEXT;
  searchtype TEXT;
  countryname HSTORE;
  hadcountry BOOLEAN;
BEGIN
  -- first query osmline (interpolation lines)
  select parent_place_id, country_code, 30, postcode, null, 'place', 'house' from location_property_osmline 
    WHERE place_id = in_place_id AND in_housenumber>=startnumber AND in_housenumber <= endnumber
    INTO for_place_id,searchcountrycode, searchrankaddress, searchpostcode, searchhousename, searchclass, searchtype;
  IF for_place_id IS NOT NULL THEN
    searchhousenumber = in_housenumber::text;
  END IF;

  --then query tiger data
  -- %NOTIGERDATA% IF 0 THEN
  IF for_place_id IS NULL THEN
    select parent_place_id,'us', 30, postcode, null, 'place', 'house' from location_property_tiger 
      WHERE place_id = in_place_id AND in_housenumber>=startnumber AND in_housenumber <= endnumber
      INTO for_place_id,searchcountrycode, searchrankaddress, searchpostcode, searchhousename, searchclass, searchtype;
    IF for_place_id IS NOT NULL THEN
      searchhousenumber = in_housenumber::text;
    END IF;
  END IF;
  -- %NOTIGERDATA% END IF;

  -- %NOAUXDATA% IF 0 THEN
  IF for_place_id IS NULL THEN
    select parent_place_id,'us', housenumber, 30, postcode, null, 'place', 'house' from location_property_aux
      WHERE place_id = in_place_id
      INTO for_place_id,searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode, searchhousename, searchclass, searchtype;
  END IF;
  -- %NOAUXDATA% END IF;

  -- postcode table
  IF for_place_id IS NULL THEN
    select parent_place_id, country_code, rank_address, postcode, 'place', 'postcode'
      FROM location_postcode
      WHERE place_id = in_place_id
      INTO for_place_id, searchcountrycode, searchrankaddress, searchpostcode, searchclass, searchtype;
  END IF;

  IF for_place_id IS NULL THEN
    select parent_place_id, country_code, housenumber, rank_search, postcode, name, class, type from placex 
      WHERE place_id = in_place_id and  rank_search > 27
      INTO for_place_id, searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode, searchhousename, searchclass, searchtype;
  END IF;

  IF for_place_id IS NULL THEN
    select coalesce(linked_place_id, place_id),  country_code,
           housenumber, rank_search, postcode, null
      from placex where place_id = in_place_id
      INTO for_place_id, searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode, searchhousename;
  END IF;

--RAISE WARNING '% % % %',searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode;

  found := 1000;
  hadcountry := false;
  FOR location IN 
    select placex.place_id, osm_type, osm_id, name,
      class, type, admin_level, true as isaddress,
      CASE WHEN rank_address = 0 THEN 100 WHEN rank_address = 11 THEN 5 ELSE rank_address END as rank_address,
      0 as distance, country_code, postcode
      from placex
      where place_id = for_place_id 
  LOOP
--RAISE WARNING '%',location;
    IF searchcountrycode IS NULL AND location.country_code IS NOT NULL THEN
      searchcountrycode := location.country_code;
    END IF;
    IF location.type in ('postcode', 'postal_code') THEN
      location.isaddress := FALSE;
    ELSEIF location.rank_address = 4 THEN
      hadcountry := true;
    END IF;
    IF location.rank_address < 4 AND NOT hadcountry THEN
      select name from country_name where country_code = searchcountrycode limit 1 INTO countryname;
      IF countryname IS NOT NULL THEN
        countrylocation := ROW(null, null, null, countryname, 'place', 'country', null, true, true, 4, 0)::addressline;
        RETURN NEXT countrylocation;
      END IF;
    END IF;
    countrylocation := ROW(location.place_id, location.osm_type, location.osm_id, location.name, location.class, 
                           location.type, location.admin_level, true, location.isaddress, location.rank_address,
                           location.distance)::addressline;
    RETURN NEXT countrylocation;
    found := location.rank_address;
  END LOOP;

  FOR location IN 
    select placex.place_id, osm_type, osm_id, name,
      CASE WHEN extratags ? 'place' THEN 'place' ELSE class END as class,
      CASE WHEN extratags ? 'place' THEN extratags->'place' ELSE type END as type,
      admin_level, fromarea, isaddress,
      CASE WHEN address_place_id = for_place_id AND rank_address = 0 THEN 100 WHEN rank_address = 11 THEN 5 ELSE rank_address END as rank_address,
      distance,country_code,postcode
      from place_addressline join placex on (address_place_id = placex.place_id) 
      where place_addressline.place_id = for_place_id 
      and (cached_rank_address > 0 AND cached_rank_address < searchrankaddress)
      and address_place_id != for_place_id and linked_place_id is null
      and (placex.country_code IS NULL OR searchcountrycode IS NULL OR placex.country_code = searchcountrycode)
      order by rank_address desc,isaddress desc,fromarea desc,distance asc,rank_search desc
  LOOP
--RAISE WARNING '%',location;
    IF searchcountrycode IS NULL AND location.country_code IS NOT NULL THEN
      searchcountrycode := location.country_code;
    END IF;
    IF location.type in ('postcode', 'postal_code') THEN
      location.isaddress := FALSE;
    END IF;
    IF location.rank_address = 4 AND location.isaddress THEN
      hadcountry := true;
    END IF;
    IF location.rank_address < 4 AND NOT hadcountry THEN
      select name from country_name where country_code = searchcountrycode limit 1 INTO countryname;
      IF countryname IS NOT NULL THEN
        countrylocation := ROW(null, null, null, countryname, 'place', 'country', null, true, true, 4, 0)::addressline;
        RETURN NEXT countrylocation;
      END IF;
    END IF;
    countrylocation := ROW(location.place_id, location.osm_type, location.osm_id, location.name, location.class, 
                           location.type, location.admin_level, location.fromarea, location.isaddress, location.rank_address, 
                           location.distance)::addressline;
    RETURN NEXT countrylocation;
    found := location.rank_address;
  END LOOP;

  IF found > 4 THEN
    select name from country_name where country_code = searchcountrycode limit 1 INTO countryname;
--RAISE WARNING '% % %',found,searchcountrycode,countryname;
    IF countryname IS NOT NULL THEN
      location := ROW(null, null, null, countryname, 'place', 'country', null, true, true, 4, 0)::addressline;
      RETURN NEXT location;
    END IF;
  END IF;

  IF searchcountrycode IS NOT NULL THEN
    location := ROW(null, null, null, hstore('ref', searchcountrycode), 'place', 'country_code', null, true, false, 4, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchhousename IS NOT NULL THEN
    location := ROW(in_place_id, null, null, searchhousename, searchclass, searchtype, null, true, true, 29, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchhousenumber IS NOT NULL THEN
    location := ROW(in_place_id, null, null, hstore('ref', searchhousenumber), 'place', 'house_number', null, true, true, 28, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchpostcode IS NOT NULL THEN
    location := ROW(null, null, null, hstore('ref', searchpostcode), 'place', 'postcode', null, true, true, 5, 0)::addressline;
    RETURN NEXT location;
  END IF;

  RETURN;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_searchrank_label(rank INTEGER) RETURNS TEXT
  AS $$
DECLARE
BEGIN
  IF rank < 2 THEN
    RETURN 'Continent';
  ELSEIF rank < 4 THEN
    RETURN 'Sea';
  ELSEIF rank < 8 THEN
    RETURN 'Country';
  ELSEIF rank < 12 THEN
    RETURN 'State';
  ELSEIF rank < 16 THEN
    RETURN 'County';
  ELSEIF rank = 16 THEN
    RETURN 'City';
  ELSEIF rank = 17 THEN
    RETURN 'Town / Island';
  ELSEIF rank = 18 THEN
    RETURN 'Village / Hamlet';
  ELSEIF rank = 20 THEN
    RETURN 'Suburb';
  ELSEIF rank = 21 THEN
    RETURN 'Postcode Area';
  ELSEIF rank = 22 THEN
    RETURN 'Croft / Farm / Locality / Islet';
  ELSEIF rank = 23 THEN
    RETURN 'Postcode Area';
  ELSEIF rank = 25 THEN
    RETURN 'Postcode Point';
  ELSEIF rank = 26 THEN
    RETURN 'Street / Major Landmark';
  ELSEIF rank = 27 THEN
    RETURN 'Minory Street / Path';
  ELSEIF rank = 28 THEN
    RETURN 'House / Building';
  ELSE
    RETURN 'Other: '||rank;
  END IF;
  
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_addressrank_label(rank INTEGER) RETURNS TEXT
  AS $$
DECLARE
BEGIN
  IF rank = 0 THEN
    RETURN 'None';
  ELSEIF rank < 2 THEN
    RETURN 'Continent';
  ELSEIF rank < 4 THEN
    RETURN 'Sea';
  ELSEIF rank = 5 THEN
    RETURN 'Postcode';
  ELSEIF rank < 8 THEN
    RETURN 'Country';
  ELSEIF rank < 12 THEN
    RETURN 'State';
  ELSEIF rank < 16 THEN
    RETURN 'County';
  ELSEIF rank = 16 THEN
    RETURN 'City';
  ELSEIF rank = 17 THEN
    RETURN 'Town / Village / Hamlet';
  ELSEIF rank = 20 THEN
    RETURN 'Suburb';
  ELSEIF rank = 21 THEN
    RETURN 'Postcode Area';
  ELSEIF rank = 22 THEN
    RETURN 'Croft / Farm / Locality / Islet';
  ELSEIF rank = 23 THEN
    RETURN 'Postcode Area';
  ELSEIF rank = 25 THEN
    RETURN 'Postcode Point';
  ELSEIF rank = 26 THEN
    RETURN 'Street / Major Landmark';
  ELSEIF rank = 27 THEN
    RETURN 'Minory Street / Path';
  ELSEIF rank = 28 THEN
    RETURN 'House / Building';
  ELSE
    RETURN 'Other: '||rank;
  END IF;
  
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION aux_create_property(pointgeo GEOMETRY, in_housenumber TEXT, 
  in_street TEXT, in_isin TEXT, in_postcode TEXT, in_countrycode char(2)) RETURNS INTEGER
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
  insert into location_property_aux (place_id, partition, parent_place_id, housenumber, postcode, centroid)
    values (nextval('seq_place'), out_partition, out_parent_place_id, in_housenumber, out_postcode, place_centroid);
  newpoints := newpoints + 1;

  RETURN newpoints;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_osm_rel_members(members TEXT[], member TEXT) RETURNS TEXT[]
  AS $$
DECLARE
  result TEXT[];
  i INTEGER;
BEGIN

  FOR i IN 1..ARRAY_UPPER(members,1) BY 2 LOOP
    IF members[i+1] = member THEN
      result := result || members[i];
    END IF;
  END LOOP;

  return result;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_osm_rel_members(members TEXT[], memberLabels TEXT[]) RETURNS SETOF TEXT
  AS $$
DECLARE
  i INTEGER;
BEGIN

  FOR i IN 1..ARRAY_UPPER(members,1) BY 2 LOOP
    IF members[i+1] = ANY(memberLabels) THEN
      RETURN NEXT members[i];
    END IF;
  END LOOP;

  RETURN;
END;
$$
LANGUAGE plpgsql;

-- See: http://stackoverflow.com/questions/6410088/how-can-i-mimic-the-php-urldecode-function-in-postgresql
CREATE OR REPLACE FUNCTION decode_url_part(p varchar) RETURNS varchar 
  AS $$
SELECT convert_from(CAST(E'\\x' || array_to_string(ARRAY(
    SELECT CASE WHEN length(r.m[1]) = 1 THEN encode(convert_to(r.m[1], 'SQL_ASCII'), 'hex') ELSE substring(r.m[1] from 2 for 2) END
    FROM regexp_matches($1, '%[0-9a-f][0-9a-f]|.', 'gi') AS r(m)
), '') AS bytea), 'UTF8');
$$ 
LANGUAGE SQL IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION catch_decode_url_part(p varchar) RETURNS varchar
  AS $$
DECLARE
BEGIN
  RETURN decode_url_part(p);
EXCEPTION
  WHEN others THEN return null;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

DROP TYPE wikipedia_article_match CASCADE;
create type wikipedia_article_match as (
  language TEXT,
  title TEXT,
  importance FLOAT
);

CREATE OR REPLACE FUNCTION get_wikipedia_match(extratags HSTORE, country_code varchar(2)) RETURNS wikipedia_article_match
  AS $$
DECLARE
  langs TEXT[];
  i INT;
  wiki_article TEXT;
  wiki_article_title TEXT;
  wiki_article_language TEXT;
  result wikipedia_article_match;
BEGIN
  langs := ARRAY['english','country','ar','bg','ca','cs','da','de','en','es','eo','eu','fa','fr','ko','hi','hr','id','it','he','lt','hu','ms','nl','ja','no','pl','pt','kk','ro','ru','sk','sl','sr','fi','sv','tr','uk','vi','vo','war','zh'];
  i := 1;
  WHILE langs[i] IS NOT NULL LOOP
    wiki_article := extratags->(case when langs[i] in ('english','country') THEN 'wikipedia' ELSE 'wikipedia:'||langs[i] END);
    IF wiki_article is not null THEN
      wiki_article := regexp_replace(wiki_article,E'^(.*?)([a-z]{2,3}).wikipedia.org/wiki/',E'\\2:');
      wiki_article := regexp_replace(wiki_article,E'^(.*?)([a-z]{2,3}).wikipedia.org/w/index.php\\?title=',E'\\2:');
      wiki_article := regexp_replace(wiki_article,E'^(.*?)/([a-z]{2,3})/wiki/',E'\\2:');
      --wiki_article := regexp_replace(wiki_article,E'^(.*?)([a-z]{2,3})[=:]',E'\\2:');
      wiki_article := replace(wiki_article,' ','_');
      IF strpos(wiki_article, ':') IN (3,4) THEN
        wiki_article_language := lower(trim(split_part(wiki_article, ':', 1)));
        wiki_article_title := trim(substr(wiki_article, strpos(wiki_article, ':')+1));
      ELSE
        wiki_article_title := trim(wiki_article);
        wiki_article_language := CASE WHEN langs[i] = 'english' THEN 'en' WHEN langs[i] = 'country' THEN get_country_language_code(country_code) ELSE langs[i] END;
      END IF;

      select wikipedia_article.language,wikipedia_article.title,wikipedia_article.importance
        from wikipedia_article 
        where language = wiki_article_language and 
        (title = wiki_article_title OR title = catch_decode_url_part(wiki_article_title) OR title = replace(catch_decode_url_part(wiki_article_title),E'\\',''))
      UNION ALL
      select wikipedia_article.language,wikipedia_article.title,wikipedia_article.importance
        from wikipedia_redirect join wikipedia_article on (wikipedia_redirect.language = wikipedia_article.language and wikipedia_redirect.to_title = wikipedia_article.title)
        where wikipedia_redirect.language = wiki_article_language and 
        (from_title = wiki_article_title OR from_title = catch_decode_url_part(wiki_article_title) OR from_title = replace(catch_decode_url_part(wiki_article_title),E'\\',''))
      order by importance desc limit 1 INTO result;

      IF result.language is not null THEN
        return result;
      END IF;
    END IF;
    i := i + 1;
  END LOOP;
  RETURN NULL;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION quad_split_geometry(geometry GEOMETRY, maxarea FLOAT, maxdepth INTEGER) 
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
LANGUAGE plpgsql;

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
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION place_force_delete(placeid BIGINT) RETURNS BOOLEAN
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
  -- force delete from place/placex by making it a very small geometry
  UPDATE place set geometry = ST_SetSRID(ST_Point(0,0), 4326) where osm_type = osmtype and osm_id = osmid and class = pclass and type = ptype;
  DELETE FROM place where osm_type = osmtype and osm_id = osmid and class = pclass and type = ptype;

  RETURN TRUE;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION place_force_update(placeid BIGINT) RETURNS BOOLEAN
  AS $$
DECLARE
  placegeom GEOMETRY;
  geom GEOMETRY;
  diameter FLOAT;
  rank INTEGER;
BEGIN
  UPDATE placex SET indexed_status = 2 WHERE place_id = placeid;
  SELECT geometry, rank_search FROM placex WHERE place_id = placeid INTO placegeom, rank;
  IF placegeom IS NOT NULL AND ST_IsValid(placegeom) THEN
    IF ST_GeometryType(placegeom) in ('ST_Polygon','ST_MultiPolygon') THEN
      FOR geom IN select split_geometry(placegeom) FROM placex WHERE place_id = placeid LOOP
        update placex set indexed_status = 2 where (st_covers(geom, placex.geometry) OR ST_Intersects(geom, placex.geometry)) 
        AND rank_search > rank and indexed_status = 0 and ST_geometrytype(placex.geometry) = 'ST_Point' and (rank_search < 28 or name is not null or (rank >= 16 and address ? 'place'));
        update placex set indexed_status = 2 where (st_covers(geom, placex.geometry) OR ST_Intersects(geom, placex.geometry)) 
        AND rank_search > rank and indexed_status = 0 and ST_geometrytype(placex.geometry) != 'ST_Point' and (rank_search < 28 or name is not null or (rank >= 16 and address ? 'place'));
      END LOOP;
    ELSE
        diameter := 0;
        IF rank = 11 THEN
          diameter := 0.05;
        ELSEIF rank < 18 THEN
          diameter := 0.1;
        ELSEIF rank < 20 THEN
          diameter := 0.05;
        ELSEIF rank = 21 THEN
          diameter := 0.001;
        ELSEIF rank < 24 THEN
          diameter := 0.02;
        ELSEIF rank < 26 THEN
          diameter := 0.002; -- 100 to 200 meters
        ELSEIF rank < 28 THEN
          diameter := 0.001; -- 50 to 100 meters
        END IF;
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
