--DROP TRIGGER IF EXISTS place_before_insert on placex;
--DROP TRIGGER IF EXISTS place_before_update on placex;
--CREATE TYPE addresscalculationtype AS (
--  word text,
--  score integer
--);


CREATE OR REPLACE FUNCTION getclasstypekey(c text, t text) RETURNS TEXT
  AS $$
DECLARE
BEGIN
  RETURN c||'|'||t;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION isbrokengeometry(place geometry) RETURNS BOOLEAN
  AS $$
DECLARE
  NEWgeometry geometry;
BEGIN
  NEWgeometry := place;
  IF ST_IsEmpty(NEWgeometry) OR NOT ST_IsValid(NEWgeometry) OR ST_X(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') THEN  
    RETURN true;
  END IF;
  RETURN false;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION clean_geometry(place geometry) RETURNS geometry
  AS $$
DECLARE
  NEWgeometry geometry;
BEGIN
  NEWgeometry := place;
  IF ST_X(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') THEN  
    NEWgeometry := ST_buffer(NEWgeometry,0);
    IF ST_X(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') THEN  
      RETURN ST_SetSRID(ST_Point(0,0),4326);
    END IF;
  END IF;
  RETURN NEWgeometry;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION geometry_sector(partition INTEGER, place geometry) RETURNS INTEGER
  AS $$
DECLARE
  NEWgeometry geometry;
BEGIN
--  RAISE WARNING '%',place;
  NEWgeometry := place;
  IF ST_IsEmpty(NEWgeometry) OR NOT ST_IsValid(NEWgeometry) OR ST_X(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') THEN  
    NEWgeometry := ST_buffer(NEWgeometry,0);
    IF ST_IsEmpty(NEWgeometry) OR NOT ST_IsValid(NEWgeometry) OR ST_X(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') THEN  
      RETURN 0;
    END IF;
  END IF;
  RETURN (partition*1000000) + (500-ST_X(ST_Centroid(NEWgeometry))::integer)*1000 + (500-ST_Y(ST_Centroid(NEWgeometry))::integer);
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION debug_geometry_sector(osmid integer, place geometry) RETURNS INTEGER
  AS $$
DECLARE
  NEWgeometry geometry;
BEGIN
--  RAISE WARNING '%',osmid;
  IF osmid = 61315 THEN
    return null;
  END IF;
  NEWgeometry := place;
  IF ST_IsEmpty(NEWgeometry) OR NOT ST_IsValid(NEWgeometry) OR ST_X(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') THEN  
    NEWgeometry := ST_buffer(NEWgeometry,0);
    IF ST_IsEmpty(NEWgeometry) OR NOT ST_IsValid(NEWgeometry) OR ST_X(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEWgeometry))::text in ('NaN','Infinity','-Infinity') THEN  
      RETURN NULL;
    END IF;
  END IF;
  RETURN (500-ST_X(ST_Centroid(NEWgeometry))::integer)*1000 + (500-ST_Y(ST_Centroid(NEWgeometry))::integer);
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
  o := gettokenstring(transliteration(name));
  RETURN trim(substr(o,1,length(o)));
END;
$$
LANGUAGE 'plpgsql' IMMUTABLE;

CREATE OR REPLACE FUNCTION getorcreate_word_id(lookup_word TEXT) 
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and class is null and type is null into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, regexp_replace(lookup_token,E'([^0-9])\\1+',E'\\1','g'), null, null, null, null, 0, null);
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
    INSERT INTO word VALUES (return_word_id, lookup_token, null, null, 'place', 'house', null, 0, null);
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
    INSERT INTO word VALUES (return_word_id, lookup_token, null, null, null, null, lookup_country_code, 0, null);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_amenity(lookup_word TEXT, lookup_class text, lookup_type text)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and class=lookup_class and type = lookup_type into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, null, null, lookup_class, lookup_type, null, 0, null);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_tagpair(lookup_class text, lookup_type text)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := lookup_class||'='||lookup_type;
  SELECT min(word_id) FROM word WHERE word_token = lookup_token into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, null, null, null, null, null, 0, null);
  END IF;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_tagpair(lookup_class text, lookup_type text)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := lookup_class||'='||lookup_type;
  SELECT min(word_id) FROM word WHERE word_token = lookup_token into return_word_id;
  RETURN return_word_id;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION getorcreate_amenityoperator(lookup_word TEXT, lookup_class text, lookup_type text, op text)
  RETURNS INTEGER
  AS $$
DECLARE
  lookup_token TEXT;
  return_word_id INTEGER;
BEGIN
  lookup_token := ' '||trim(lookup_word);
  SELECT min(word_id) FROM word WHERE word_token = lookup_token and class=lookup_class and type = lookup_type and operator = op into return_word_id;
  IF return_word_id IS NULL THEN
    return_word_id := nextval('seq_word');
    INSERT INTO word VALUES (return_word_id, lookup_token, null, null, lookup_class, lookup_type, null, 0, op, null);
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
    INSERT INTO word VALUES (return_word_id, lookup_token, regexp_replace(lookup_token,E'([^0-9])\\1+',E'\\1','g'), src_word, null, null, null, 0, null);
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

    words := string_to_array(s, ' ');
    IF array_upper(words, 1) IS NOT NULL THEN
      FOR j IN 1..array_upper(words, 1) LOOP
        IF (words[j] != '') THEN
          w = getorcreate_word_id(words[j]);
          IF NOT (ARRAY[w] <@ result) THEN
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
          IF NOT (ARRAY[w] <@ result) THEN
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
  w := getorcreate_name_id(s);

  IF NOT (ARRAY[w] <@ result) THEN
    result := result || w;
  END IF;

  words := string_to_array(s, ' ');
  IF array_upper(words, 1) IS NOT NULL THEN
    FOR j IN 1..array_upper(words, 1) LOOP
      IF (words[j] != '') THEN
        w = getorcreate_word_id(words[j]);
        IF NOT (ARRAY[w] <@ result) THEN
          result := result || w;
        END IF;
      END IF;
    END LOOP;
  END IF;

  RETURN result;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_word_score(wordscores wordscore[], words text[]) RETURNS integer
  AS $$
DECLARE
  idxword integer;
  idxscores integer;
  result integer;
BEGIN
  IF (wordscores is null OR words is null) THEN
    RETURN 0;
  END IF;

  result := 0;
  FOR idxword in 1 .. array_upper(words, 1) LOOP
    FOR idxscores in 1 .. array_upper(wordscores, 1) LOOP
      IF wordscores[idxscores].word = words[idxword] THEN
        result := result + wordscores[idxscores].score;
      END IF;
    END LOOP;
  END LOOP;

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
  place_centre := ST_Centroid(place);

--RAISE WARNING 'start: %', ST_AsText(place_centre);

  -- Try for a OSM polygon first
  FOR nearcountry IN select country_code from location_area_country where country_code is not null and not isguess and st_contains(geometry, place_centre) limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

--RAISE WARNING 'osm fallback: %', ST_AsText(place_centre);

  -- Try for OSM fallback data
  FOR nearcountry IN select country_code from country_osm_grid where st_contains(geometry, place_centre) limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

--RAISE WARNING 'natural earth: %', ST_AsText(place_centre);

  -- Natural earth data (first fallback)
  FOR nearcountry IN select country_code from country_naturalearthdata where st_contains(geometry, place_centre) limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

  -- Natural earth data (first fallback)
  FOR nearcountry IN select country_code from country_naturalearthdata where st_distance(geometry, place_centre) < 0.5 limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

--RAISE WARNING 'in country: %', ST_AsText(place_centre);

  -- WorldBoundaries data (second fallback - think there might be something broken in this data)
  FOR nearcountry IN select country_code from country where st_contains(geometry, place_centre) limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

--RAISE WARNING 'near country: %', ST_AsText(place_centre);

  -- Still not in a country - try nearest within ~12 miles of a country
  FOR nearcountry IN select country_code from country where st_distance(geometry, place_centre) < 0.5 
    order by st_distance(geometry, place) limit 1
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;

  RETURN NULL;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_country_code(place geometry, in_country_code VARCHAR(2)) RETURNS TEXT
  AS $$
DECLARE
  nearcountry RECORD;
BEGIN
  FOR nearcountry IN select country_code from country_name where country_code = lower(in_country_code)
  LOOP
    RETURN nearcountry.country_code;
  END LOOP;
  RETURN get_country_code(place);
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

CREATE OR REPLACE FUNCTION get_partition(place geometry, in_country_code VARCHAR(10)) RETURNS INTEGER
  AS $$
DECLARE
  place_centre GEOMETRY;
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
    geometry GEOMETRY
  ) 
  RETURNS BOOLEAN
  AS $$
DECLARE
  locationid INTEGER;
  isarea BOOLEAN;
  xmin INTEGER;
  ymin INTEGER;
  xmax INTEGER;
  ymax INTEGER;
  lon INTEGER;
  lat INTEGER;
  centroid GEOMETRY;
  secgeo GEOMETRY;
  secbox GEOMETRY;
  diameter FLOAT;
  x BOOLEAN;
BEGIN

  IF rank_search > 25 THEN
    RAISE EXCEPTION 'Adding location with rank > 25 (% rank %)', place_id, rank_search;
  END IF;

--  RAISE WARNING 'Adding location with rank > 25 (% rank %)', place_id, rank_search;

  x := deleteLocationArea(partition, place_id);

  isarea := false;
  IF (ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') AND ST_IsValid(geometry)) THEN

    isArea := true;
    centroid := ST_Centroid(geometry);

    xmin := floor(st_xmin(geometry));
    xmax := ceil(st_xmax(geometry));
    ymin := floor(st_ymin(geometry));
    ymax := ceil(st_ymax(geometry));

    IF xmin = xmax OR ymin = ymax OR (xmax-xmin < 2 AND ymax-ymin < 2) THEN
      x := insertLocationAreaLarge(partition, place_id, country_code, keywords, rank_search, rank_address, false, centroid, geometry);
    ELSE
--      RAISE WARNING 'Spliting geometry: % to %, % to %', xmin, xmax, ymin, ymax;
      FOR lon IN xmin..(xmax-1) LOOP
        FOR lat IN ymin..(ymax-1) LOOP
          secbox := ST_SetSRID(ST_MakeBox2D(ST_Point(lon,lat),ST_Point(lon+1,lat+1)),4326);
          IF st_intersects(geometry, secbox) THEN
            secgeo := st_intersection(geometry, secbox);
            IF NOT ST_IsEmpty(secgeo) AND ST_GeometryType(secgeo) in ('ST_Polygon','ST_MultiPolygon') THEN
              x := insertLocationAreaLarge(partition, place_id, country_code, keywords, rank_search, rank_address, false, centroid, secgeo);
            END IF;
          END IF;
        END LOOP;
      END LOOP;
    END IF;

  ELSEIF rank_search < 26 THEN

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
    x := insertLocationAreaLarge(partition, place_id, country_code, keywords, rank_search, rank_address, true, ST_Centroid(geometry), secgeo);

  ELSE

    -- ~ 20meters
    secgeo := ST_Buffer(geometry, 0.0002);
    x := insertLocationAreaRoadNear(partition, place_id, country_code, keywords, rank_search, rank_address, true, ST_Centroid(geometry), secgeo);

    -- ~ 100meters
    secgeo := ST_Buffer(geometry, 0.001);
    x := insertLocationAreaRoadFar(partition, place_id, country_code, keywords, rank_search, rank_address, true, ST_Centroid(geometry), secgeo);

  END IF;

  RETURN true;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_location(
    partition INTEGER,
    place_id BIGINT,
    place_country_code varchar(2),
    name hstore,
    rank_search INTEGER,
    rank_address INTEGER,
    geometry GEOMETRY
  ) 
  RETURNS BOOLEAN
  AS $$
DECLARE
  b BOOLEAN;
BEGIN
  b := deleteLocationArea(partition, place_id);
--  result := add_location(NEW.place_id, NEW.country_code, NEW.partition, name_vector, NEW.rank_search, NEW.rank_address, NEW.geometry);
  RETURN add_location(place_id, place_country_code, name, rank_search, rank_address, geometry);
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_name_add_words(parent_place_id BIGINT, to_add INTEGER[])
  RETURNS BOOLEAN
  AS $$
DECLARE
  childplace RECORD;
BEGIN

  IF #to_add = 0 THEN
    RETURN true;
  END IF;

  -- this should just be an update, but it seems to do insane things to the index size (delete and insert doesn't)
  FOR childplace IN select * from search_name,place_addressline 
    where  address_place_id = parent_place_id
      and search_name.place_id = place_addressline.place_id
  LOOP
    delete from search_name where place_id = childplace.place_id;
    IF not (ARRAY[to_add] <@ childplace.nameaddress_vector) THEN
      childplace.nameaddress_vector := childplace.nameaddress_vector || to_add;
    END IF;
    IF childplace.place_id = parent_place_id and not (ARRAY[to_add] <@ childplace.name_vector) THEN
      childplace.name_vector := childplace.name_vector || to_add;
    END IF;
    insert into search_name (place_id, search_rank, address_rank, country_code, name_vector, nameaddress_vector, centroid) 
      values (childplace.place_id, childplace.search_rank, childplace.address_rank, childplace.country_code, 
        childplace.name_vector, childplace.nameaddress_vector, childplace.centroid);
  END LOOP;

  RETURN true;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_location_nameonly(partition INTEGER, OLD_place_id BIGINT, name hstore) RETURNS BOOLEAN
  AS $$
DECLARE
  newkeywords INTEGER[];
  addedkeywords INTEGER[];
  removedkeywords INTEGER[];
BEGIN

  -- what has changed?
  newkeywords := make_keywords(name);
  select coalesce(newkeywords,'{}'::INTEGER[]) - coalesce(location_point.keywords,'{}'::INTEGER[]), 
    coalesce(location_point.keywords,'{}'::INTEGER[]) - coalesce(newkeywords,'{}'::INTEGER[]) from location_point 
    where place_id = OLD_place_id into addedkeywords, removedkeywords;

--  RAISE WARNING 'update_location_nameonly for %: new:% added:% removed:%', OLD_place_id, newkeywords, addedkeywords, removedkeywords;

  IF #removedkeywords > 0 THEN
    -- abort due to tokens removed
    RETURN false;
  END IF;
  
  IF #addedkeywords > 0 THEN
    -- short circuit - no changes
    RETURN true;
  END IF;

  UPDATE location_area set keywords = newkeywords where place_id = OLD_place_id;
  RETURN search_name_add_words(OLD_place_id, addedkeywords);
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION create_interpolation(wayid BIGINT, interpolationtype TEXT) RETURNS INTEGER
  AS $$
DECLARE
  
  newpoints INTEGER;
  waynodes integer[];
  nodeid INTEGER;
  prevnode RECORD;
  nextnode RECORD;
  startnumber INTEGER;
  endnumber INTEGER;
  stepsize INTEGER;
  orginalstartnumber INTEGER;
  originalnumberrange INTEGER;
  housenum INTEGER;
  linegeo GEOMETRY;
  search_place_id BIGINT;
  defpostalcode TEXT;

  havefirstpoint BOOLEAN;
  linestr TEXT;
BEGIN
  newpoints := 0;
  IF interpolationtype = 'odd' OR interpolationtype = 'even' OR interpolationtype = 'all' THEN

    select postcode from placex where osm_type = 'W' and osm_id = wayid INTO defpostalcode;
    select nodes from planet_osm_ways where id = wayid INTO waynodes;
--RAISE WARNING 'interpolation % % %',wayid,interpolationtype,waynodes;
    IF array_upper(waynodes, 1) IS NOT NULL THEN

      havefirstpoint := false;

      FOR nodeidpos in 1..array_upper(waynodes, 1) LOOP

        select min(place_id) from placex where osm_type = 'N' and osm_id = waynodes[nodeidpos]::INTEGER and type = 'house' INTO search_place_id;
        IF search_place_id IS NULL THEN
          -- null record of right type
          select * from placex where osm_type = 'N' and osm_id = waynodes[nodeidpos]::INTEGER and type = 'house' limit 1 INTO nextnode;
          select ST_SetSRID(ST_Point(lon::float/10000000,lat::float/10000000),4326) from planet_osm_nodes where id = waynodes[nodeidpos] INTO nextnode.geometry;
        ELSE
          select * from placex where place_id = search_place_id INTO nextnode;
        END IF;

--RAISE WARNING 'interpolation node % % % ',nextnode.housenumber,ST_X(nextnode.geometry),ST_Y(nextnode.geometry);
      
        IF havefirstpoint THEN

          -- add point to the line string
          linestr := linestr||','||ST_X(nextnode.geometry)||' '||ST_Y(nextnode.geometry);
          endnumber := ('0'||substring(nextnode.housenumber,'[0-9]+'))::integer;

          IF startnumber IS NOT NULL and startnumber > 0 AND endnumber IS NOT NULL and endnumber > 0 AND @(startnumber - endnumber) < 1000 THEN

--RAISE WARNING 'interpolation end % % ',nextnode.place_id,endnumber;

            IF startnumber != endnumber THEN

              linestr := linestr || ')';
--RAISE WARNING 'linestr %',linestr;
              linegeo := ST_GeomFromText(linestr,4326);
              linestr := 'LINESTRING('||ST_X(nextnode.geometry)||' '||ST_Y(nextnode.geometry);
              IF (startnumber > endnumber) THEN
                housenum := endnumber;
                endnumber := startnumber;
                startnumber := housenum;
                linegeo := ST_Reverse(linegeo);
              END IF;
              orginalstartnumber := startnumber;
              originalnumberrange := endnumber - startnumber;

-- Too much broken data worldwide for this test to be worth using
--              IF originalnumberrange > 500 THEN
--                RAISE WARNING 'Number block of % while processing % %', originalnumberrange, prevnode, nextnode;
--              END IF;

              IF (interpolationtype = 'odd' AND startnumber%2 = 0) OR (interpolationtype = 'even' AND startnumber%2 = 1) THEN
                startnumber := startnumber + 1;
                stepsize := 2;
              ELSE
                IF (interpolationtype = 'odd' OR interpolationtype = 'even') THEN
                  startnumber := startnumber + 2;
                  stepsize := 2;
                ELSE -- everything else assumed to be 'all'
                  startnumber := startnumber + 1;
                  stepsize := 1;
                END IF;
              END IF;
              endnumber := endnumber - 1;
              delete from placex where osm_type = 'N' and osm_id = prevnode.osm_id and type = 'house' and place_id != prevnode.place_id;
              FOR housenum IN startnumber..endnumber BY stepsize LOOP
                -- this should really copy postcodes but it puts a huge burdon on the system for no big benefit
                -- ideally postcodes should move up to the way
                insert into placex (osm_type, osm_id, class, type, admin_level, housenumber, street, isin, postcode,
                  country_code, parent_place_id, rank_address, rank_search, indexed_status, geometry)
                  values ('N',prevnode.osm_id, prevnode.class, prevnode.type, prevnode.admin_level, housenum, prevnode.street, prevnode.isin, coalesce(prevnode.postcode, defpostalcode),
                  prevnode.country_code, prevnode.parent_place_id, prevnode.rank_address, prevnode.rank_search, 1, ST_Line_Interpolate_Point(linegeo, (housenum::float-orginalstartnumber::float)/originalnumberrange::float));
                newpoints := newpoints + 1;
--RAISE WARNING 'interpolation number % % ',prevnode.place_id,housenum;
              END LOOP;
            END IF;
            havefirstpoint := false;
          END IF;
        END IF;

        IF NOT havefirstpoint THEN
          startnumber := ('0'||substring(nextnode.housenumber,'[0-9]+'))::integer;
          IF startnumber IS NOT NULL AND startnumber > 0 THEN
            havefirstpoint := true;
            linestr := 'LINESTRING('||ST_X(nextnode.geometry)||' '||ST_Y(nextnode.geometry);
            prevnode := nextnode;
          END IF;
--RAISE WARNING 'interpolation start % % ',nextnode.place_id,startnumber;
        END IF;
      END LOOP;
    END IF;
  END IF;

--RAISE WARNING 'interpolation points % ',newpoints;

  RETURN newpoints;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION placex_insert() RETURNS TRIGGER
  AS $$
DECLARE
  i INTEGER;
  postcode TEXT;
  result BOOLEAN;
  country_code VARCHAR(2);
  default_language VARCHAR(10);
  diameter FLOAT;
  classtable TEXT;
BEGIN
--  RAISE WARNING '%',NEW.osm_id;

  -- just block these
  IF NEW.class = 'highway' and NEW.type in ('turning_circle','traffic_signals','mini_roundabout','noexit','crossing') THEN
--    RAISE WARNING 'bad highway %',NEW.osm_id;
    RETURN null;
  END IF;
  IF NEW.class in ('landuse','natural') and NEW.name is null THEN
--    RAISE WARNING 'empty landuse %',NEW.osm_id;
    RETURN null;
  END IF;

  IF ST_IsEmpty(NEW.geometry) OR NOT ST_IsValid(NEW.geometry) OR ST_X(ST_Centroid(NEW.geometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEW.geometry))::text in ('NaN','Infinity','-Infinity') THEN  
    -- block all invalid geometary - just not worth the risk.  seg faults are causing serious problems.
--    RAISE WARNING 'invalid geometry %',NEW.osm_id;
    RETURN NULL;

    -- Dead code
    IF NEW.osm_type = 'R' THEN
      -- invalid multipolygons can crash postgis, don't even bother to try!
      RETURN NULL;
    END IF;
    NEW.geometry := ST_buffer(NEW.geometry,0);
    IF ST_IsEmpty(NEW.geometry) OR NOT ST_IsValid(NEW.geometry) OR ST_X(ST_Centroid(NEW.geometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEW.geometry))::text in ('NaN','Infinity','-Infinity') THEN  
--      RAISE WARNING 'Invalid geometary, rejecting: % %', NEW.osm_type, NEW.osm_id;
      RETURN NULL;
    END IF;
  END IF;

  NEW.place_id := nextval('seq_place');
  NEW.indexed_status := 1; --STATUS_NEW

  IF NEW.rank_search >= 4 THEN
    NEW.country_code := lower(get_country_code(NEW.geometry, NEW.country_code));
  ELSE
    NEW.country_code := NULL;
  END IF;

  NEW.partition := get_partition(NEW.geometry, NEW.country_code);
  NEW.geometry_sector := geometry_sector(NEW.partition, NEW.geometry);

  -- copy 'name' to or from the default language (if there is a default language)
  IF NEW.name is not null AND array_upper(akeys(NEW.name),1) > 1 THEN
    default_language := get_country_language_code(NEW.country_code);
    IF default_language IS NOT NULL THEN
      IF NEW.name ? 'name' AND NOT NEW.name ? ('name:'||default_language) THEN
        NEW.name := NEW.name || (('name:'||default_language) => (NEW.name -> 'name'));
      ELSEIF NEW.name ? ('name:'||default_language) AND NOT NEW.name ? 'name' THEN
        NEW.name := NEW.name || ('name' => (NEW.name -> ('name:'||default_language)));
      END IF;
    END IF;
  END IF;

  IF NEW.admin_level > 15 THEN
    NEW.admin_level := 15;
  END IF;

  IF NEW.housenumber IS NOT NULL THEN
    i := getorcreate_housenumber_id(make_standard_name(NEW.housenumber));
  END IF;

  IF NEW.osm_type = 'X' THEN
    -- E'X'ternal records should already be in the right format so do nothing
  ELSE
    NEW.rank_search := 30;
    NEW.rank_address := NEW.rank_search;

    -- By doing in postgres we have the country available to us - currently only used for postcode
    IF NEW.class in ('place','boundary') AND NEW.type in ('postcode','postal_code') THEN

        IF NEW.postcode IS NULL THEN
            -- most likely just a part of a multipolygon postcode boundary, throw it away
            RETURN NULL;
        END IF;

        NEW.name := 'ref'=>NEW.postcode;

        IF NEW.country_code = 'gb' THEN

          IF NEW.postcode ~ '^([A-Z][A-Z]?[0-9][0-9A-Z]? [0-9][A-Z][A-Z])$' THEN
            NEW.rank_search := 25;
            NEW.rank_address := 5;
          ELSEIF NEW.postcode ~ '^([A-Z][A-Z]?[0-9][0-9A-Z]? [0-9])$' THEN
            NEW.rank_search := 23;
            NEW.rank_address := 5;
          ELSEIF NEW.postcode ~ '^([A-Z][A-Z]?[0-9][0-9A-Z])$' THEN
            NEW.rank_search := 21;
            NEW.rank_address := 5;
          END IF;

        ELSEIF NEW.country_code = 'de' THEN

          IF NEW.postcode ~ '^([0-9]{5})$' THEN
            NEW.rank_search := 21;
            NEW.rank_address := 11;
          END IF;

        ELSE
          -- Guess at the postcode format and coverage (!)
          IF upper(NEW.postcode) ~ '^[A-Z0-9]{1,5}$' THEN -- Probably too short to be very local
            NEW.rank_search := 21;
            NEW.rank_address := 11;
          ELSE
            -- Does it look splitable into and area and local code?
            postcode := substring(upper(NEW.postcode) from '^([- :A-Z0-9]+)([- :][A-Z0-9]+)$');

            IF postcode IS NOT NULL THEN
              NEW.rank_search := 25;
              NEW.rank_address := 11;
            ELSEIF NEW.postcode ~ '^[- :A-Z0-9]{6,}$' THEN
              NEW.rank_search := 21;
              NEW.rank_address := 11;
            END IF;
          END IF;
        END IF;

    ELSEIF NEW.class = 'place' THEN
      IF NEW.type in ('continent') THEN
        NEW.rank_search := 2;
        NEW.rank_address := NEW.rank_search;
      ELSEIF NEW.type in ('sea') THEN
        NEW.rank_search := 2;
        NEW.rank_address := 0;
      ELSEIF NEW.type in ('country') THEN
        NEW.rank_search := 4;
        NEW.rank_address := NEW.rank_search;
      ELSEIF NEW.type in ('state') THEN
        NEW.rank_search := 8;
        NEW.rank_address := NEW.rank_search;
      ELSEIF NEW.type in ('region') THEN
        NEW.rank_search := 18; -- dropped from previous value of 10
        NEW.rank_address := 0; -- So badly miss-used that better to just drop it!
      ELSEIF NEW.type in ('county') THEN
        NEW.rank_search := 12;
        NEW.rank_address := NEW.rank_search;
      ELSEIF NEW.type in ('city') THEN
        NEW.rank_search := 16;
        NEW.rank_address := NEW.rank_search;
      ELSEIF NEW.type in ('island') THEN
        NEW.rank_search := 17;
        NEW.rank_address := 0;
      ELSEIF NEW.type in ('town') THEN
        NEW.rank_search := 18;
        NEW.rank_address := 16;
      ELSEIF NEW.type in ('village','hamlet','municipality','district','unincorporated_area','borough') THEN
        NEW.rank_search := 19;
        NEW.rank_address := 16;
      ELSEIF NEW.type in ('airport') AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon') THEN
        NEW.rank_search := 18;
        NEW.rank_address := 17;
      ELSEIF NEW.type in ('moor') AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon') THEN
        NEW.rank_search := 17;
        NEW.rank_address := 18;
      ELSEIF NEW.type in ('moor') THEN
        NEW.rank_search := 17;
        NEW.rank_address := 0;
      ELSEIF NEW.type in ('national_park') THEN
        NEW.rank_search := 18;
        NEW.rank_address := 18;
      ELSEIF NEW.type in ('suburb','croft','subdivision') THEN
        NEW.rank_search := 20;
        NEW.rank_address := NEW.rank_search;
      ELSEIF NEW.type in ('farm','locality','islet','isolated_dwelling','mountain_pass') THEN
        NEW.rank_search := 20;
        NEW.rank_address := 0;
        -- Irish townlands, tagged as place=locality and locality=townland
        IF (NEW.extratags -> 'locality') = 'townland' THEN
          NEW.rank_address := 20;
        END IF;
      ELSEIF NEW.type in ('hall_of_residence','neighbourhood','housing_estate','nature_reserve') THEN
        NEW.rank_search := 22;
        NEW.rank_address := 22;
      ELSEIF NEW.type in ('airport','street') THEN
        NEW.rank_search := 26;
        NEW.rank_address := NEW.rank_search;
      ELSEIF NEW.type in ('house','building') THEN
        NEW.rank_search := 30;
        NEW.rank_address := NEW.rank_search;
      ELSEIF NEW.type in ('houses') THEN
        -- can't guarantee all required nodes loaded yet due to caching in osm2pgsql
        -- insert new point into place for each derived building
        --i := create_interpolation(NEW.osm_id, NEW.housenumber);
        NEW.rank_search := 28;
        NEW.rank_address := 0;
      END IF;

    ELSEIF NEW.class = 'boundary' THEN
      IF ST_GeometryType(NEW.geometry) NOT IN ('ST_Polygon','ST_MultiPolygon') THEN
--        RAISE WARNING 'invalid boundary %',NEW.osm_id;
        return NULL;
      END IF;
      NEW.rank_search := NEW.admin_level * 2;
      NEW.rank_address := NEW.rank_search;
    ELSEIF NEW.class = 'landuse' AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon') THEN
      NEW.rank_search := 22;
      NEW.rank_address := NEW.rank_search;
    -- any feature more than 5 square miles is probably worth indexing
    ELSEIF ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon') AND ST_Area(NEW.geometry) > 0.1 THEN
      NEW.rank_search := 22;
      NEW.rank_address := NEW.rank_search;
    ELSEIF NEW.class = 'highway' AND NEW.name is NULL AND 
           NEW.type in ('service','cycleway','path','footway','steps','bridleway','track','byway','motorway_link','primary_link','trunk_link','secondary_link','tertiary_link') THEN
--      RAISE WARNING 'unnamed minor feature %',NEW.osm_id;
      RETURN NULL;
    ELSEIF NEW.class = 'railway' AND NEW.type in ('rail') THEN
      RETURN NULL;
    ELSEIF NEW.class = 'waterway' AND NEW.name is NULL THEN
      RETURN NULL;
    ELSEIF NEW.class = 'waterway' THEN
      NEW.rank_address := 17;
    ELSEIF NEW.class = 'highway' AND NEW.osm_type != 'N' AND NEW.type in ('service','cycleway','path','footway','steps','bridleway','motorway_link','primary_link','trunk_link','secondary_link','tertiary_link') THEN
      NEW.rank_search := 27;
      NEW.rank_address := NEW.rank_search;
    ELSEIF NEW.class = 'highway' AND NEW.osm_type != 'N' THEN
      NEW.rank_search := 26;
      NEW.rank_address := NEW.rank_search;
    ELSEIF NEW.class = 'natural' and NEW.type = 'sea' THEN
      NEW.rank_search := 4;
      NEW.rank_address := NEW.rank_search;
    ELSEIF NEW.class = 'natural' and NEW.type in ('coastline') THEN
      RETURN NULL;
    ELSEIF NEW.class = 'natural' and NEW.type in ('peak','volcano') THEN
      NEW.rank_search := 18;
      NEW.rank_address := 0;
    END IF;

  END IF;

  IF NEW.rank_search > 30 THEN
    NEW.rank_search := 30;
  END IF;

  IF NEW.rank_address > 30 THEN
    NEW.rank_address := 30;
  END IF;

  IF (NEW.extratags -> 'capital') = 'yes' THEN
    NEW.rank_search := NEW.rank_search -1;
  END IF;

-- Block import below rank 22
--  IF NEW.rank_search > 22 THEN
--    RETURN NULL;
--  END IF;

  RETURN NEW;  -- The following is not needed until doing diff updates, and slows the main index process down

  IF (ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon') AND ST_IsValid(NEW.geometry)) THEN
    -- Performance: We just can't handle re-indexing for country level changes
    IF st_area(NEW.geometry) < 1 THEN
      -- mark items within the geometry for re-indexing
--    RAISE WARNING 'placex poly insert: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;

      -- work around bug in postgis, this may have been fixed in 2.0.0 (see http://trac.osgeo.org/postgis/ticket/547)
      update placex set indexed_status = 2 where (ST_Contains(NEW.geometry, placex.geometry) OR ST_Intersects(NEW.geometry, placex.geometry)) 
       AND rank_search > NEW.rank_search and indexed_status = 0 and ST_geometrytype(placex.geometry) = 'ST_Point' and (rank_search < 28 or name is not null);
      update placex set indexed_status = 2 where (ST_Contains(NEW.geometry, placex.geometry) OR ST_Intersects(NEW.geometry, placex.geometry)) 
       AND rank_search > NEW.rank_search and indexed_status = 0 and ST_geometrytype(placex.geometry) != 'ST_Point' and (rank_search < 28 or name is not null);
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
      update placex set indexed_status = 2 where indexed_status = 0 and rank_search > NEW.rank_search and ST_DWithin(placex.geometry, NEW.geometry, diameter) and (rank_search < 28 or name is not null);
    END IF;

  END IF;

   -- add to tables for special search
   -- Note: won't work on initial import because the classtype tables
   -- do not yet exist. It won't hurt either.
  classtable := 'place_classtype_' || NEW.class || '_' || NEW.type;
  SELECT count(*)>0 FROM pg_tables WHERE tablename = classtable INTO result;
  IF result THEN
    EXECUTE 'INSERT INTO ' || classtable::regclass || ' (place_id, centroid) VALUES ($1,$2)' 
    USING NEW.place_id, ST_Centroid(NEW.geometry);
  END IF;


--  IF NEW.rank_search < 26 THEN
--    RAISE WARNING 'placex insert: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;
--  END IF;

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
--  search_scores wordscore[];
--  search_scores_pos INTEGER;

  i INTEGER;
  iMax FLOAT;
  location RECORD;
  way RECORD;
  relation RECORD;
  relation_members TEXT[];
  relMember RECORD;
  linkedplacex RECORD;
  search_diameter FLOAT;
  search_prevdiameter FLOAT;
  search_maxrank INTEGER;
  address_maxrank INTEGER;
  address_street_word_id INTEGER;
  parent_place_id_rank BIGINT;
  
  isin TEXT[];
  isin_tokens INT[];

  location_rank_search INTEGER;
  location_distance FLOAT;

  tagpairid INTEGER;

  default_language TEXT;
  name_vector INTEGER[];
  nameaddress_vector INTEGER[];

  wiki_article TEXT;
  wiki_article_title TEXT;
  wiki_article_language TEXT;

  result BOOLEAN;
BEGIN

--RAISE WARNING '%',NEW.place_id;
--RAISE WARNING '%', NEW;

  IF NEW.class = 'place' AND NEW.type = 'postcodearea' THEN
    -- Silently do nothing
    RETURN NEW;
  END IF;

  -- deferred delete
  IF OLD.indexed_status = 100 THEN
    delete from placex where place_id = OLD.place_id;
    RETURN NULL;
  END IF;

  IF NEW.indexed_status = 0 and OLD.indexed_status != 0 THEN

    NEW.indexed_date = now();

    IF NEW.class = 'place' AND NEW.type = 'houses' THEN
      i := create_interpolation(NEW.osm_id, NEW.housenumber);
      RETURN NEW;
    END IF;

    IF OLD.indexed_status > 1 THEN
      result := deleteSearchName(NEW.partition, NEW.place_id);
      DELETE FROM place_addressline WHERE place_id = NEW.place_id;
      DELETE FROM place_boundingbox where place_id = NEW.place_id;
      result := deleteRoad(NEW.partition, NEW.place_id);
      result := deleteLocationArea(NEW.partition, NEW.place_id);
      UPDATE placex set linked_place_id = null where linked_place_id = NEW.place_id;
    END IF;

    -- reclaculate country and partition (should probably have a country_code and calculated_country_code as seperate fields)
    IF NEW.rank_search >= 4 THEN
      SELECT country_code from place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type INTO NEW.country_code;
      NEW.country_code := lower(get_country_code(NEW.geometry, NEW.country_code));
    ELSE
      NEW.country_code := NULL;
    END IF;
    NEW.partition := get_partition(NEW.geometry, NEW.country_code);
    NEW.geometry_sector := geometry_sector(NEW.partition, NEW.geometry);

    -- Adding ourselves to the list simplifies address calculations later
    INSERT INTO place_addressline VALUES (NEW.place_id, NEW.place_id, true, true, 0, NEW.rank_address); 

    -- What level are we searching from
    search_maxrank := NEW.rank_search;

    -- Speed up searches - just use the centroid of the feature
    -- cheaper but less acurate
    place_centroid := ST_Centroid(NEW.geometry);
    NEW.centroid := null;

    -- Thought this wasn't needed but when we add new languages to the country_name table
    -- we need to update the existing names
    IF NEW.name is not null AND array_upper(akeys(NEW.name),1) > 1 THEN
      default_language := get_country_language_code(NEW.country_code);
      IF default_language IS NOT NULL THEN
        IF NEW.name ? 'name' AND NOT NEW.name ? ('name:'||default_language) THEN
          NEW.name := NEW.name || (('name:'||default_language) => (NEW.name -> 'name'));
        ELSEIF NEW.name ? ('name:'||default_language) AND NOT NEW.name ? 'name' THEN
          NEW.name := NEW.name || ('name' => (NEW.name -> ('name:'||default_language)));
        END IF;
      END IF;
    END IF;

    -- Initialise the name vector using our name
    name_vector := make_keywords(NEW.name);
    nameaddress_vector := '{}'::int[];

    -- some tag combinations add a special id for search
    tagpairid := get_tagpair(NEW.class,NEW.type);
    IF tagpairid IS NOT NULL THEN
      name_vector := name_vector + tagpairid;
    END IF;

    FOR i IN 1..28 LOOP
      address_havelevel[i] := false;
    END LOOP;

    NEW.importance := null;
    -- WARNING: see duplicate of code below (yuk!)
    IF NEW.extratags?'wikipedia' THEN
      wiki_article := replace(regexp_replace(NEW.extratags->'wikipedia',E'(.*?)([a-z]+).wikipedia.org/wiki/',E'\\2:'),' ','_');
      wiki_article_title := split_part(wiki_article, ':', 2);
      IF wiki_article_title IS NULL OR wiki_article_title = '' THEN
        wiki_article_title := wiki_article;
        wiki_article_language := 'en';
      ELSE
        wiki_article_language := lower(split_part(wiki_article, ':', 1));
      END IF;
--RAISE WARNING '% %', wiki_article_language, wiki_article_title;

      select wikipedia_article.importance,wikipedia_article.language||':'||wikipedia_article.title 
        from wikipedia_article 
        where language = wiki_article_language and 
        (title = wiki_article_title OR title = decode_url_part(wiki_article_title) OR title = replace(decode_url_part(wiki_article_title),E'\\',''))
      UNION ALL
      select wikipedia_article.importance,wikipedia_article.language||':'||wikipedia_article.title 
        from wikipedia_redirect join wikipedia_article on (wikipedia_redirect.language = wikipedia_article.language and wikipedia_redirect.to_title = wikipedia_article.title)
        where wikipedia_redirect.language = wiki_article_language and 
        (from_title = wiki_article_title OR from_title = decode_url_part(wiki_article_title) OR from_title = replace(decode_url_part(wiki_article_title),E'\\',''))
      order by importance asc limit 1 INTO NEW.importance,NEW.wikipedia;

    ELSE
      select importance,language||':'||title from wikipedia_article where osm_type = NEW.osm_type and osm_id = NEW.osm_id order by importance asc limit 1 INTO NEW.importance,NEW.wikipedia;
    END IF;

--RAISE WARNING '% %', NEW.place_id, NEW.rank_search;

    -- For low level elements we inherit from our parent road
    IF (NEW.rank_search > 27 OR (NEW.type = 'postcode' AND NEW.rank_search = 25)) THEN

--RAISE WARNING 'finding street for %', NEW;

      NEW.parent_place_id := null;

      -- to do that we have to find our parent road
      -- Copy data from linked items (points on ways, addr:street links, relations)
      -- Note that addr:street links can only be indexed once the street itself is indexed
      IF NEW.parent_place_id IS NULL AND NEW.osm_type = 'N' THEN

        -- Is this node part of a relation?
        FOR relation IN select * from planet_osm_rels where parts @> ARRAY[NEW.osm_id] and members @> ARRAY['n'||NEW.osm_id]
        LOOP
          -- At the moment we only process one type of relation - associatedStreet
          IF relation.tags @> ARRAY['associatedStreet'] AND array_upper(relation.members, 1) IS NOT NULL THEN
            FOR i IN 1..array_upper(relation.members, 1) BY 2 LOOP
              IF NEW.parent_place_id IS NULL AND relation.members[i+1] = 'street' THEN
--RAISE WARNING 'node in relation %',relation;
                SELECT place_id from placex where osm_type='W' and osm_id = substring(relation.members[i],2,200)::integer 
                  and rank_search = 26 INTO NEW.parent_place_id;
              END IF;
            END LOOP;
          END IF;
        END LOOP;      

--RAISE WARNING 'x1';
        -- Is this node part of a way?
        FOR way IN select id from planet_osm_ways where nodes @> ARRAY[NEW.osm_id] LOOP
--RAISE WARNING '%', way;
        FOR location IN select * from placex where osm_type = 'W' and osm_id = way.id
        LOOP
--RAISE WARNING '%', location;
          -- Way IS a road then we are on it - that must be our road
          IF location.rank_search = 26 AND NEW.parent_place_id IS NULL THEN
--RAISE WARNING 'node in way that is a street %',location;
            NEW.parent_place_id := location.place_id;
          END IF;

          -- Is the WAY part of a relation
          IF NEW.parent_place_id IS NULL THEN
              FOR relation IN select * from planet_osm_rels where parts @> ARRAY[location.osm_id] and members @> ARRAY['w'||location.osm_id]
              LOOP
                -- At the moment we only process one type of relation - associatedStreet
                IF relation.tags @> ARRAY['associatedStreet'] AND array_upper(relation.members, 1) IS NOT NULL THEN
                  FOR i IN 1..array_upper(relation.members, 1) BY 2 LOOP
                    IF NEW.parent_place_id IS NULL AND relation.members[i+1] = 'street' THEN
    --RAISE WARNING 'node in way that is in a relation %',relation;
                      SELECT place_id from placex where osm_type='W' and osm_id = substring(relation.members[i],2,200)::integer 
                        and rank_search = 26 INTO NEW.parent_place_id;
                    END IF;
                  END LOOP;
                END IF;
              END LOOP;
          END IF;    
          
          -- If the way contains an explicit name of a street copy it
          IF NEW.street IS NULL AND location.street IS NOT NULL THEN
--RAISE WARNING 'node in way that has a streetname %',location;
            NEW.street := location.street;
          END IF;

          -- If this way is a street interpolation line then it is probably as good as we are going to get
          IF NEW.parent_place_id IS NULL AND NEW.street IS NULL AND location.class = 'place' and location.type='houses' THEN
            -- Try and find a way that is close roughly parellel to this line
            FOR relation IN SELECT place_id FROM placex
              WHERE ST_DWithin(location.geometry, placex.geometry, 0.001) and placex.rank_search = 26
                and st_geometrytype(location.geometry) in ('ST_LineString')
              ORDER BY (ST_distance(placex.geometry, ST_Line_Interpolate_Point(location.geometry,0))+
                        ST_distance(placex.geometry, ST_Line_Interpolate_Point(location.geometry,0.5))+
                        ST_distance(placex.geometry, ST_Line_Interpolate_Point(location.geometry,1))) ASC limit 1
            LOOP
--RAISE WARNING 'using nearest street to address interpolation line,0.001 %',relation;
              NEW.parent_place_id := relation.place_id;
            END LOOP;
          END IF;

        END LOOP;
        END LOOP;
                
      END IF;

--RAISE WARNING 'x2';

      IF NEW.parent_place_id IS NULL AND NEW.osm_type = 'W' THEN
        -- Is this way part of a relation?
        FOR relation IN select * from planet_osm_rels where parts @> ARRAY[NEW.osm_id] and members @> ARRAY['w'||NEW.osm_id]
        LOOP
          -- At the moment we only process one type of relation - associatedStreet
          IF relation.tags @> ARRAY['associatedStreet'] AND array_upper(relation.members, 1) IS NOT NULL THEN
            FOR i IN 1..array_upper(relation.members, 1) BY 2 LOOP
              IF NEW.parent_place_id IS NULL AND relation.members[i+1] = 'street' THEN
--RAISE WARNING 'way that is in a relation %',relation;
                SELECT place_id from placex where osm_type='W' and osm_id = substring(relation.members[i],2,200)::integer
                  and rank_search = 26 INTO NEW.parent_place_id;
              END IF;
            END LOOP;
          END IF;
        END LOOP;
      END IF;
      
--RAISE WARNING 'x3 %',NEW.parent_place_id;

      IF NEW.parent_place_id IS NULL AND NEW.street IS NOT NULL THEN
      	address_street_word_id := get_name_id(make_standard_name(NEW.street));
        IF address_street_word_id IS NOT NULL THEN
          FOR location IN SELECT * from getNearestNamedRoadFeature(NEW.partition, place_centroid, address_street_word_id) LOOP
            NEW.parent_place_id := location.place_id;
          END LOOP;
        END IF;
      END IF;

--RAISE WARNING 'x4 %',NEW.parent_place_id;
      -- Still nothing, just use the nearest road
      IF NEW.parent_place_id IS NULL THEN
        FOR location IN SELECT place_id FROM getNearestRoadFeature(NEW.partition, place_centroid) LOOP
          NEW.parent_place_id := location.place_id;
        END LOOP;
      END IF;

--return NEW;
--RAISE WARNING 'x6 %',NEW.parent_place_id;

      -- If we didn't find any road fallback to standard method
      IF NEW.parent_place_id IS NOT NULL THEN

        -- Add the street to the address as zero distance to force to front of list
--        INSERT INTO place_addressline VALUES (NEW.place_id, NEW.parent_place_id, true, true, 0, 26);
        address_havelevel[26] := true;

        -- Import address details from parent, reclculating distance in process
--        INSERT INTO place_addressline select NEW.place_id, x.address_place_id, x.fromarea, x.isaddress, ST_distance(NEW.geometry, placex.geometry), placex.rank_address
--          from place_addressline as x join placex on (address_place_id = placex.place_id)
--          where x.place_id = NEW.parent_place_id and x.address_place_id != NEW.parent_place_id;

        -- Get the details of the parent road
        select * from search_name where place_id = NEW.parent_place_id INTO location;
        NEW.country_code := location.country_code;

--RAISE WARNING '%', NEW.name;
        -- If there is no name it isn't searchable, don't bother to create a search record
        IF NEW.name is NULL THEN
          return NEW;
        END IF;

        -- Merge address from parent
        nameaddress_vector := array_merge(nameaddress_vector, location.nameaddress_vector);
--return NEW;
        -- Performance, it would be more acurate to do all the rest of the import process but it takes too long
        -- Just be happy with inheriting from parent road only

        IF NEW.rank_search <= 25 THEN
          result := add_location(NEW.place_id, NEW.country_code, NEW.partition, name_vector, NEW.rank_search, NEW.rank_address, NEW.geometry);
        END IF;

        result := insertSearchName(NEW.partition, NEW.place_id, NEW.country_code, name_vector, nameaddress_vector, NEW.rank_search, NEW.rank_address, NEW.importance, place_centroid);

        return NEW;
      END IF;

    END IF;

-- RAISE WARNING '  INDEXING: %',NEW;

    IF NEW.osm_type = 'R' AND NEW.rank_search < 26 THEN

      -- see if we have any special relation members
      select members from planet_osm_rels where id = NEW.osm_id INTO relation_members;

      FOR relMember IN select get_osm_rel_members(relation_members,ARRAY['label']) as member LOOP

        select * from placex where osm_type = upper(substring(relMember.member,1,1)) 
          and osm_id = substring(relMember.member,2,10000)::integer order by rank_search desc limit 1 into linkedPlacex;

        -- If we don't already have one use this as the centre point of the geometry
        IF NEW.centroid IS NULL THEN
          NEW.centroid := coalesce(linkedPlacex.centroid,st_centroid(linkedPlacex.geometry));
        END IF;

        -- merge in the label name, re-init word vector
        NEW.name := linkedPlacex.name || NEW.name;
        name_vector := make_keywords(NEW.name);

        -- merge in extra tags
        NEW.extratags := linkedPlacex.extratags || NEW.extratags;

        -- mark the linked place (excludes from search results)
        UPDATE placex set linked_place_id = NEW.place_id where place_id = linkedPlacex.place_id;

      END LOOP;

      IF NEW.centroid IS NULL THEN

        FOR relMember IN select get_osm_rel_members(relation_members,ARRAY['admin_center','admin_centre']) as member LOOP

          select * from placex where osm_type = upper(substring(relMember.member,1,1)) 
            and osm_id = substring(relMember.member,2,10000)::integer order by rank_search desc limit 1 into linkedPlacex;

          -- For an admin centre we also want a name match - still not perfect, for example 'new york, new york'
          -- But that can be fixed by explicitly setting the label in the data
          IF make_standard_name(NEW.name->'name') = make_standard_name(linkedPlacex.name->'name') 
            AND NEW.rank_search = linkedPlacex.rank_search THEN

            -- If we don't already have one use this as the centre point of the geometry
            IF NEW.centroid IS NULL THEN
              NEW.centroid := coalesce(linkedPlacex.centroid,st_centroid(linkedPlacex.geometry));
            END IF;

            -- merge in the name, re-init word vector
            NEW.name := linkedPlacex.name || NEW.name;
            name_vector := make_keywords(NEW.name);

            -- merge in extra tags
            NEW.extratags := linkedPlacex.extratags || NEW.extratags;

            -- mark the linked place (excludes from search results)
            UPDATE placex set linked_place_id = NEW.place_id where place_id = linkedPlacex.place_id;
          END IF;

        END LOOP;

      END IF;

      -- not found one yet? how about doing a name search
      IF NEW.centroid IS NULL AND (NEW.name->'name') is not null and make_standard_name(NEW.name->'name') != '' THEN

        FOR linkedPlacex IN select placex.* from placex WHERE
          make_standard_name(name->'name') = make_standard_name(NEW.name->'name')
          AND placex.rank_search = NEW.rank_search
          AND placex.place_id != NEW.place_id
          AND osm_type = 'N'
          AND st_contains(NEW.geometry, placex.geometry)
        LOOP

          -- If we don't already have one use this as the centre point of the geometry
          IF NEW.centroid IS NULL THEN
            NEW.centroid := coalesce(linkedPlacex.centroid,st_centroid(linkedPlacex.geometry));
          END IF;

          -- merge in the name, re-init word vector
          NEW.name := linkedPlacex.name || NEW.name;
          name_vector := make_keywords(NEW.name);

          -- merge in extra tags
          NEW.extratags := linkedPlacex.extratags || NEW.extratags;

          -- mark the linked place (excludes from search results)
          UPDATE placex set linked_place_id = NEW.place_id where place_id = linkedPlacex.place_id;

        END LOOP;
      END IF;

      IF NEW.centroid IS NOT NULL THEN
        place_centroid := NEW.centroid;
      END IF;

      -- Did we gain a wikipedia tag in the process? then we need to recalculate our importance
      -- WARNING: duplicate of code above (yuk!)
      IF NEW.importance is null AND NEW.extratags?'wikipedia' THEN
        wiki_article := replace(regexp_replace(NEW.extratags->'wikipedia',E'(.*?)([a-z]+).wikipedia.org/wiki/',E'\\2:'),' ','_');
        wiki_article_title := split_part(wiki_article, ':', 2);
        IF wiki_article_title IS NULL OR wiki_article_title = '' THEN
          wiki_article_title := wiki_article;
          wiki_article_language := 'en';
        ELSE
          wiki_article_language := lower(split_part(wiki_article, ':', 1));
        END IF;

        select wikipedia_article.importance,wikipedia_article.language||':'||wikipedia_article.title 
          from wikipedia_article 
          where language = wiki_article_language and 
          (title = wiki_article_title OR title = decode_url_part(wiki_article_title) OR title = replace(decode_url_part(wiki_article_title),E'\\',''))
        UNION ALL
        select wikipedia_article.importance,wikipedia_article.language||':'||wikipedia_article.title 
          from wikipedia_redirect join wikipedia_article on (wikipedia_redirect.language = wikipedia_article.language and wikipedia_redirect.to_title = wikipedia_article.title)
          where wikipedia_redirect.language = wiki_article_language and 
          (from_title = wiki_article_title OR from_title = decode_url_part(wiki_article_title) OR from_title = replace(decode_url_part(wiki_article_title),E'\\',''))
        order by importance asc limit 1 INTO NEW.importance,NEW.wikipedia;

      END IF;

    END IF;

    NEW.parent_place_id = 0;
    parent_place_id_rank = 0;

    -- convert isin to array of tokenids
    isin_tokens := '{}'::int[];
    IF NEW.isin IS NOT NULL THEN
      isin := regexp_split_to_array(NEW.isin, E'[;,]');
      IF array_upper(isin, 1) IS NOT NULL THEN
        FOR i IN 1..array_upper(isin, 1) LOOP
          address_street_word_id := get_name_id(make_standard_name(isin[i]));
          IF address_street_word_id IS NOT NULL AND NOT(ARRAY[address_street_word_id] <@ isin_tokens) THEN
            isin_tokens := isin_tokens || address_street_word_id;
          END IF;
        END LOOP;
      END IF;
    END IF;
    IF NEW.postcode IS NOT NULL THEN
      isin := regexp_split_to_array(NEW.postcode, E'[;,]');
      IF array_upper(isin, 1) IS NOT NULL THEN
        FOR i IN 1..array_upper(isin, 1) LOOP
          address_street_word_id := get_name_id(make_standard_name(isin[i]));
          IF address_street_word_id IS NOT NULL AND NOT(ARRAY[address_street_word_id] <@ isin_tokens) THEN
            isin_tokens := isin_tokens || address_street_word_id;
          END IF;
        END LOOP;
      END IF;
    END IF;
--RAISE WARNING 'ISIN: %', isin_tokens;

    -- Process area matches
    location_rank_search := 100;
    location_distance := 0;
--RAISE WARNING '  getNearFeatures(%,''%'',%,''%'')',NEW.partition, place_centroid, search_maxrank, isin_tokens;
    FOR location IN SELECT * from getNearFeatures(NEW.partition, place_centroid, search_maxrank, isin_tokens) LOOP

--RAISE WARNING '  AREA: %',location;

      IF location.rank_search < location_rank_search THEN
        location_rank_search := location.rank_search;
        location_distance := location.distance * 1.5;
      END IF;

      IF location.distance < location_distance OR NOT location.isguess THEN

        -- Add it to the list of search terms
        nameaddress_vector := array_merge(nameaddress_vector, location.keywords::integer[]);
        INSERT INTO place_addressline VALUES (NEW.place_id, location.place_id, true, NOT address_havelevel[location.rank_address], location.distance, location.rank_address); 
        address_havelevel[location.rank_address] := true;

--RAISE WARNING '  Terms: (%) %',location, nameaddress_vector;

        IF location.rank_address > parent_place_id_rank THEN
          NEW.parent_place_id = location.place_id;
          parent_place_id_rank = location.rank_address;
        END IF;

      END IF;

    END LOOP;

    -- try using the isin value to find parent places
    IF array_upper(isin_tokens, 1) IS NOT NULL THEN
      FOR i IN 1..array_upper(isin_tokens, 1) LOOP
--RAISE WARNING '  getNearestNamedFeature: % % % %',NEW.partition, place_centroid, search_maxrank, isin_tokens[i];

        FOR location IN SELECT * from getNearestNamedFeature(NEW.partition, place_centroid, search_maxrank, isin_tokens[i]) LOOP

--RAISE WARNING '  ISIN: %',location;

          nameaddress_vector := array_merge(nameaddress_vector, location.keywords::integer[]);
          INSERT INTO place_addressline VALUES (NEW.place_id, location.place_id, false, NOT address_havelevel[location.rank_address], location.distance, location.rank_address);
          address_havelevel[location.rank_address] := true;

          IF location.rank_address > parent_place_id_rank THEN
            NEW.parent_place_id = location.place_id;
            parent_place_id_rank = location.rank_address;
          END IF;

        END LOOP;

      END LOOP;
    END IF;

    -- for long ways we should add search terms for the entire length
    IF st_length(NEW.geometry) > 0.05 THEN

      location_rank_search := 100;
      location_distance := 0;

      FOR location IN SELECT * from getNearFeatures(NEW.partition, NEW.geometry, search_maxrank, isin_tokens) LOOP

        IF location.rank_search < location_rank_search THEN
          location_rank_search := location.rank_search;
          location_distance := location.distance * 1.5;
        END IF;

        IF location.distance < location_distance THEN

          -- Add it to the list of search terms
          nameaddress_vector := array_merge(nameaddress_vector, location.keywords::integer[]);
          INSERT INTO place_addressline VALUES (NEW.place_id, location.place_id, true, false, location.distance, location.rank_address); 

        END IF;

      END LOOP;

    END IF;

    -- if we have a name add this to the name search table
    IF NEW.name IS NOT NULL THEN

      IF NEW.rank_search <= 25 THEN
        result := add_location(NEW.place_id, NEW.country_code, NEW.partition, name_vector, NEW.rank_search, NEW.rank_address, NEW.geometry);
      END IF;

      IF NEW.rank_search between 26 and 27 and NEW.class = 'highway' THEN
        result := insertLocationRoad(NEW.partition, NEW.place_id, NEW.country_code, NEW.geometry);
      END IF;

      result := insertSearchName(NEW.partition, NEW.place_id, NEW.country_code, name_vector, nameaddress_vector, NEW.rank_search, NEW.rank_address, NEW.importance, place_centroid);

--      INSERT INTO search_name values (NEW.place_id, NEW.rank_search, NEW.rank_search, 0, NEW.country_code, name_vector, nameaddress_vector, place_centroid);
    END IF;

    -- If we've not managed to pick up a better one - default centroid
    IF NEW.centroid IS NULL THEN
      NEW.centroid := place_centroid;
    END IF;

  END IF;

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

  update placex set linked_place_id = null where linked_place_id = OLD.place_id;
  update placex set indexed_status = 2 where linked_place_id = OLD.place_id and indexed_status = 0;

  IF OLD.rank_address < 30 THEN

    -- mark everything linked to this place for re-indexing
    UPDATE placex set indexed_status = 2 from place_addressline where address_place_id = OLD.place_id 
      and placex.place_id = place_addressline.place_id and indexed_status = 0;

    DELETE FROM place_addressline where address_place_id = OLD.place_id;

    b := deleteRoad(OLD.partition, OLD.place_id);

    update placex set indexed_status = 2 where parent_place_id = OLD.place_id and indexed_status = 0;

  END IF;

  IF OLD.rank_address < 26 THEN
    b := deleteLocationArea(OLD.partition, OLD.place_id);
  END IF;

  IF OLD.name is not null THEN
    b := deleteSearchName(OLD.partition, OLD.place_id);
  END IF;

  DELETE FROM place_addressline where place_id = OLD.place_id;

  -- remove from tables for special search
  classtable := 'place_classtype_' || OLD.class || '_' || OLD.type;
  SELECT count(*)>0 FROM pg_tables WHERE tablename = classtable INTO b;
  IF b THEN
    EXECUTE 'DELETE FROM ' || classtable::regclass || ' WHERE place_id = $1' USING OLD.place_id;
  END IF;

  RETURN OLD;

END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION place_delete() RETURNS TRIGGER
  AS $$
DECLARE
  placeid BIGINT;
BEGIN

--  RAISE WARNING 'delete: % % % %',OLD.osm_type,OLD.osm_id,OLD.class,OLD.type;

  -- deleting large polygons can have a massive effect ont he system - require manual intervention to let them through
  IF st_area(OLD.geometry) > 2 THEN
    insert into import_polygon_delete values (OLD.osm_type,OLD.osm_id,OLD.class,OLD.type);
    RETURN NULL;
  END IF;

  -- mark for delete
  UPDATE placex set indexed_status = 100 where osm_type = OLD.osm_type and osm_id = OLD.osm_id and class = OLD.class and type = OLD.type;

--  delete from placex where osm_type = OLD.osm_type and osm_id = OLD.osm_id and class = OLD.class and type = OLD.type;
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
  existinggeometry GEOMETRY;
  existingplace_id BIGINT;
  result BOOLEAN;
  partition INTEGER;
BEGIN

  IF FALSE and NEW.osm_type = 'R' THEN
    RAISE WARNING '-----------------------------------------------------------------------------------';
    RAISE WARNING 'place_insert: % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,st_area(NEW.geometry);
    select * from placex where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type INTO existingplacex;
    RAISE WARNING '%', existingplacex;
  END IF;

  -- Just block these - lots and pointless
  IF NEW.class = 'highway' and NEW.type in ('turning_circle','traffic_signals','mini_roundabout','noexit','crossing') THEN
    RETURN null;
  END IF;
  IF NEW.class in ('landuse','natural') and NEW.name is null THEN
    RETURN null;
  END IF;

  IF ST_IsEmpty(NEW.geometry) OR NOT ST_IsValid(NEW.geometry) OR ST_X(ST_Centroid(NEW.geometry))::text in ('NaN','Infinity','-Infinity') OR ST_Y(ST_Centroid(NEW.geometry))::text in ('NaN','Infinity','-Infinity') THEN  
    INSERT INTO import_polygon_error values (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name, NEW.country_code, 
      now(), ST_IsValidReason(NEW.geometry), null, NEW.geometry);
--    RAISE WARNING 'Invalid Geometry: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;
    RETURN null;
  END IF;

  -- Patch in additional country names
  IF NEW.admin_level = 2 AND NEW.type = 'administrative' AND NEW.country_code is not null THEN
    select country_name.name || NEW.name from country_name where country_name.country_code = lower(NEW.country_code) INTO NEW.name;
  END IF;
    
  -- Have we already done this place?
  select * from place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type INTO existing;

  -- Get the existing place_id
  select * from placex where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type INTO existingplacex;

  -- Handle a place changing type by removing the old data
  -- My generated 'place' types are causing havok because they overlap with real keys
  -- TODO: move them to their own special purpose key/class to avoid collisions
  IF existing.osm_type IS NULL AND (NEW.type not in ('postcode','house','houses')) THEN
    DELETE FROM place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type not in ('postcode','house','houses');
  END IF;

--  RAISE WARNING 'Existing: %',existing.place_id;

  -- Log and discard 
  IF existing.geometry is not null AND st_isvalid(existing.geometry) 
    AND st_area(existing.geometry) > 0.02
    AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon')
    AND st_area(NEW.geometry) < st_area(existing.geometry)*0.5
    THEN
    INSERT INTO import_polygon_error values (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name, NEW.country_code, now(), 
      'Area reduced from '||st_area(existing.geometry)||' to '||st_area(NEW.geometry), existing.geometry, NEW.geometry);
    RETURN null;
  END IF;

  DELETE from import_polygon_error where osm_type = NEW.osm_type and osm_id = NEW.osm_id;
  DELETE from import_polygon_delete where osm_type = NEW.osm_type and osm_id = NEW.osm_id;

  -- To paraphrase, if there isn't an existing item, OR if the admin level has changed, OR if it is a major change in geometry
  IF existing.osm_type IS NULL 
     OR existingplacex.osm_type IS NULL
     OR coalesce(existing.admin_level, 100) != coalesce(NEW.admin_level, 100) 
     OR coalesce(existing.country_code, '') != coalesce(NEW.country_code, '')
     OR (existing.geometry::text != NEW.geometry::text AND ST_Distance(ST_Centroid(existing.geometry),ST_Centroid(NEW.geometry)) > 0.01 AND NOT
     (ST_GeometryType(existing.geometry) in ('ST_Polygon','ST_MultiPolygon') AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon')))
     THEN

--  IF existing.osm_type IS NULL THEN
--    RAISE WARNING 'no existing place';
--  END IF;
--  IF existingplacex.osm_type IS NULL THEN
--    RAISE WARNING 'no existing placex %', existingplacex;
--  END IF;

--    RAISE WARNING 'delete and replace';

    IF existing.osm_type IS NOT NULL THEN
--      RAISE WARNING 'insert delete % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,ST_Distance(ST_Centroid(existing.geometry),ST_Centroid(NEW.geometry)),existing;
      DELETE FROM place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type;
    END IF;   

--    RAISE WARNING 'delete and replace2';

    -- No - process it as a new insertion (hopefully of low rank or it will be slow)
    insert into placex (osm_type, osm_id, class, type, name, admin_level, housenumber, 
      street, isin, postcode, country_code, extratags, geometry)
      values (NEW.osm_type
        ,NEW.osm_id
        ,NEW.class
        ,NEW.type
        ,NEW.name
        ,NEW.admin_level
        ,NEW.housenumber
        ,NEW.street
        ,NEW.isin
        ,NEW.postcode
        ,NEW.country_code
        ,NEW.extratags
        ,NEW.geometry
        );

--    RAISE WARNING 'insert done % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;

    RETURN NEW;
  END IF;

  -- Various ways to do the update

  -- Debug, what's changed?
  IF FALSE THEN
    IF coalesce(existing.name::text, '') != coalesce(NEW.name::text, '') THEN
      RAISE WARNING 'update details, name: % % % %',NEW.osm_type,NEW.osm_id,existing.name::text,NEW.name::text;
    END IF;
    IF coalesce(existing.housenumber, '') != coalesce(NEW.housenumber, '') THEN
      RAISE WARNING 'update details, housenumber: % % % %',NEW.osm_type,NEW.osm_id,existing.housenumber,NEW.housenumber;
    END IF;
    IF coalesce(existing.street, '') != coalesce(NEW.street, '') THEN
      RAISE WARNING 'update details, street: % % % %',NEW.osm_type,NEW.osm_id,existing.street,NEW.street;
    END IF;
    IF coalesce(existing.isin, '') != coalesce(NEW.isin, '') THEN
      RAISE WARNING 'update details, isin: % % % %',NEW.osm_type,NEW.osm_id,existing.isin,NEW.isin;
    END IF;
    IF coalesce(existing.postcode, '') != coalesce(NEW.postcode, '') THEN
      RAISE WARNING 'update details, postcode: % % % %',NEW.osm_type,NEW.osm_id,existing.postcode,NEW.postcode;
    END IF;
    IF coalesce(existing.country_code, '') != coalesce(NEW.country_code, '') THEN
      RAISE WARNING 'update details, country_code: % % % %',NEW.osm_type,NEW.osm_id,existing.country_code,NEW.country_code;
    END IF;
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
          (ST_Contains(NEW.geometry, placex.geometry) OR ST_Intersects(NEW.geometry, placex.geometry))
          AND NOT (ST_Contains(existinggeometry, placex.geometry) OR ST_Intersects(existinggeometry, placex.geometry))
          AND rank_search > existingplacex.rank_search AND (rank_search < 28 or name is not null);

      update placex set indexed_status = 2 where indexed_status = 0 and 
          (ST_Contains(existinggeometry, placex.geometry) OR ST_Intersects(existinggeometry, placex.geometry))
          AND NOT (ST_Contains(NEW.geometry, placex.geometry) OR ST_Intersects(NEW.geometry, placex.geometry))
          AND rank_search > existingplacex.rank_search AND (rank_search < 28 or name is not null);

    END IF;

  END IF;

  -- Special case - if we are just adding extra words we hack them into the search_name table rather than reindexing
  IF FALSE AND existingplacex.rank_search < 26
     AND coalesce(existing.housenumber, '') = coalesce(NEW.housenumber, '')
     AND coalesce(existing.street, '') = coalesce(NEW.street, '')
     AND coalesce(existing.isin, '') = coalesce(NEW.isin, '')
     AND coalesce(existing.postcode, '') = coalesce(NEW.postcode, '')
     AND coalesce(existing.country_code, '') = coalesce(NEW.country_code, '')
     AND coalesce(existing.name::text, '') != coalesce(NEW.name::text, '') 
     THEN

    IF NOT update_location_nameonly(existingplacex.place_id, NEW.name) THEN

      IF st_area(NEW.geometry) < 0.5 THEN
        UPDATE placex set indexed_status = 2 from place_addressline where address_place_id = existingplacex.place_id 
          and placex.place_id = place_addressline.place_id and indexed_status = 0
          and (rank_search < 28 or name is not null);
      END IF;

    END IF;
  
  ELSE

    -- Anything else has changed - reindex the lot
    IF coalesce(existing.name::text, '') != coalesce(NEW.name::text, '')
        OR coalesce(existing.housenumber, '') != coalesce(NEW.housenumber, '')
        OR coalesce(existing.street, '') != coalesce(NEW.street, '')
        OR coalesce(existing.isin, '') != coalesce(NEW.isin, '')
        OR coalesce(existing.postcode, '') != coalesce(NEW.postcode, '')
        OR coalesce(existing.country_code, '') != coalesce(NEW.country_code, '') THEN

      -- performance, can't take the load of re-indexing a whole country / huge area
      IF st_area(NEW.geometry) < 0.5 THEN
--        UPDATE placex set indexed_status = 2 from place_addressline where address_place_id = existingplacex.place_id 
--          and placex.place_id = place_addressline.place_id and indexed_status = 0;
      END IF;

    END IF;

  END IF;

  IF coalesce(existing.name::text, '') != coalesce(NEW.name::text, '')
     OR coalesce(existing.extratags::text, '') != coalesce(NEW.extratags::text, '')
     OR coalesce(existing.housenumber, '') != coalesce(NEW.housenumber, '')
     OR coalesce(existing.street, '') != coalesce(NEW.street, '')
     OR coalesce(existing.isin, '') != coalesce(NEW.isin, '')
     OR coalesce(existing.postcode, '') != coalesce(NEW.postcode, '')
     OR coalesce(existing.country_code, '') != coalesce(NEW.country_code, '')
     OR existing.geometry::text != NEW.geometry::text
     THEN

    update place set 
      name = NEW.name,
      housenumber  = NEW.housenumber,
      street = NEW.street,
      isin = NEW.isin,
      postcode = NEW.postcode,
      country_code = NEW.country_code,
      extratags = NEW.extratags,
      geometry = NEW.geometry
      where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class and type = NEW.type;

    update placex set 
      name = NEW.name,
      housenumber = NEW.housenumber,
      street = NEW.street,
      isin = NEW.isin,
      postcode = NEW.postcode,
      country_code = NEW.country_code,
      parent_place_id = null,
      extratags = NEW.extratags,
      indexed_status = 2,    
      geometry = NEW.geometry
      where place_id = existingplacex.place_id;

-- now done as part of insert
--    partition := get_partition(NEW.geometry, existingplacex.country_code);
--    result := update_location(partition, existingplacex.place_id, existingplacex.country_code, NEW.name, existingplacex.rank_search, existingplacex.rank_address, NEW.geometry);

  END IF;

  -- Abort the add (we modified the existing place instead)
  RETURN NULL;

END; 
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_name_by_language(name hstore, languagepref TEXT[]) RETURNS TEXT
  AS $$
DECLARE
  search TEXT[];
  found BOOLEAN;
BEGIN

  IF name is null THEN
    RETURN null;
  END IF;

  search := languagepref;

  FOR j IN 1..array_upper(search, 1) LOOP
    IF name ? search[j] AND trim(name->search[j]) != '' THEN
      return trim(name->search[j]);
    END IF;
  END LOOP;

  RETURN null;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_connected_ways(way_ids INTEGER[]) RETURNS SETOF planet_osm_ways
  AS $$
DECLARE
  searchnodes INTEGER[];
  location RECORD;
  j INTEGER;
BEGIN

  searchnodes := '{}';
  FOR j IN 1..array_upper(way_ids, 1) LOOP
    FOR location IN 
      select nodes from planet_osm_ways where id = way_ids[j] LIMIT 1
    LOOP
      IF not (ARRAY[location.nodes] <@ searchnodes) THEN
        searchnodes := searchnodes || location.nodes;
      END IF;
    END LOOP;
  END LOOP;

  RETURN QUERY select * from planet_osm_ways where nodes && searchnodes and NOT ARRAY[id] <@ way_ids;
END;
$$
LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION get_address_postcode(for_place_id BIGINT) RETURNS TEXT
  AS $$
DECLARE
  result TEXT[];
  search TEXT[];
  for_postcode TEXT;
  found INTEGER;
  location RECORD;
BEGIN

  found := 1000;
  search := ARRAY['ref'];
  result := '{}';

  select postcode from placex where place_id = for_place_id limit 1 into for_postcode;

  FOR location IN 
    select rank_address,name,distance,length(name::text) as namelength 
      from place_addressline join placex on (address_place_id = placex.place_id) 
      where place_addressline.place_id = for_place_id and rank_address in (5,11)
      order by rank_address desc,rank_search desc,fromarea desc,distance asc,namelength desc
  LOOP
    IF array_upper(search, 1) IS NOT NULL AND array_upper(location.name, 1) IS NOT NULL THEN
      FOR j IN 1..array_upper(search, 1) LOOP
        FOR k IN 1..array_upper(location.name, 1) LOOP
          IF (found > location.rank_address AND location.name[k].key = search[j] AND location.name[k].value != '') AND NOT result @> ARRAY[trim(location.name[k].value)] AND (for_postcode IS NULL OR location.name[k].value ilike for_postcode||'%') THEN
            result[(100 - location.rank_address)] := trim(location.name[k].value);
            found := location.rank_address;
          END IF;
        END LOOP;
      END LOOP;
    END IF;
  END LOOP;

  RETURN array_to_string(result,', ');
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_address_by_language(for_place_id BIGINT, languagepref TEXT[]) RETURNS TEXT
  AS $$
DECLARE
  result TEXT[];
  currresult TEXT;
  prevresult TEXT;
  location RECORD;
BEGIN

  result := '{}';
  prevresult := '';

  FOR location IN select * from get_addressdata(for_place_id) where isaddress order by rank_address desc LOOP
    currresult := trim(get_name_by_language(location.name, languagepref));
    IF currresult != prevresult AND currresult IS NOT NULL THEN
      result[(100 - location.rank_address)] := trim(get_name_by_language(location.name, languagepref));
      prevresult := currresult;
    END IF;
  END LOOP;

  RETURN array_to_string(result,', ');
END;
$$
LANGUAGE plpgsql;

DROP TYPE addressline CASCADE;
create type addressline as (
  place_id BIGINT,
  osm_type CHAR(1),
  osm_id INTEGER,
  name HSTORE,
  class TEXT,
  type TEXT,
  admin_level INTEGER,
  fromarea BOOLEAN,  
  isaddress BOOLEAN,  
  rank_address INTEGER,
  distance FLOAT
);

CREATE OR REPLACE FUNCTION get_addressdata(in_place_id BIGINT) RETURNS setof addressline 
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

  select parent_place_id,'us', housenumber, 30, postcode, null, 'place', 'house' from location_property_tiger 
    WHERE place_id = in_place_id 
    INTO for_place_id,searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode, searchhousename, searchclass, searchtype;

  IF for_place_id IS NULL THEN
    select parent_place_id,'us', housenumber, 30, postcode, null, 'place', 'house' from location_property_aux
      WHERE place_id = in_place_id 
      INTO for_place_id,searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode, searchhousename, searchclass, searchtype;
  END IF;

  IF for_place_id IS NULL THEN
    select parent_place_id, country_code, housenumber, rank_address, postcode, name, class, type from placex 
      WHERE place_id = in_place_id and rank_address = 30 
      INTO for_place_id, searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode, searchhousename, searchclass, searchtype;
  END IF;

  IF for_place_id IS NULL THEN
    for_place_id := in_place_id;
    select country_code, housenumber, rank_address, postcode, null from placex where place_id = for_place_id 
      INTO searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode, searchhousename;
  END IF;

--RAISE WARNING '% % % %',searchcountrycode, searchhousenumber, searchrankaddress, searchpostcode;

  found := 1000;
  hadcountry := false;
  FOR location IN 
    select placex.place_id, osm_type, osm_id,
      CASE WHEN class = 'place' and type = 'postcode' THEN 'name' => postcode ELSE name END as name,
      class, type, admin_level, true as fromarea, true as isaddress,
      CASE WHEN rank_address = 0 THEN 100 WHEN rank_address = 11 THEN 5 ELSE rank_address END as rank_address,
      0 as distance, country_code
      from placex
      where place_id = for_place_id 
  LOOP
--RAISE WARNING '%',location;
    IF searchcountrycode IS NULL AND location.country_code IS NOT NULL THEN
      searchcountrycode := location.country_code;
    END IF;
    IF searchpostcode IS NOT NULL and location.type = 'postcode' THEN
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

  FOR location IN 
    select placex.place_id, osm_type, osm_id,
      CASE WHEN class = 'place' and type = 'postcode' THEN 'name' => postcode ELSE name END as name,
      class, type, admin_level, fromarea, isaddress,
      CASE WHEN address_place_id = for_place_id AND rank_address = 0 THEN 100 WHEN rank_address = 11 THEN 5 ELSE rank_address END as rank_address,
      distance,country_code
      from place_addressline join placex on (address_place_id = placex.place_id) 
      where place_addressline.place_id = for_place_id 
      and (cached_rank_address > 0 AND cached_rank_address < searchrankaddress)
      and address_place_id != for_place_id
      and (placex.country_code IS NULL OR searchcountrycode IS NULL OR placex.country_code = searchcountrycode OR rank_address < 4)
      order by rank_address desc,isaddress desc,fromarea desc,distance asc,rank_search desc
  LOOP
--RAISE WARNING '%',location;
    IF searchcountrycode IS NULL AND location.country_code IS NOT NULL THEN
      searchcountrycode := location.country_code;
    END IF;
    IF searchpostcode IS NOT NULL and location.type = 'postcode' THEN
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
    location := ROW(null, null, null, 'ref'=>searchcountrycode, 'place', 'country_code', null, true, false, 4, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchhousename IS NOT NULL THEN
    location := ROW(in_place_id, null, null, searchhousename, searchclass, searchtype, null, true, true, 29, 0)::addressline;
--    location := ROW(in_place_id, null, null, searchhousename, 'place', 'house_name', null, true, true, 29, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchhousenumber IS NOT NULL THEN
    location := ROW(in_place_id, null, null, 'ref'=>searchhousenumber, 'place', 'house_number', null, true, true, 28, 0)::addressline;
    RETURN NEXT location;
  END IF;

  IF searchpostcode IS NOT NULL THEN
    location := ROW(null, null, null, 'ref'=>searchpostcode, 'place', 'postcode', null, true, true, 5, 0)::addressline;
    RETURN NEXT location;
  END IF;

  RETURN;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_place_boundingbox(search_place_id BIGINT) RETURNS place_boundingbox
  AS $$
DECLARE
  result place_boundingbox;
  numfeatures integer;
BEGIN
  select * from place_boundingbox into result where place_id = search_place_id;
  IF result.place_id IS NULL THEN
-- remove  isaddress = true because if there is a matching polygon it always wins
    select count(*) from place_addressline where address_place_id = search_place_id into numfeatures;
    insert into place_boundingbox select place_id,
             ST_Y(ST_PointN(ExteriorRing(ST_Box2D(geometry)),4)),ST_Y(ST_PointN(ExteriorRing(ST_Box2D(geometry)),2)),
             ST_X(ST_PointN(ExteriorRing(ST_Box2D(geometry)),1)),ST_X(ST_PointN(ExteriorRing(ST_Box2D(geometry)),3)),
             numfeatures, ST_Area(geometry),
             geometry as area from location_area where place_id = search_place_id;
    select * from place_boundingbox into result where place_id = search_place_id;
  END IF;
  IF result.place_id IS NULL THEN
-- TODO 0.0001
    insert into place_boundingbox select address_place_id,
             min(ST_Y(ST_Centroid(geometry))) as minlon,max(ST_Y(ST_Centroid(geometry))) as maxlon,
             min(ST_X(ST_Centroid(geometry))) as minlat,max(ST_X(ST_Centroid(geometry))) as maxlat,
             count(*), ST_Area(ST_Buffer(ST_Convexhull(ST_Collect(geometry)),0.0001)) as area,
             ST_Buffer(ST_Convexhull(ST_Collect(geometry)),0.0001) as boundary 
             from (select * from place_addressline where address_place_id = search_place_id order by cached_rank_address limit 4000) as place_addressline join placex using (place_id) 
             where address_place_id = search_place_id
--               and (isaddress = true OR place_id = search_place_id)
               and (st_length(geometry) < 0.01 or place_id = search_place_id)
             group by address_place_id limit 1;
    select * from place_boundingbox into result where place_id = search_place_id;
  END IF;
  return result;
END;
$$
LANGUAGE plpgsql;

-- don't do the operation if it would be slow
CREATE OR REPLACE FUNCTION get_place_boundingbox_quick(search_place_id BIGINT) RETURNS place_boundingbox
  AS $$
DECLARE
  result place_boundingbox;
  numfeatures integer;
  rank integer;
BEGIN
  select * from place_boundingbox into result where place_id = search_place_id;
  IF result IS NULL AND rank > 14 THEN
    select count(*) from place_addressline where address_place_id = search_place_id and isaddress = true into numfeatures;
    insert into place_boundingbox select place_id,
             ST_Y(ST_PointN(ExteriorRing(ST_Box2D(geometry)),4)),ST_Y(ST_PointN(ExteriorRing(ST_Box2D(geometry)),2)),
             ST_X(ST_PointN(ExteriorRing(ST_Box2D(geometry)),1)),ST_X(ST_PointN(ExteriorRing(ST_Box2D(geometry)),3)),
             numfeatures, ST_Area(geometry),
             geometry as area from location_area where place_id = search_place_id;
    select * from place_boundingbox into result where place_id = search_place_id;
  END IF;
  IF result IS NULL THEN
    select rank_search from placex where place_id = search_place_id into rank;
    IF rank > 20 THEN
-- TODO 0.0001
      insert into place_boundingbox select address_place_id,
             min(ST_Y(ST_Centroid(geometry))) as minlon,max(ST_Y(ST_Centroid(geometry))) as maxlon,
             min(ST_X(ST_Centroid(geometry))) as minlat,max(ST_X(ST_Centroid(geometry))) as maxlat,
             count(*), ST_Area(ST_Buffer(ST_Convexhull(ST_Collect(geometry)),0.0001)) as area,
             ST_Buffer(ST_Convexhull(ST_Collect(geometry)),0.0001) as boundary 
             from place_addressline join placex using (place_id) 
             where address_place_id = search_place_id 
               and (isaddress = true OR place_id = search_place_id)
               and (st_length(geometry) < 0.01 or place_id = search_place_id)
             group by address_place_id limit 1;
      select * from place_boundingbox into result where place_id = search_place_id;
    END IF;
  END IF;
  return result;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_place(search_place_id BIGINT) RETURNS BOOLEAN
  AS $$
DECLARE
  result place_boundingbox;
  numfeatures integer;
BEGIN
  update placex set 
      name = place.name,
      housenumber = place.housenumber,
      street = place.street,
      isin = place.isin,
      postcode = place.postcode,
      country_code = place.country_code,
      parent_place_id = null
      from place
      where placex.place_id = search_place_id 
        and place.osm_type = placex.osm_type and place.osm_id = placex.osm_id
        and place.class = placex.class and place.type = placex.type;
  update placex set indexed_status = 2 where place_id = search_place_id;
  update placex set indexed_status = 0 where place_id = search_place_id;
  return true;
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

CREATE OR REPLACE FUNCTION get_word_suggestion(srcword TEXT) RETURNS TEXT
  AS $$
DECLARE
  trigramtoken TEXT;
  result TEXT;
BEGIN

  trigramtoken := regexp_replace(make_standard_name(srcword),E'([^0-9])\\1+',E'\\1','g');
  SELECT word FROM word WHERE word_trigram like ' %' and word_trigram % trigramtoken ORDER BY similarity(word_trigram, trigramtoken) DESC, word limit 1 into result;

  return result;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_word_suggestions(srcword TEXT) RETURNS TEXT[]
  AS $$
DECLARE
  trigramtoken TEXT;
  result TEXT[];
  r RECORD;
BEGIN

  trigramtoken := regexp_replace(make_standard_name(srcword),E'([^0-9])\\1+',E'\\1','g');

  FOR r IN SELECT word,similarity(word_trigram, trigramtoken) as score FROM word 
    WHERE word_trigram like ' %' and word_trigram % trigramtoken ORDER BY similarity(word_trigram, trigramtoken) DESC, word limit 4
  LOOP
    result[coalesce(array_upper(result,1)+1,1)] := r.word;
  END LOOP;

  return result;
END;
$$
LANGUAGE plpgsql;

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
  out_partition := get_partition(place_centroid, 'us');
  out_parent_place_id := null;

  address_street_word_id := get_name_id(make_standard_name(in_street));
  IF address_street_word_id IS NOT NULL THEN
    FOR location IN SELECT * from getNearestNamedRoadFeature(out_partition, place_centroid, address_street_word_id) LOOP
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
    insert into location_property_tiger (place_id, partition, parent_place_id, housenumber, postcode, centroid)
    values (nextval('seq_place'), out_partition, out_parent_place_id, housenum, in_postcode,
      ST_Line_Interpolate_Point(linegeo, (housenum::float-rangestartnumber::float)/numberrange::float));
    newpoints := newpoints + 1;
  END LOOP;

  RETURN newpoints;
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
  out_partition := get_partition(place_centroid, in_countrycode);
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
  IF out_postcode IS NULL THEN
    out_postcode := getNearestPostcode(out_partition, place_centroid);
  END IF;

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
SELECT convert_from(CAST(E'\\x' || string_agg(CASE WHEN length(r.m[1]) = 1 THEN encode(convert_to(r.m[1], 'SQL_ASCII'), 'hex') ELSE substring(r.m[1] from 2 for 2) END, '') AS bytea), 'UTF8')
FROM regexp_matches($1, '%[0-9a-f][0-9a-f]|.', 'gi') AS r(m);
$$ 
LANGUAGE SQL IMMUTABLE STRICT;
