-- Trigger functions for the placex table.

CREATE OR REPLACE FUNCTION get_rel_node_members(members TEXT[], memberLabels TEXT[])
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

-- copy 'name' to or from the default language (if there is a default language)
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

-- Find the parent road of a POI.
--
-- \returns Place ID of parent object or NULL if none
--
-- Copy data from linked items (POIs on ways, addr:street links, relations).
--
CREATE OR REPLACE FUNCTION find_parent_for_poi(poi_osm_type CHAR(1),
                                               poi_osm_id BIGINT,
                                               poi_partition SMALLINT,
                                               bbox GEOMETRY,
                                               addr_street TEXT,
                                               addr_place TEXT,
                                               fallback BOOL = true)
  RETURNS BIGINT
  AS $$
DECLARE
  parent_place_id BIGINT DEFAULT NULL;
  location RECORD;
  parent RECORD;
BEGIN
    --DEBUG: RAISE WARNING 'finding street for % %', poi_osm_type, poi_osm_id;

    -- Is this object part of an associatedStreet relation?
    FOR location IN
      SELECT members FROM planet_osm_rels
      WHERE parts @> ARRAY[poi_osm_id]
        and members @> ARRAY[lower(poi_osm_type) || poi_osm_id]
        and tags @> ARRAY['associatedStreet']
    LOOP
      FOR i IN 1..array_upper(location.members, 1) BY 2 LOOP
        IF location.members[i+1] = 'street' THEN
          --DEBUG: RAISE WARNING 'node in relation %',relation;
          FOR parent IN
            SELECT place_id from placex
             WHERE osm_type = 'W' and osm_id = substring(location.members[i],2)::bigint
               and name is not null
               and rank_search between 26 and 27
          LOOP
            RETURN parent.place_id;
          END LOOP;
        END IF;
      END LOOP;
    END LOOP;

    parent_place_id := find_parent_for_address(addr_street, addr_place,
                                               poi_partition, bbox);
    IF parent_place_id is not null THEN
      RETURN parent_place_id;
    END IF;

    IF poi_osm_type = 'N' THEN
      -- Is this node part of an interpolation?
      FOR parent IN
        SELECT q.parent_place_id
          FROM location_property_osmline q, planet_osm_ways x
         WHERE q.linegeo && bbox and x.id = q.osm_id
               and poi_osm_id = any(x.nodes)
         LIMIT 1
      LOOP
        --DEBUG: RAISE WARNING 'Get parent from interpolation: %', parent.parent_place_id;
        RETURN parent.parent_place_id;
      END LOOP;

      -- Is this node part of any other way?
      FOR location IN
        SELECT p.place_id, p.osm_id, p.rank_search, p.address,
               coalesce(p.centroid, ST_Centroid(p.geometry)) as centroid
          FROM placex p, planet_osm_ways w
         WHERE p.osm_type = 'W' and p.rank_search >= 26
               and p.geometry && bbox
               and w.id = p.osm_id and poi_osm_id = any(w.nodes)
      LOOP
        --DEBUG: RAISE WARNING 'Node is part of way % ', location.osm_id;

        -- Way IS a road then we are on it - that must be our road
        IF location.rank_search < 28 THEN
          --DEBUG: RAISE WARNING 'node in way that is a street %',location;
          return location.place_id;
        END IF;

        SELECT find_parent_for_poi('W', location.osm_id, poi_partition,
                                   location.centroid,
                                   location.address->'street',
                                   location.address->'place',
                                   false)
          INTO parent_place_id;
        IF parent_place_id is not null THEN
          RETURN parent_place_id;
        END IF;
      END LOOP;
    END IF;

    IF fallback THEN
      IF ST_Area(bbox) < 0.01 THEN
        -- for smaller features get the nearest road
        SELECT getNearestRoadPlaceId(poi_partition, bbox) INTO parent_place_id;
        --DEBUG: RAISE WARNING 'Checked for nearest way (%)', parent_place_id;
      ELSE
        -- for larger features simply find the area with the largest rank that
        -- contains the bbox
        FOR location IN
          SELECT place_id FROM placex
            WHERE bbox @ geometry AND _ST_Covers(geometry, ST_Centroid(bbox))
                  AND rank_search between 5 and 25
            ORDER BY rank_search desc
        LOOP
            RETURN location.place_id;
        END LOOP;
      END IF;
    END IF;

    RETURN parent_place_id;
END;
$$
LANGUAGE plpgsql STABLE;

-- Try to find a linked place for the given object.
CREATE OR REPLACE FUNCTION find_linked_place(bnd placex)
  RETURNS placex
  AS $$
DECLARE
  relation_members TEXT[];
  rel_member RECORD;
  linked_placex placex%ROWTYPE;
  bnd_name TEXT;
BEGIN
  IF bnd.rank_search >= 26 or bnd.rank_address = 0
     or ST_GeometryType(bnd.geometry) NOT IN ('ST_Polygon','ST_MultiPolygon')
  THEN
    RETURN NULL;
  END IF;

  IF bnd.osm_type = 'R' THEN
    -- see if we have any special relation members
    SELECT members FROM planet_osm_rels WHERE id = bnd.osm_id INTO relation_members;
    --DEBUG: RAISE WARNING 'Got relation members';

    -- Search for relation members with role 'lable'.
    IF relation_members IS NOT NULL THEN
      FOR rel_member IN
        SELECT get_rel_node_members(relation_members, ARRAY['label']) as member
      LOOP
        --DEBUG: RAISE WARNING 'Found label member %', rel_member.member;

        FOR linked_placex IN
          SELECT * from placex
          WHERE osm_type = 'N' and osm_id = rel_member.member
            and class = 'place'
        LOOP
          --DEBUG: RAISE WARNING 'Linked label member';
          RETURN linked_placex;
        END LOOP;

      END LOOP;
    END IF;
  END IF;

  IF bnd.name ? 'name' THEN
    bnd_name := make_standard_name(bnd.name->'name');
    IF bnd_name = '' THEN
      bnd_name := NULL;
    END IF;
  END IF;

  -- If extratags has a place tag, look for linked nodes by their place type.
  -- Area and node still have to have the same name.
  IF bnd.extratags ? 'place' and bnd_name is not null THEN
    FOR linked_placex IN
      SELECT * FROM placex
      WHERE make_standard_name(name->'name') = bnd_name
        AND placex.class = 'place' AND placex.type = bnd.extratags->'place'
        AND placex.osm_type = 'N'
        AND placex.rank_search < 26 -- needed to select the right index
        AND _st_covers(bnd.geometry, placex.geometry)
    LOOP
      --DEBUG: RAISE WARNING 'Found type-matching place node %', linked_placex.osm_id;
      RETURN linked_placex;
    END LOOP;
  END IF;

  -- Search for relation members with role admin_center.
  IF bnd.osm_type = 'R' and bnd_name is not null
     and relation_members is not null
  THEN
    FOR rel_member IN
      SELECT get_rel_node_members(relation_members,
                                ARRAY['admin_center','admin_centre']) as member
    LOOP
    --DEBUG: RAISE WARNING 'Found admin_center member %', rel_member.member;
      FOR linked_placex IN
        SELECT * from placex
        WHERE osm_type = 'N' and osm_id = rel_member.member
          and class = 'place'
      LOOP
        -- For an admin centre we also want a name match - still not perfect,
        -- for example 'new york, new york'
        -- But that can be fixed by explicitly setting the label in the data
        IF bnd_name = make_standard_name(linked_placex.name->'name')
           AND bnd.rank_address = linked_placex.rank_address
        THEN
          RETURN linked_placex;
        END IF;
          --DEBUG: RAISE WARNING 'Linked admin_center';
      END LOOP;
    END LOOP;
  END IF;

  -- Name searches can be done for ways as well as relations
  IF bnd_name is not null THEN
    --DEBUG: RAISE WARNING 'Looking for nodes with matching names';
    FOR linked_placex IN
      SELECT placex.* from placex
      WHERE make_standard_name(name->'name') = bnd_name
        AND ((bnd.rank_address > 0 and placex.rank_address = bnd.rank_address)
             OR (bnd.rank_address = 0 and placex.rank_search = bnd.rank_search))
        AND placex.osm_type = 'N'
        AND placex.rank_search < 26 -- needed to select the right index
        AND _st_covers(bnd.geometry, placex.geometry)
    LOOP
      --DEBUG: RAISE WARNING 'Found matching place node %', linked_placex.osm_id;
      RETURN linked_placex;
    END LOOP;
  END IF;

  RETURN NULL;
END;
$$
LANGUAGE plpgsql STABLE;


-- Insert address of a place into the place_addressline table.
--
-- \param obj_place_id  Place_id of the place to compute the address for.
-- \param partition     Partition number where the place is in.
-- \param maxrank       Rank of the place. All address features must have
--                      a search rank lower than the given rank.
-- \param address       Address terms for the place.
-- \param geoemtry      Geometry to which the address objects should be close.
--
-- \retval parent_place_id  Place_id of the address object that is the direct
--                          ancestor.
-- \retval postcode         Postcode computed from the address. This is the
--                          addr:postcode of one of the address objects. If
--                          more than one of has a postcode, the highest ranking
--                          one is used. May be NULL.
-- \retval nameaddress_vector  Search terms for the address. This is the sum
--                             of name terms of all address objects.
CREATE OR REPLACE FUNCTION insert_addresslines(obj_place_id BIGINT,
                                               partition SMALLINT,
                                               maxrank SMALLINT,
                                               address HSTORE,
                                               geometry GEOMETRY,
                                               OUT parent_place_id BIGINT,
                                               OUT postcode TEXT,
                                               OUT nameaddress_vector INT[])
  AS $$
DECLARE
  current_rank_address INTEGER := 0;
  location_distance FLOAT := 0;
  location_parent GEOMETRY := NULL;
  parent_place_id_rank SMALLINT := 0;

  location_isaddress BOOLEAN;

  address_havelevel BOOLEAN[];
  location_keywords INT[];

  location RECORD;
  addr_item RECORD;

  isin_tokens INT[];
  isin TEXT[];
BEGIN
  parent_place_id := 0;
  nameaddress_vector := '{}'::int[];
  isin_tokens := '{}'::int[];

  ---- convert address store to array of tokenids
  IF address IS NOT NULL THEN
    FOR addr_item IN SELECT * FROM each(address)
    LOOP
      IF addr_item.key IN ('city', 'tiger:county', 'state', 'suburb', 'province',
                           'district', 'region', 'county', 'municipality',
                           'hamlet', 'village', 'subdistrict', 'town',
                           'neighbourhood', 'quarter', 'parish')
      THEN
        isin_tokens := array_merge(isin_tokens,
                                   word_ids_from_name(addr_item.value));
        IF NOT %REVERSE-ONLY% THEN
          nameaddress_vector := array_merge(nameaddress_vector,
                                            addr_ids_from_name(addr_item.value));
        END IF;
      END IF;
    END LOOP;

    IF address ? 'is_in' THEN
      -- is_in items need splitting
      isin := regexp_split_to_array(address->'is_in', E'[;,]');
      IF array_upper(isin, 1) IS NOT NULL THEN
        FOR i IN 1..array_upper(isin, 1) LOOP
          isin_tokens := array_merge(isin_tokens,
                                     word_ids_from_name(isin[i]));

          -- merge word into address vector
          IF NOT %REVERSE-ONLY% THEN
            nameaddress_vector := array_merge(nameaddress_vector,
                                              addr_ids_from_name(isin[i]));
          END IF;
        END LOOP;
      END IF;
    END IF;
  END IF;
  IF NOT %REVERSE-ONLY% THEN
    nameaddress_vector := array_merge(nameaddress_vector, isin_tokens);
  END IF;

  ---- now compute the address terms
  FOR i IN 1..28 LOOP
    address_havelevel[i] := false;
  END LOOP;

  FOR location IN
    SELECT * FROM getNearFeatures(partition, geometry, maxrank, isin_tokens)
  LOOP
    IF location.rank_address != current_rank_address THEN
      current_rank_address := location.rank_address;
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
      --DEBUG: RAISE WARNING 'should be address: %, is guess: %, rank: %', location_isaddress, location.isguess, location.rank_address;
      IF location_isaddress AND location.isguess AND location_parent IS NOT NULL THEN
          location_isaddress := ST_Contains(location_parent, location.centroid);
      END IF;

      --DEBUG: RAISE WARNING '% isaddress: %', location.place_id, location_isaddress;
      -- Add it to the list of search terms
      IF NOT %REVERSE-ONLY% THEN
          nameaddress_vector := array_merge(nameaddress_vector,
                                            location.keywords::integer[]);
      END IF;

      INSERT INTO place_addressline (place_id, address_place_id, fromarea,
                                     isaddress, distance, cached_rank_address)
        VALUES (obj_place_id, location.place_id, true,
                location_isaddress, location.distance, location.rank_address);

      IF location_isaddress THEN
        -- add postcode if we have one
        -- (If multiple postcodes are available, we end up with the highest ranking one.)
        IF location.postcode is not null THEN
            postcode = location.postcode;
        END IF;

        address_havelevel[location.rank_address] := true;
        -- add a hack against postcode ranks
        IF NOT location.isguess
           AND location.rank_address != 11 AND location.rank_address != 5
        THEN
          SELECT p.geometry FROM placex p
            WHERE p.place_id = location.place_id INTO location_parent;
        END IF;

        IF location.rank_address > parent_place_id_rank THEN
          parent_place_id = location.place_id;
          parent_place_id_rank = location.rank_address;
        END IF;
      END IF;
    END IF;

  END LOOP;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION placex_insert()
  RETURNS TRIGGER
  AS $$
DECLARE
  postcode TEXT;
  result BOOLEAN;
  is_area BOOLEAN;
  country_code VARCHAR(2);
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
    IF NEW.class = 'waterway' AND NEW.osm_type = 'R' THEN
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

  --DEBUG: RAISE WARNING 'placex_insert:END: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;

  RETURN NEW; -- %DIFFUPDATES% The following is not needed until doing diff updates, and slows the main index process down

  IF NEW.osm_type = 'N' and NEW.rank_search > 28 THEN
      -- might be part of an interpolation
      result := osmline_reinsert(NEW.osm_id, NEW.geometry);
  ELSEIF NEW.rank_address > 0 THEN
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


CREATE OR REPLACE FUNCTION placex_update()
  RETURNS TRIGGER
  AS $$
DECLARE
  i INTEGER;
  location RECORD;
  relation_members TEXT[];

  centroid GEOMETRY;

  addr_street TEXT;
  addr_place TEXT;

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
  -- housenumber is a computed field, so start with an empty value
  NEW.housenumber := NULL;
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
  NEW.centroid := ST_PointOnSurface(NEW.geometry);
  --DEBUG: RAISE WARNING 'Computing preliminary centroid at %',ST_AsText(NEW.centroid);

  NEW.postcode := null;

  -- recalculate country and partition
  IF NEW.rank_search = 4 AND NEW.address is not NULL AND NEW.address ? 'country' THEN
    -- for countries, believe the mapped country code,
    -- so that we remain in the right partition if the boundaries
    -- suddenly expand.
    NEW.country_code := lower(NEW.address->'country');
    NEW.partition := get_partition(lower(NEW.country_code));
    IF NEW.partition = 0 THEN
      NEW.country_code := lower(get_country_code(NEW.centroid));
      NEW.partition := get_partition(NEW.country_code);
    END IF;
  ELSE
    IF NEW.rank_search >= 4 THEN
      NEW.country_code := lower(get_country_code(NEW.centroid));
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
                  DELETE FROM search_name WHERE place_id = linked_node_id;
                END LOOP;
              END IF;
          END LOOP;
      END LOOP;
      --DEBUG: RAISE WARNING 'Waterway processed';
  END IF;

  NEW.importance := null;
  SELECT wikipedia, importance
    FROM compute_importance(NEW.extratags, NEW.country_code, NEW.osm_type, NEW.osm_id)
    INTO NEW.wikipedia,NEW.importance;

--DEBUG: RAISE WARNING 'Importance computed from wikipedia: %', NEW.importance;

  -- ---------------------------------------------------------------------------
  -- For low level elements we inherit from our parent road
  IF (NEW.rank_search > 27 OR (NEW.type = 'postcode' AND NEW.rank_search = 25)) THEN

    --DEBUG: RAISE WARNING 'finding street for % %', NEW.osm_type, NEW.osm_id;
    NEW.parent_place_id := null;

    -- if we have a POI and there is no address information,
    -- see if we can get it from a surrounding building
    IF NEW.osm_type = 'N' AND addr_street IS NULL AND addr_place IS NULL
       AND NEW.housenumber IS NULL THEN
      FOR location IN
        -- The additional && condition works around the misguided query
        -- planner of postgis 3.0.
        SELECT address from placex where ST_Covers(geometry, NEW.centroid)
            and geometry && NEW.centroid
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
    NEW.parent_place_id := find_parent_for_poi(NEW.osm_type, NEW.osm_id,
                                               NEW.partition,
                                               ST_Envelope(NEW.geometry),
                                               addr_street, addr_place);

    -- If we found the road take a shortcut here.
    -- Otherwise fall back to the full address getting method below.
    IF NEW.parent_place_id is not null THEN

      -- Get the details of the parent road
      SELECT p.country_code, p.postcode FROM placex p
       WHERE p.place_id = NEW.parent_place_id INTO location;

      NEW.country_code := location.country_code;
      --DEBUG: RAISE WARNING 'Got parent details from search name';

      -- determine postcode
      IF NEW.address is not null AND NEW.address ? 'postcode' THEN
          NEW.postcode = upper(trim(NEW.address->'postcode'));
      ELSE
         NEW.postcode := location.postcode;
      END IF;
      IF NEW.postcode is null THEN
        NEW.postcode := get_nearest_postcode(NEW.country_code, NEW.geometry);
      END IF;

      -- If there is no name it isn't searchable, don't bother to create a search record
      IF NEW.name is NULL THEN
        --DEBUG: RAISE WARNING 'Not a searchable place % %', NEW.osm_type, NEW.osm_id;
        return NEW;
      END IF;

      NEW.name := add_default_place_name(NEW.country_code, NEW.name);
      name_vector := make_keywords(NEW.name);

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
          SELECT array_merge(s.name_vector, s.nameaddress_vector)
            INTO nameaddress_vector
            FROM search_name s
            WHERE s.place_id = NEW.parent_place_id;

          INSERT INTO search_name (place_id, search_rank, address_rank,
                                   importance, country_code, name_vector,
                                   nameaddress_vector, centroid)
                 VALUES (NEW.place_id, NEW.rank_search, NEW.rank_address,
                         NEW.importance, NEW.country_code, name_vector,
                         nameaddress_vector, NEW.centroid);
          --DEBUG: RAISE WARNING 'Place added to search table';
        END IF;

      return NEW;
    END IF;

  END IF;

  -- ---------------------------------------------------------------------------
  -- Full indexing
  --DEBUG: RAISE WARNING 'Using full index mode for % %', NEW.osm_type, NEW.osm_id;
  SELECT * INTO location FROM find_linked_place(NEW);
  IF location.place_id is not null THEN
    --DEBUG: RAISE WARNING 'Linked %', location;

    -- Use the linked point as the centre point of the geometry,
    -- but only if it is within the area of the boundary.
    centroid := coalesce(location.centroid, ST_Centroid(location.geometry));
    IF centroid is not NULL AND ST_Within(centroid, NEW.geometry) THEN
        NEW.centroid := centroid;
    END IF;

    -- Use the address rank of the linked place, if it has one
    IF location.rank_address between 5 and 25 THEN
      NEW.rank_address := location.rank_address;
    END IF;

    -- merge in the label name
    IF NOT location.name IS NULL THEN
      NEW.name := location.name || NEW.name;
    END IF;

    -- merge in extra tags
    NEW.extratags := hstore('linked_' || location.class, location.type)
                     || coalesce(location.extratags, ''::hstore)
                     || coalesce(NEW.extratags, ''::hstore);

    -- mark the linked place (excludes from search results)
    UPDATE placex set linked_place_id = NEW.place_id
      WHERE place_id = location.place_id;
    -- ensure that those places are not found anymore
    DELETE FROM search_name WHERE place_id = location.place_id;

    SELECT wikipedia, importance
      FROM compute_importance(location.extratags, NEW.country_code,
                              'N', location.osm_id)
      INTO linked_wikipedia,linked_importance;

    -- Use the maximum importance if one could be computed from the linked object.
    IF linked_importance is not null AND
       (NEW.importance is null or NEW.importance < linked_importance)
    THEN
      NEW.importance = linked_importance;
    END IF;
  END IF;

  -- Initialise the name vector using our name
  NEW.name := add_default_place_name(NEW.country_code, NEW.name);
  name_vector := make_keywords(NEW.name);

  -- make sure all names are in the word table
  IF NEW.admin_level = 2
     AND NEW.class = 'boundary' AND NEW.type = 'administrative'
     AND NEW.country_code IS NOT NULL AND NEW.osm_type = 'R'
  THEN
    PERFORM create_country(NEW.name, lower(NEW.country_code));
    --DEBUG: RAISE WARNING 'Country names updated';
  END IF;

  SELECT * FROM insert_addresslines(NEW.place_id, NEW.partition,
                                    NEW.rank_search, NEW.address,
                                    CASE WHEN NEW.rank_search >= 26
                                             AND NEW.rank_search < 30
                                      THEN NEW.geometry ELSE NEW.centroid END)
    INTO NEW.parent_place_id, NEW.postcode, nameaddress_vector;

  --DEBUG: RAISE WARNING 'RETURN insert_addresslines: %, %, %', NEW.parent_place_id, NEW.postcode, nameaddress_vector;

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
                       nameaddress_vector, NEW.centroid);
    END IF;

  END IF;

  --DEBUG: RAISE WARNING 'place update % % finsihed.', NEW.osm_type, NEW.osm_id;

  RETURN NEW;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION placex_delete()
  RETURNS TRIGGER
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
