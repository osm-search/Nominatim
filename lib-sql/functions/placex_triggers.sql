-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- Trigger functions for the placex table.

-- Information returned by update preparation.
DROP TYPE IF EXISTS prepare_update_info CASCADE;
CREATE TYPE prepare_update_info AS (
  name HSTORE,
  address HSTORE,
  rank_address SMALLINT,
  country_code TEXT,
  class TEXT,
  type TEXT,
  linked_place_id BIGINT,
  centroid_x float,
  centroid_y float
);

-- Retrieve the data needed by the indexer for updating the place.
CREATE OR REPLACE FUNCTION placex_indexing_prepare(p placex)
  RETURNS prepare_update_info
  AS $$
DECLARE
  location RECORD;
  result prepare_update_info;
  extra_names HSTORE;
BEGIN
  IF not p.address ? '_inherited' THEN
    result.address := p.address;
  END IF;

  -- For POI nodes, check if the address should be derived from a surrounding
  -- building.
  IF p.rank_search = 30 AND p.osm_type = 'N' THEN
    IF p.address is null THEN
        -- The additional && condition works around the misguided query
        -- planner of postgis 3.0.
        SELECT placex.address || hstore('_inherited', '') INTO result.address
          FROM placex
         WHERE ST_Covers(geometry, p.centroid)
               and geometry && p.centroid
               and placex.address is not null
               and (placex.address ? 'housenumber' or placex.address ? 'street' or placex.address ? 'place')
               and rank_search = 30 AND ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon')
         LIMIT 1;
    ELSE
      -- See if we can inherit additional address tags from an interpolation.
      -- These will become permanent.
      FOR location IN
        SELECT (address - 'interpolation'::text - 'housenumber'::text) as address
          FROM place, planet_osm_ways w
          WHERE place.osm_type = 'W' and place.address ? 'interpolation'
                and place.geometry && p.geometry
                and place.osm_id = w.id
                and p.osm_id = any(w.nodes)
      LOOP
        result.address := location.address || result.address;
      END LOOP;
    END IF;
  END IF;

  -- remove internal and derived names
  result.address := result.address - '_unlisted_place'::TEXT;
  SELECT hstore(array_agg(key), array_agg(value)) INTO result.name
    FROM each(p.name) WHERE key not like '\_%';

  result.class := p.class;
  result.type := p.type;
  result.country_code := p.country_code;
  result.rank_address := p.rank_address;
  result.centroid_x := ST_X(p.centroid);
  result.centroid_y := ST_Y(p.centroid);

  -- Names of linked places need to be merged in, so search for a linkable
  -- place already here.
  SELECT * INTO location FROM find_linked_place(p);

  IF location.place_id is not NULL THEN
    result.linked_place_id := location.place_id;

    IF location.name is not NULL THEN
      {% if debug %}RAISE WARNING 'Names original: %, location: %', result.name, location.name;{% endif %}
      -- Add all names from the place nodes that deviate from the name
      -- in the relation with the prefix '_place_'. Deviation means that
      -- either the value is different or a given key is missing completely
      SELECT hstore(array_agg('_place_' || key), array_agg(value)) INTO extra_names
        FROM each(location.name - result.name);
      {% if debug %}RAISE WARNING 'Extra names: %', extra_names;{% endif %}

      IF extra_names is not null THEN
          result.name := result.name || extra_names;
      END IF;

      {% if debug %}RAISE WARNING 'Final names: %', result.name;{% endif %}
    END IF;
  END IF;

  RETURN result;
END;
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION find_associated_street(poi_osm_type CHAR(1),
                                                  poi_osm_id BIGINT)
  RETURNS BIGINT
  AS $$
DECLARE
  location RECORD;
  parent RECORD;
BEGIN
  FOR location IN
    SELECT members FROM planet_osm_rels
    WHERE parts @> ARRAY[poi_osm_id]
          and members @> ARRAY[lower(poi_osm_type) || poi_osm_id]
          and tags @> ARRAY['associatedStreet']
  LOOP
    FOR i IN 1..array_upper(location.members, 1) BY 2 LOOP
      IF location.members[i+1] = 'street' THEN
        FOR parent IN
          SELECT place_id from placex
           WHERE osm_type = upper(substring(location.members[i], 1, 1))::char(1)
                 and osm_id = substring(location.members[i], 2)::bigint
                 and name is not null
                 and rank_search between 26 and 27
        LOOP
          RETURN parent.place_id;
        END LOOP;
      END IF;
    END LOOP;
  END LOOP;

  RETURN NULL;
END;
$$
LANGUAGE plpgsql STABLE;


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
                                               token_info JSONB,
                                               is_place_addr BOOLEAN)
  RETURNS BIGINT
  AS $$
DECLARE
  parent_place_id BIGINT DEFAULT NULL;
  location RECORD;
BEGIN
  {% if debug %}RAISE WARNING 'finding street for % %', poi_osm_type, poi_osm_id;{% endif %}

  -- Is this object part of an associatedStreet relation?
  parent_place_id := find_associated_street(poi_osm_type, poi_osm_id);

  IF parent_place_id is null THEN
    parent_place_id := find_parent_for_address(token_info, poi_partition, bbox);
  END IF;

  IF parent_place_id is null and poi_osm_type = 'N' THEN
    FOR location IN
      SELECT p.place_id, p.osm_id, p.rank_search, p.address,
             coalesce(p.centroid, ST_Centroid(p.geometry)) as centroid
        FROM placex p, planet_osm_ways w
       WHERE p.osm_type = 'W' and p.rank_search >= 26
             and p.geometry && bbox
             and w.id = p.osm_id and poi_osm_id = any(w.nodes)
    LOOP
      {% if debug %}RAISE WARNING 'Node is part of way % ', location.osm_id;{% endif %}

      -- Way IS a road then we are on it - that must be our road
      IF location.rank_search < 28 THEN
        {% if debug %}RAISE WARNING 'node in way that is a street %',location;{% endif %}
        RETURN location.place_id;
      END IF;

      parent_place_id := find_associated_street('W', location.osm_id);
    END LOOP;
  END IF;

  IF parent_place_id is NULL THEN
    IF is_place_addr THEN
      -- The address is attached to a place we don't know.
      -- Instead simply use the containing area with the largest rank.
      FOR location IN
        SELECT place_id FROM placex
         WHERE bbox && geometry AND _ST_Covers(geometry, ST_Centroid(bbox))
               AND rank_address between 5 and 25
         ORDER BY rank_address desc
      LOOP
        RETURN location.place_id;
      END LOOP;
    ELSEIF ST_Area(bbox) < 0.005 THEN
      -- for smaller features get the nearest road
      SELECT getNearestRoadPlaceId(poi_partition, bbox) INTO parent_place_id;
      {% if debug %}RAISE WARNING 'Checked for nearest way (%)', parent_place_id;{% endif %}
    ELSE
      -- for larger features simply find the area with the largest rank that
      -- contains the bbox, only use addressable features
      FOR location IN
        SELECT place_id FROM placex
         WHERE bbox && geometry AND _ST_Covers(geometry, ST_Centroid(bbox))
               AND rank_address between 5 and 25
        ORDER BY rank_address desc
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
     or bnd.type IN ('postcode', 'postal_code')
  THEN
    RETURN NULL;
  END IF;

  IF bnd.osm_type = 'R' THEN
    -- see if we have any special relation members
    SELECT members FROM planet_osm_rels WHERE id = bnd.osm_id INTO relation_members;
    {% if debug %}RAISE WARNING 'Got relation members';{% endif %}

    -- Search for relation members with role 'lable'.
    IF relation_members IS NOT NULL THEN
      FOR rel_member IN
        SELECT get_rel_node_members(relation_members, ARRAY['label']) as member
      LOOP
        {% if debug %}RAISE WARNING 'Found label member %', rel_member.member;{% endif %}

        FOR linked_placex IN
          SELECT * from placex
          WHERE osm_type = 'N' and osm_id = rel_member.member
            and class = 'place'
        LOOP
          {% if debug %}RAISE WARNING 'Linked label member';{% endif %}
          RETURN linked_placex;
        END LOOP;

      END LOOP;
    END IF;
  END IF;

  IF bnd.name ? 'name' THEN
    bnd_name := lower(bnd.name->'name');
    IF bnd_name = '' THEN
      bnd_name := NULL;
    END IF;
  END IF;

  -- If extratags has a place tag, look for linked nodes by their place type.
  -- Area and node still have to have the same name.
  IF bnd.extratags ? 'place' and bnd_name is not null THEN
    FOR linked_placex IN
      SELECT * FROM placex
      WHERE (position(lower(name->'name') in bnd_name) > 0
             OR position(bnd_name in lower(name->'name')) > 0)
        AND placex.class = 'place' AND placex.type = bnd.extratags->'place'
        AND placex.osm_type = 'N'
        AND (placex.linked_place_id is null or placex.linked_place_id = bnd.place_id)
        AND placex.rank_search < 26 -- needed to select the right index
        AND placex.type != 'postcode'
        AND ST_Covers(bnd.geometry, placex.geometry)
    LOOP
      {% if debug %}RAISE WARNING 'Found type-matching place node %', linked_placex.osm_id;{% endif %}
      RETURN linked_placex;
    END LOOP;
  END IF;

  IF bnd.extratags ? 'wikidata' THEN
    FOR linked_placex IN
      SELECT * FROM placex
      WHERE placex.class = 'place' AND placex.osm_type = 'N'
        AND placex.extratags ? 'wikidata' -- needed to select right index
        AND placex.extratags->'wikidata' = bnd.extratags->'wikidata'
        AND (placex.linked_place_id is null or placex.linked_place_id = bnd.place_id)
        AND placex.rank_search < 26
        AND _st_covers(bnd.geometry, placex.geometry)
      ORDER BY lower(name->'name') = bnd_name desc
    LOOP
      {% if debug %}RAISE WARNING 'Found wikidata-matching place node %', linked_placex.osm_id;{% endif %}
      RETURN linked_placex;
    END LOOP;
  END IF;

  -- Name searches can be done for ways as well as relations
  IF bnd_name is not null THEN
    {% if debug %}RAISE WARNING 'Looking for nodes with matching names';{% endif %}
    FOR linked_placex IN
      SELECT placex.* from placex
      WHERE lower(name->'name') = bnd_name
        AND ((bnd.rank_address > 0
              and bnd.rank_address = (compute_place_rank(placex.country_code,
                                                         'N', placex.class,
                                                         placex.type, 15::SMALLINT,
                                                         false, placex.postcode)).address_rank)
             OR (bnd.rank_address = 0 and placex.rank_search = bnd.rank_search))
        AND placex.osm_type = 'N'
        AND placex.class = 'place'
        AND (placex.linked_place_id is null or placex.linked_place_id = bnd.place_id)
        AND placex.rank_search < 26 -- needed to select the right index
        AND placex.type != 'postcode'
        AND ST_Covers(bnd.geometry, placex.geometry)
    LOOP
      {% if debug %}RAISE WARNING 'Found matching place node %', linked_placex.osm_id;{% endif %}
      RETURN linked_placex;
    END LOOP;
  END IF;

  RETURN NULL;
END;
$$
LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION create_poi_search_terms(obj_place_id BIGINT,
                                                   in_partition SMALLINT,
                                                   parent_place_id BIGINT,
                                                   is_place_addr BOOLEAN,
                                                   country TEXT,
                                                   token_info JSONB,
                                                   geometry GEOMETRY,
                                                   OUT name_vector INTEGER[],
                                                   OUT nameaddress_vector INTEGER[])
  AS $$
DECLARE
  parent_name_vector INTEGER[];
  parent_address_vector INTEGER[];
  addr_place_ids INTEGER[];
  hnr_vector INTEGER[];

  addr_item RECORD;
  addr_place RECORD;
  parent_address_place_ids BIGINT[];
BEGIN
  nameaddress_vector := '{}'::INTEGER[];

  SELECT s.name_vector, s.nameaddress_vector
    INTO parent_name_vector, parent_address_vector
    FROM search_name s
    WHERE s.place_id = parent_place_id;

  FOR addr_item IN
    SELECT ranks.*, key,
           token_get_address_search_tokens(token_info, key) as search_tokens
      FROM token_get_address_keys(token_info) as key,
           LATERAL get_addr_tag_rank(key, country) as ranks
      WHERE not token_get_address_search_tokens(token_info, key) <@ parent_address_vector
  LOOP
    addr_place := get_address_place(in_partition, geometry,
                                    addr_item.from_rank, addr_item.to_rank,
                                    addr_item.extent, token_info, addr_item.key);

    IF addr_place is null THEN
      -- No place found in OSM that matches. Make it at least searchable.
      nameaddress_vector := array_merge(nameaddress_vector, addr_item.search_tokens);
    ELSE
      IF parent_address_place_ids is null THEN
        SELECT array_agg(parent_place_id) INTO parent_address_place_ids
          FROM place_addressline
          WHERE place_id = parent_place_id;
      END IF;

      -- If the parent already lists the place in place_address line, then we
      -- are done. Otherwise, add its own place_address line.
      IF not parent_address_place_ids @> ARRAY[addr_place.place_id] THEN
        nameaddress_vector := array_merge(nameaddress_vector, addr_place.keywords);

        INSERT INTO place_addressline (place_id, address_place_id, fromarea,
                                       isaddress, distance, cached_rank_address)
          VALUES (obj_place_id, addr_place.place_id, not addr_place.isguess,
                    true, addr_place.distance, addr_place.rank_address);
      END IF;
    END IF;
  END LOOP;

  name_vector := token_get_name_search_tokens(token_info);

  -- Check if the parent covers all address terms.
  -- If not, create a search name entry with the house number as the name.
  -- This is unusual for the search_name table but prevents that the place
  -- is returned when we only search for the street/place.

  hnr_vector := token_get_housenumber_search_tokens(token_info);

  IF hnr_vector is not null and not nameaddress_vector <@ parent_address_vector THEN
    name_vector := array_merge(name_vector, hnr_vector);
  END IF;

  IF is_place_addr THEN
    addr_place_ids := token_addr_place_search_tokens(token_info);
    IF not addr_place_ids <@ parent_name_vector THEN
      -- make sure addr:place terms are always searchable
      nameaddress_vector := array_merge(nameaddress_vector, addr_place_ids);
      -- If there is a housenumber, also add the place name as a name,
      -- so we can search it by the usual housenumber+place algorithms.
      IF hnr_vector is not null THEN
        name_vector := array_merge(name_vector, addr_place_ids);
      END IF;
    END IF;
  END IF;

  -- Cheating here by not recomputing all terms but simply using the ones
  -- from the parent object.
  nameaddress_vector := array_merge(nameaddress_vector, parent_name_vector);
  nameaddress_vector := array_merge(nameaddress_vector, parent_address_vector);

END;
$$
LANGUAGE plpgsql;


-- Insert address of a place into the place_addressline table.
--
-- \param obj_place_id  Place_id of the place to compute the address for.
-- \param partition     Partition number where the place is in.
-- \param maxrank       Rank of the place. All address features must have
--                      a search rank lower than the given rank.
-- \param address       Address terms for the place.
-- \param geometry      Geometry to which the address objects should be close.
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
                                               token_info JSONB,
                                               geometry GEOMETRY,
                                               centroid GEOMETRY,
                                               country TEXT,
                                               OUT parent_place_id BIGINT,
                                               OUT postcode TEXT,
                                               OUT nameaddress_vector INT[])
  AS $$
DECLARE
  address_havelevel BOOLEAN[];

  location_isaddress BOOLEAN;
  current_boundary GEOMETRY := NULL;
  current_node_area GEOMETRY := NULL;

  parent_place_rank INT := 0;
  addr_place_ids BIGINT[] := '{}'::int[];
  new_address_vector INT[];

  location RECORD;
BEGIN
  parent_place_id := 0;
  nameaddress_vector := '{}'::int[];

  address_havelevel := array_fill(false, ARRAY[maxrank]);

  FOR location IN
    SELECT apl.*, key
      FROM (SELECT extra.*, key
              FROM token_get_address_keys(token_info) as key,
                   LATERAL get_addr_tag_rank(key, country) as extra) x,
           LATERAL get_address_place(partition, geometry, from_rank, to_rank,
                              extent, token_info, key) as apl
      ORDER BY rank_address, distance, isguess desc
  LOOP
    IF location.place_id is null THEN
      {% if not db.reverse_only %}
      nameaddress_vector := array_merge(nameaddress_vector,
                                        token_get_address_search_tokens(token_info,
                                                                        location.key));
      {% endif %}
    ELSE
      {% if not db.reverse_only %}
      nameaddress_vector := array_merge(nameaddress_vector, location.keywords::INTEGER[]);
      {% endif %}

      location_isaddress := not address_havelevel[location.rank_address];
      IF not address_havelevel[location.rank_address] THEN
        address_havelevel[location.rank_address] := true;
        IF parent_place_rank < location.rank_address THEN
          parent_place_id := location.place_id;
          parent_place_rank := location.rank_address;
        END IF;
      END IF;

      INSERT INTO place_addressline (place_id, address_place_id, fromarea,
                                     isaddress, distance, cached_rank_address)
        VALUES (obj_place_id, location.place_id, not location.isguess,
                true, location.distance, location.rank_address);

      addr_place_ids := addr_place_ids || location.place_id;
    END IF;
  END LOOP;

  FOR location IN
    SELECT * FROM getNearFeatures(partition, geometry, centroid, maxrank)
    WHERE not addr_place_ids @> ARRAY[place_id]
    ORDER BY rank_address, isguess asc,
             distance *
               CASE WHEN rank_address = 16 AND rank_search = 15 THEN 0.2
                    WHEN rank_address = 16 AND rank_search = 16 THEN 0.25
                    WHEN rank_address = 16 AND rank_search = 18 THEN 0.5
                    ELSE 1 END ASC
  LOOP
    -- Ignore all place nodes that do not fit in a lower level boundary.
    CONTINUE WHEN location.isguess
                  and current_boundary is not NULL
                  and not ST_Contains(current_boundary, location.centroid);

    -- If this is the first item in the rank, then assume it is the address.
    location_isaddress := not address_havelevel[location.rank_address];

    -- Further sanity checks to ensure that the address forms a sane hierarchy.
    IF location_isaddress THEN
      IF location.isguess and current_node_area is not NULL THEN
        location_isaddress := ST_Contains(current_node_area, location.centroid);
      END IF;
      IF not location.isguess and current_boundary is not NULL
         and location.rank_address != 11 AND location.rank_address != 5 THEN
        location_isaddress := ST_Contains(current_boundary, location.centroid);
      END IF;
    END IF;

    IF location_isaddress THEN
      address_havelevel[location.rank_address] := true;
      parent_place_id := location.place_id;

      -- Set postcode if we have one.
      -- (Returned will be the highest ranking one.)
      IF location.postcode is not NULL THEN
        postcode = location.postcode;
      END IF;

      -- Recompute the areas we need for hierarchy sanity checks.
      IF location.rank_address != 11 AND location.rank_address != 5 THEN
        IF location.isguess THEN
          current_node_area := place_node_fuzzy_area(location.centroid,
                                                     location.rank_search);
        ELSE
          current_node_area := NULL;
          SELECT p.geometry FROM placex p
              WHERE p.place_id = location.place_id INTO current_boundary;
        END IF;
      END IF;
    END IF;

    -- Add it to the list of search terms
    {% if not db.reverse_only %}
      nameaddress_vector := array_merge(nameaddress_vector,
                                        location.keywords::integer[]);
    {% endif %}

    INSERT INTO place_addressline (place_id, address_place_id, fromarea,
                                     isaddress, distance, cached_rank_address)
        VALUES (obj_place_id, location.place_id, not location.isguess,
                location_isaddress, location.distance, location.rank_address);
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
BEGIN
  {% if debug %}RAISE WARNING '% % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;{% endif %}

  NEW.place_id := nextval('seq_place');
  NEW.indexed_status := 1; --STATUS_NEW

  NEW.centroid := ST_PointOnSurface(NEW.geometry);
  NEW.country_code := lower(get_country_code(NEW.centroid));

  NEW.partition := get_partition(NEW.country_code);
  NEW.geometry_sector := geometry_sector(NEW.partition, NEW.centroid);

  IF NEW.osm_type = 'X' THEN
    -- E'X'ternal records should already be in the right format so do nothing
  ELSE
    is_area := ST_GeometryType(NEW.geometry) IN ('ST_Polygon','ST_MultiPolygon');

    IF NEW.class in ('place','boundary')
       AND NEW.type in ('postcode','postal_code')
    THEN
      IF NEW.address IS NULL OR NOT NEW.address ? 'postcode' THEN
          -- most likely just a part of a multipolygon postcode boundary, throw it away
          RETURN NULL;
      END IF;

      NEW.name := hstore('ref', NEW.address->'postcode');

    ELSEIF NEW.class = 'highway' AND is_area AND NEW.name is null
           AND NEW.extratags ? 'area' AND NEW.extratags->'area' = 'yes'
    THEN
        RETURN NULL;
    ELSEIF NEW.class = 'boundary' AND NOT is_area
    THEN
        RETURN NULL;
    ELSEIF NEW.class = 'boundary' AND NEW.type = 'administrative'
           AND NEW.admin_level <= 4 AND NEW.osm_type = 'W'
    THEN
        RETURN NULL;
    END IF;

    SELECT * INTO NEW.rank_search, NEW.rank_address
      FROM compute_place_rank(NEW.country_code,
                              CASE WHEN is_area THEN 'A' ELSE NEW.osm_type END,
                              NEW.class, NEW.type, NEW.admin_level,
                              (NEW.extratags->'capital') = 'yes',
                              NEW.address->'postcode');

    -- a country code make no sense below rank 4 (country)
    IF NEW.rank_search < 4 THEN
      NEW.country_code := NULL;
    END IF;

  END IF;

  {% if debug %}RAISE WARNING 'placex_insert:END: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;{% endif %}

{% if not disable_diff_updates %}
  -- The following is not needed until doing diff updates, and slows the main index process down

  IF NEW.rank_address > 0 THEN
    IF (ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon') AND ST_IsValid(NEW.geometry)) THEN
      -- Performance: We just can't handle re-indexing for country level changes
      IF st_area(NEW.geometry) < 1 THEN
        -- mark items within the geometry for re-indexing
  --    RAISE WARNING 'placex poly insert: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;

        UPDATE placex SET indexed_status = 2
         WHERE ST_Intersects(NEW.geometry, placex.geometry)
               and indexed_status = 0
               and ((rank_address = 0 and rank_search > NEW.rank_address)
                    or rank_address > NEW.rank_address
                    or (class = 'place' and osm_type = 'N')
                   )
               and (rank_search < 28
                    or name is not null
                    or (NEW.rank_address >= 16 and address ? 'place'));
      END IF;
    ELSE
      -- mark nearby items for re-indexing, where 'nearby' depends on the features rank_search and is a complete guess :(
      diameter := update_place_diameter(NEW.rank_search);
      IF diameter > 0 THEN
  --      RAISE WARNING 'placex point insert: % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,diameter;
        IF NEW.rank_search >= 26 THEN
          -- roads may cause reparenting for >27 rank places
          update placex set indexed_status = 2 where indexed_status = 0 and rank_search > NEW.rank_search and ST_DWithin(placex.geometry, NEW.geometry, diameter);
          -- reparenting also for OSM Interpolation Lines (and for Tiger?)
          update location_property_osmline set indexed_status = 2 where indexed_status = 0 and startnumber is not null and ST_DWithin(location_property_osmline.linegeo, NEW.geometry, diameter);
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

{% endif %} -- not disable_diff_updates

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

  geom GEOMETRY;
  parent_address_level SMALLINT;
  place_address_level SMALLINT;

  max_rank SMALLINT;

  name_vector INTEGER[];
  nameaddress_vector INTEGER[];
  addr_nameaddress_vector INTEGER[];

  linked_place BIGINT;

  linked_node_id BIGINT;
  linked_importance FLOAT;
  linked_wikipedia TEXT;

  is_place_address BOOLEAN;
  result BOOLEAN;
BEGIN
  -- deferred delete
  IF OLD.indexed_status = 100 THEN
    {% if debug %}RAISE WARNING 'placex_update delete % %',NEW.osm_type,NEW.osm_id;{% endif %}
    delete from placex where place_id = OLD.place_id;
    RETURN NULL;
  END IF;

  IF NEW.indexed_status != 0 OR OLD.indexed_status = 0 THEN
    RETURN NEW;
  END IF;

  {% if debug %}RAISE WARNING 'placex_update % % (%)',NEW.osm_type,NEW.osm_id,NEW.place_id;{% endif %}

  NEW.indexed_date = now();

  {% if 'search_name' in db.tables %}
    DELETE from search_name WHERE place_id = NEW.place_id;
  {% endif %}
  result := deleteSearchName(NEW.partition, NEW.place_id);
  DELETE FROM place_addressline WHERE place_id = NEW.place_id;
  result := deleteRoad(NEW.partition, NEW.place_id);
  result := deleteLocationArea(NEW.partition, NEW.place_id, NEW.rank_search);

  NEW.extratags := NEW.extratags - 'linked_place'::TEXT;

  -- NEW.linked_place_id contains the precomputed linkee. Save this and restore
  -- the previous link status.
  linked_place := NEW.linked_place_id;
  NEW.linked_place_id := OLD.linked_place_id;

  -- Remove linkage, if we have computed a different new linkee.
  UPDATE placex SET linked_place_id = null, indexed_status = 2
    WHERE linked_place_id = NEW.place_id
          and (linked_place is null or linked_place_id != linked_place);
  -- update not necessary for osmline, cause linked_place_id does not exist

  -- Postcodes are just here to compute the centroids. They are not searchable
  -- unless they are a boundary=postal_code.
  -- There was an error in the style so that boundary=postal_code used to be
  -- imported as place=postcode. That's why relations are allowed to pass here.
  -- This can go away in a couple of versions.
  IF NEW.class = 'place'  and NEW.type = 'postcode' and NEW.osm_type != 'R' THEN
    NEW.token_info := null;
    RETURN NEW;
  END IF;

  -- Compute a preliminary centroid.
  NEW.centroid := ST_PointOnSurface(NEW.geometry);

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
  {% if debug %}RAISE WARNING 'Country updated: "%"', NEW.country_code;{% endif %}


  -- recompute the ranks, they might change when linking changes
  SELECT * INTO NEW.rank_search, NEW.rank_address
    FROM compute_place_rank(NEW.country_code,
                            CASE WHEN ST_GeometryType(NEW.geometry)
                                        IN ('ST_Polygon','ST_MultiPolygon')
                            THEN 'A' ELSE NEW.osm_type END,
                            NEW.class, NEW.type, NEW.admin_level,
                            (NEW.extratags->'capital') = 'yes',
                            NEW.address->'postcode');

  -- Short-cut out for linked places. Note that this must happen after the
  -- address rank has been recomputed. The linking might nullify a shift in
  -- address rank.
  IF NEW.linked_place_id is not null THEN
    NEW.token_info := null;
    {% if debug %}RAISE WARNING 'place already linked to %', OLD.linked_place_id;{% endif %}
    RETURN NEW;
  END IF;

  -- We must always increase the address level relative to the admin boundary.
  IF NEW.class = 'boundary' and NEW.type = 'administrative'
     and NEW.osm_type = 'R' and NEW.rank_address > 0
  THEN
    -- First, check that admin boundaries do not overtake each other rank-wise.
    parent_address_level := 3;
    FOR location IN
      SELECT rank_address,
             (CASE WHEN extratags ? 'wikidata' and NEW.extratags ? 'wikidata'
                        and extratags->'wikidata' = NEW.extratags->'wikidata'
                   THEN ST_Equals(geometry, NEW.geometry)
                   ELSE false END) as is_same
      FROM placex
      WHERE osm_type = 'R' and class = 'boundary' and type = 'administrative'
            and admin_level < NEW.admin_level and admin_level > 3
            and rank_address > 0
            and geometry && NEW.centroid and _ST_Covers(geometry, NEW.centroid)
      ORDER BY admin_level desc LIMIT 1
    LOOP
      IF location.is_same THEN
        -- Looks like the same boundary is replicated on multiple admin_levels.
        -- Usual tagging in Poland. Remove our boundary from addresses.
        NEW.rank_address := 0;
      ELSE
        parent_address_level := location.rank_address;
        IF location.rank_address >= NEW.rank_address THEN
          IF location.rank_address >= 24 THEN
            NEW.rank_address := 25;
          ELSE
            NEW.rank_address := location.rank_address + 2;
          END IF;
        END IF;
      END IF;
    END LOOP;

    IF NEW.rank_address > 9 THEN
        -- Second check that the boundary is not completely contained in a
        -- place area with a equal or higher address rank.
        FOR location IN
          SELECT rank_address
          FROM placex,
               LATERAL compute_place_rank(country_code, 'A', class, type,
                                          admin_level, False, null) prank
          WHERE class = 'place' and rank_address < 24
                and prank.address_rank >= NEW.rank_address
                and geometry && NEW.geometry
                and geometry ~ NEW.geometry -- needed because ST_Relate does not do bbox cover test
                and ST_Relate(geometry, NEW.geometry, 'T*T***FF*') -- contains but not equal
          ORDER BY prank.address_rank desc LIMIT 1
        LOOP
          NEW.rank_address := location.rank_address + 2;
        END LOOP;
    END IF;
  ELSEIF NEW.class = 'place'
         and ST_GeometryType(NEW.geometry) in ('ST_Polygon', 'ST_MultiPolygon')
         and NEW.rank_address between 16 and 23
  THEN
    -- For place areas make sure they are not completely contained in an area
    -- with a equal or higher address rank.
    FOR location IN
          SELECT rank_address
          FROM placex,
               LATERAL compute_place_rank(country_code, 'A', class, type,
                                          admin_level, False, null) prank
          WHERE prank.address_rank < 24
                and prank.address_rank >= NEW.rank_address
                and geometry && NEW.geometry
                and geometry ~ NEW.geometry -- needed because ST_Relate does not do bbox cover test
                and ST_Relate(geometry, NEW.geometry, 'T*T***FF*') -- contains but not equal
          ORDER BY prank.address_rank desc LIMIT 1
        LOOP
          NEW.rank_address := location.rank_address + 2;
        END LOOP;
  ELSEIF NEW.class = 'place' and NEW.osm_type = 'N'
         and NEW.rank_address between 16 and 23
  THEN
    -- If a place node is contained in an admin or place boundary with the same
    -- address level and has not been linked, then make the node a subpart
    -- by increasing the address rank (city level and above).
    FOR location IN
        SELECT rank_address
        FROM placex,
             LATERAL compute_place_rank(country_code, 'A', class, type,
                                        admin_level, False, null) prank
        WHERE osm_type = 'R'
              and ((class = 'place' and prank.address_rank = NEW.rank_address)
                   or (class = 'boundary' and rank_address = NEW.rank_address))
              and geometry && NEW.centroid and _ST_Covers(geometry, NEW.centroid)
        LIMIT 1
    LOOP
      NEW.rank_address = NEW.rank_address + 2;
    END LOOP;
  ELSE
    parent_address_level := 3;
  END IF;

  NEW.housenumber := token_normalized_housenumber(NEW.token_info);

  NEW.postcode := null;

  -- waterway ways are linked when they are part of a relation and have the same class/type
  IF NEW.osm_type = 'R' and NEW.class = 'waterway' THEN
      FOR relation_members IN select members from planet_osm_rels r where r.id = NEW.osm_id and r.parts != array[]::bigint[]
      LOOP
          FOR i IN 1..array_upper(relation_members, 1) BY 2 LOOP
              IF relation_members[i+1] in ('', 'main_stream', 'side_stream') AND substring(relation_members[i],1,1) = 'w' THEN
                {% if debug %}RAISE WARNING 'waterway parent %, child %/%', NEW.osm_id, i, relation_members[i];{% endif %}
                FOR linked_node_id IN SELECT place_id FROM placex
                  WHERE osm_type = 'W' and osm_id = substring(relation_members[i],2,200)::bigint
                  and class = NEW.class and type in ('river', 'stream', 'canal', 'drain', 'ditch')
                  and ( relation_members[i+1] != 'side_stream' or NEW.name->'name' = name->'name')
                LOOP
                  UPDATE placex SET linked_place_id = NEW.place_id WHERE place_id = linked_node_id;
                  {% if 'search_name' in db.tables %}
                    DELETE FROM search_name WHERE place_id = linked_node_id;
                  {% endif %}
                END LOOP;
              END IF;
          END LOOP;
      END LOOP;
      {% if debug %}RAISE WARNING 'Waterway processed';{% endif %}
  END IF;

  NEW.importance := null;
  SELECT wikipedia, importance
    FROM compute_importance(NEW.extratags, NEW.country_code, NEW.osm_type, NEW.osm_id)
    INTO NEW.wikipedia,NEW.importance;

{% if debug %}RAISE WARNING 'Importance computed from wikipedia: %', NEW.importance;{% endif %}

  -- ---------------------------------------------------------------------------
  -- For low level elements we inherit from our parent road
  IF NEW.rank_search > 27 THEN

    {% if debug %}RAISE WARNING 'finding street for % %', NEW.osm_type, NEW.osm_id;{% endif %}
    NEW.parent_place_id := null;
    is_place_address := coalesce(not NEW.address ? 'street' and NEW.address ? 'place', FALSE);

    -- We have to find our parent road.
    NEW.parent_place_id := find_parent_for_poi(NEW.osm_type, NEW.osm_id,
                                               NEW.partition,
                                               ST_Envelope(NEW.geometry),
                                               NEW.token_info,
                                               is_place_address);

    -- If we found the road take a shortcut here.
    -- Otherwise fall back to the full address getting method below.
    IF NEW.parent_place_id is not null THEN

      -- Get the details of the parent road
      SELECT p.country_code, p.postcode, p.name FROM placex p
       WHERE p.place_id = NEW.parent_place_id INTO location;

      IF is_place_address THEN
        -- Check if the addr:place tag is part of the parent name
        SELECT count(*) INTO i
          FROM svals(location.name) AS pname WHERE pname = NEW.address->'place';
        IF i = 0 THEN
          NEW.address = NEW.address || hstore('_unlisted_place', NEW.address->'place');
        END IF;
      END IF;

      NEW.country_code := location.country_code;
      {% if debug %}RAISE WARNING 'Got parent details from search name';{% endif %}

      -- determine postcode
      NEW.postcode := coalesce(token_get_postcode(NEW.token_info),
                               location.postcode,
                               get_nearest_postcode(NEW.country_code, NEW.centroid));

      IF NEW.name is not NULL THEN
          NEW.name := add_default_place_name(NEW.country_code, NEW.name);
      END IF;

      {% if not db.reverse_only %}
      IF NEW.name is not NULL OR NEW.address is not NULL THEN
        SELECT * INTO name_vector, nameaddress_vector
          FROM create_poi_search_terms(NEW.place_id,
                                       NEW.partition, NEW.parent_place_id,
                                       is_place_address, NEW.country_code,
                                       NEW.token_info, NEW.centroid);

        IF array_length(name_vector, 1) is not NULL THEN
          INSERT INTO search_name (place_id, search_rank, address_rank,
                                   importance, country_code, name_vector,
                                   nameaddress_vector, centroid)
                 VALUES (NEW.place_id, NEW.rank_search, NEW.rank_address,
                         NEW.importance, NEW.country_code, name_vector,
                         nameaddress_vector, NEW.centroid);
          {% if debug %}RAISE WARNING 'Place added to search table';{% endif %}
        END IF;
      END IF;
      {% endif %}

      NEW.token_info := token_strip_info(NEW.token_info);

      RETURN NEW;
    END IF;

  END IF;

  -- ---------------------------------------------------------------------------
  -- Full indexing
  {% if debug %}RAISE WARNING 'Using full index mode for % %', NEW.osm_type, NEW.osm_id;{% endif %}
  IF linked_place is not null THEN
    -- Recompute the ranks here as the ones from the linked place might
    -- have been shifted to accommodate surrounding boundaries.
    SELECT place_id, osm_id, class, type, extratags,
           centroid, geometry,
           (compute_place_rank(country_code, osm_type, class, type, admin_level,
                              (extratags->'capital') = 'yes', null)).*
      INTO location
      FROM placex WHERE place_id = linked_place;

    {% if debug %}RAISE WARNING 'Linked %', location;{% endif %}

    -- Use the linked point as the centre point of the geometry,
    -- but only if it is within the area of the boundary.
    geom := coalesce(location.centroid, ST_Centroid(location.geometry));
    IF geom is not NULL AND ST_Within(geom, NEW.geometry) THEN
        NEW.centroid := geom;
    END IF;

    {% if debug %}RAISE WARNING 'parent address: % rank address: %', parent_address_level, location.address_rank;{% endif %}
    IF location.address_rank > parent_address_level
       and location.address_rank < 26
    THEN
      NEW.rank_address := location.address_rank;
    END IF;

    -- merge in extra tags
    NEW.extratags := hstore('linked_' || location.class, location.type)
                     || coalesce(location.extratags, ''::hstore)
                     || coalesce(NEW.extratags, ''::hstore);

    -- mark the linked place (excludes from search results)
    -- Force reindexing to remove any traces from the search indexes and
    -- reset the address rank if necessary.
    UPDATE placex set linked_place_id = NEW.place_id, indexed_status = 2
      WHERE place_id = location.place_id;
    -- ensure that those places are not found anymore
    {% if 'search_name' in db.tables %}
      DELETE FROM search_name WHERE place_id = location.place_id;
    {% endif %}
    PERFORM deleteLocationArea(NEW.partition, location.place_id, NEW.rank_search);

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
  ELSE
    -- No linked place? As a last resort check if the boundary is tagged with
    -- a place type and adapt the rank address.
    IF NEW.rank_address > 0 and NEW.extratags ? 'place' THEN
      SELECT address_rank INTO place_address_level
        FROM compute_place_rank(NEW.country_code, 'A', 'place',
                                NEW.extratags->'place', 0::SMALLINT, False, null);
      IF place_address_level > parent_address_level and
         place_address_level < 26 THEN
        NEW.rank_address := place_address_level;
      END IF;
    END IF;
  END IF;

  {% if not disable_diff_updates %}
  IF OLD.rank_address != NEW.rank_address THEN
    -- After a rank shift all addresses containing us must be updated.
    UPDATE placex p SET indexed_status = 2 FROM place_addressline pa
      WHERE pa.address_place_id = NEW.place_id and p.place_id = pa.place_id
            and p.indexed_status = 0 and p.rank_address between 4 and 25;
  END IF;
  {% endif %}

  IF NEW.admin_level = 2
     AND NEW.class = 'boundary' AND NEW.type = 'administrative'
     AND NEW.country_code IS NOT NULL AND NEW.osm_type = 'R'
  THEN
    -- Update the list of country names.
    -- Only take the name from the largest area for the given country code
    -- in the hope that this is the authoritative one.
    -- Also replace any old names so that all mapping mistakes can
    -- be fixed through regular OSM updates.
    FOR location IN
      SELECT osm_id FROM placex
       WHERE rank_search = 4 and osm_type = 'R'
             and country_code = NEW.country_code
       ORDER BY ST_Area(geometry) desc
       LIMIT 1
    LOOP
      IF location.osm_id = NEW.osm_id THEN
        {% if debug %}RAISE WARNING 'Updating names for country '%' with: %', NEW.country_code, NEW.name;{% endif %}
        UPDATE country_name SET derived_name = NEW.name WHERE country_code = NEW.country_code;
      END IF;
    END LOOP;
  END IF;

  -- For linear features we need the full geometry for determining the address
  -- because they may go through several administrative entities. Otherwise use
  -- the centroid for performance reasons.
  IF ST_GeometryType(NEW.geometry) in ('ST_LineString', 'ST_MultiLineString') THEN
    geom := NEW.geometry;
  ELSE
    geom := NEW.centroid;
  END IF;

  IF NEW.rank_address = 0 THEN
    max_rank := geometry_to_rank(NEW.rank_search, NEW.geometry, NEW.country_code);
    -- Rank 0 features may also span multiple administrative areas (e.g. lakes)
    -- so use the geometry here too. Just make sure the areas don't become too
    -- large.
    IF NEW.class = 'natural' or max_rank > 10 THEN
      geom := NEW.geometry;
    END IF;
  ELSEIF NEW.rank_address > 25 THEN
    max_rank := 25;
  ELSE
    max_rank := NEW.rank_address;
  END IF;

  SELECT * FROM insert_addresslines(NEW.place_id, NEW.partition, max_rank,
                                    NEW.token_info, geom, NEW.centroid,
                                    NEW.country_code)
    INTO NEW.parent_place_id, NEW.postcode, nameaddress_vector;

  {% if debug %}RAISE WARNING 'RETURN insert_addresslines: %, %, %', NEW.parent_place_id, NEW.postcode, nameaddress_vector;{% endif %}

  NEW.postcode := coalesce(token_get_postcode(NEW.token_info), NEW.postcode);

  -- if we have a name add this to the name search table
  IF NEW.name IS NOT NULL THEN
    -- Initialise the name vector using our name
    NEW.name := add_default_place_name(NEW.country_code, NEW.name);
    name_vector := token_get_name_search_tokens(NEW.token_info);

    IF NEW.rank_search <= 25 and NEW.rank_address > 0 THEN
      result := add_location(NEW.place_id, NEW.country_code, NEW.partition,
                             name_vector, NEW.rank_search, NEW.rank_address,
                             NEW.postcode, NEW.geometry, NEW.centroid);
      {% if debug %}RAISE WARNING 'added to location (full)';{% endif %}
    END IF;

    IF NEW.rank_search between 26 and 27 and NEW.class = 'highway' THEN
      result := insertLocationRoad(NEW.partition, NEW.place_id, NEW.country_code, NEW.geometry);
      {% if debug %}RAISE WARNING 'insert into road location table (full)';{% endif %}
    END IF;

    IF NEW.rank_address between 16 and 27 THEN
      result := insertSearchName(NEW.partition, NEW.place_id,
                                 token_get_name_match_tokens(NEW.token_info),
                                 NEW.rank_search, NEW.rank_address, NEW.geometry);
    END IF;
    {% if debug %}RAISE WARNING 'added to search name (full)';{% endif %}

    {% if not db.reverse_only %}
        INSERT INTO search_name (place_id, search_rank, address_rank,
                                 importance, country_code, name_vector,
                                 nameaddress_vector, centroid)
               VALUES (NEW.place_id, NEW.rank_search, NEW.rank_address,
                       NEW.importance, NEW.country_code, name_vector,
                       nameaddress_vector, NEW.centroid);
    {% endif %}
  END IF;

  IF NEW.postcode is null AND NEW.rank_search > 8 THEN
    NEW.postcode := get_nearest_postcode(NEW.country_code, NEW.geometry);
  END IF;

  {% if debug %}RAISE WARNING 'place update % % finished.', NEW.osm_type, NEW.osm_id;{% endif %}

  NEW.token_info := token_strip_info(NEW.token_info);
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

  IF OLD.linked_place_id is null THEN
    update placex set linked_place_id = null, indexed_status = 2 where linked_place_id = OLD.place_id and indexed_status = 0;
    {% if debug %}RAISE WARNING 'placex_delete:01 % %',OLD.osm_type,OLD.osm_id;{% endif %}
    update placex set linked_place_id = null where linked_place_id = OLD.place_id;
    {% if debug %}RAISE WARNING 'placex_delete:02 % %',OLD.osm_type,OLD.osm_id;{% endif %}
  ELSE
    update placex set indexed_status = 2 where place_id = OLD.linked_place_id and indexed_status = 0;
  END IF;

  IF OLD.rank_address < 30 THEN

    -- mark everything linked to this place for re-indexing
    {% if debug %}RAISE WARNING 'placex_delete:03 % %',OLD.osm_type,OLD.osm_id;{% endif %}
    UPDATE placex set indexed_status = 2 from place_addressline where address_place_id = OLD.place_id 
      and placex.place_id = place_addressline.place_id and indexed_status = 0 and place_addressline.isaddress;

    {% if debug %}RAISE WARNING 'placex_delete:04 % %',OLD.osm_type,OLD.osm_id;{% endif %}
    DELETE FROM place_addressline where address_place_id = OLD.place_id;

    {% if debug %}RAISE WARNING 'placex_delete:05 % %',OLD.osm_type,OLD.osm_id;{% endif %}
    b := deleteRoad(OLD.partition, OLD.place_id);

    {% if debug %}RAISE WARNING 'placex_delete:06 % %',OLD.osm_type,OLD.osm_id;{% endif %}
    update placex set indexed_status = 2 where parent_place_id = OLD.place_id and indexed_status = 0;
    {% if debug %}RAISE WARNING 'placex_delete:07 % %',OLD.osm_type,OLD.osm_id;{% endif %}
    -- reparenting also for OSM Interpolation Lines (and for Tiger?)
    update location_property_osmline set indexed_status = 2 where indexed_status = 0 and parent_place_id = OLD.place_id;

  END IF;

  {% if debug %}RAISE WARNING 'placex_delete:08 % %',OLD.osm_type,OLD.osm_id;{% endif %}

  IF OLD.rank_address < 26 THEN
    b := deleteLocationArea(OLD.partition, OLD.place_id, OLD.rank_search);
  END IF;

  {% if debug %}RAISE WARNING 'placex_delete:09 % %',OLD.osm_type,OLD.osm_id;{% endif %}

  IF OLD.name is not null THEN
    {% if 'search_name' in db.tables %}
      DELETE from search_name WHERE place_id = OLD.place_id;
    {% endif %}
    b := deleteSearchName(OLD.partition, OLD.place_id);
  END IF;

  {% if debug %}RAISE WARNING 'placex_delete:10 % %',OLD.osm_type,OLD.osm_id;{% endif %}

  DELETE FROM place_addressline where place_id = OLD.place_id;

  {% if debug %}RAISE WARNING 'placex_delete:11 % %',OLD.osm_type,OLD.osm_id;{% endif %}

  -- remove from tables for special search
  classtable := 'place_classtype_' || OLD.class || '_' || OLD.type;
  SELECT count(*)>0 FROM pg_tables WHERE tablename = classtable and schemaname = current_schema() INTO b;
  IF b THEN
    EXECUTE 'DELETE FROM ' || classtable::regclass || ' WHERE place_id = $1' USING OLD.place_id;
  END IF;

  {% if debug %}RAISE WARNING 'placex_delete:12 % %',OLD.osm_type,OLD.osm_id;{% endif %}

  RETURN OLD;

END;
$$
LANGUAGE plpgsql;
