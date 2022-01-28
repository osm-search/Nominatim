-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
-- For a full list of authors see the git log.

CREATE OR REPLACE FUNCTION place_insert()
  RETURNS TRIGGER
  AS $$
DECLARE
  i INTEGER;
  country RECORD;
  existing RECORD;
  existingplacex RECORD;
  existingline BIGINT[];
  interpol RECORD;
BEGIN
  {% if debug %}
    RAISE WARNING 'place_insert: % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,st_area(NEW.geometry);
  {% endif %}

  -- Filter tuples with bad geometries.
  IF ST_IsEmpty(NEW.geometry) OR NOT ST_IsValid(NEW.geometry) THEN
    INSERT INTO import_polygon_error (osm_type, osm_id, class, type, name,
                                      country_code, updated, errormessage,
                                      prevgeometry, newgeometry)
      VALUES (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name,
              NEW.address->'country', now(), ST_IsValidReason(NEW.geometry),
              null, NEW.geometry);
    {% if debug %}
      RAISE WARNING 'Invalid Geometry: % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type;
    {% endif %}
    RETURN null;
  END IF;

  -- Have we already done this place?
  SELECT * INTO existing
    FROM place
    WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
          and class = NEW.class and type = NEW.type;

  {% if debug %}RAISE WARNING 'Existing: %',existing.osm_id;{% endif %}

  -- Handle a place changing type by removing the old data.
  -- (This trigger is executed BEFORE INSERT of the NEW tuple.)
  IF existing.osm_type IS NULL THEN
    DELETE FROM place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class;
  END IF;

  -- Remove any old logged data.
  DELETE from import_polygon_error where osm_type = NEW.osm_type and osm_id = NEW.osm_id;
  DELETE from import_polygon_delete where osm_type = NEW.osm_type and osm_id = NEW.osm_id;

  -- ---- Interpolation Lines

  IF NEW.class='place' and NEW.type='houses'
     and NEW.osm_type='W' and ST_GeometryType(NEW.geometry) = 'ST_LineString'
  THEN
    PERFORM reinsert_interpolation(NEW.osm_id, NEW.address, NEW.geometry);

    -- Now invalidate all address nodes on the line.
    -- They get their parent from the interpolation.
    UPDATE placex p SET indexed_status = 2
      FROM planet_osm_ways w
      WHERE w.id = NEW.osm_id and p.osm_type = 'N' and p.osm_id = any(w.nodes);

    -- If there is already an entry in place, just update that, if necessary.
    IF existing.osm_type is not null THEN
      IF coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
         OR existing.geometry::text != NEW.geometry::text
      THEN
        UPDATE place
          SET name = NEW.name,
              address = NEW.address,
              extratags = NEW.extratags,
              admin_level = NEW.admin_level,
              geometry = NEW.geometry
          WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
                and class = NEW.class and type = NEW.type;
       END IF;

       RETURN NULL;
    END IF;

    RETURN NEW;
  END IF;

  -- ---- Postcode points.

  IF NEW.class = 'place' AND NEW.type = 'postcode' THEN
    -- Pure postcodes are never queried from placex so we don't add them.
    -- location_postcodes is filled from the place table directly.

    -- Remove any old placex entry.
    DELETE FROM placex WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id;

    IF existing.osm_type IS NOT NULL THEN
      IF coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
         OR existing.geometry::text != NEW.geometry::text
      THEN
        UPDATE place
          SET name = NEW.name,
              address = NEW.address,
              extratags = NEW.extratags,
              admin_level = NEW.admin_level,
              geometry = NEW.geometry
          WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
                and class = NEW.class and type = NEW.type;
      END IF;

      RETURN NULL;
    END IF;

    RETURN NEW;
  END IF;

  -- ---- All other place types.

  -- Patch in additional country names
  IF NEW.admin_level = 2 and NEW.type = 'administrative' and NEW.address ? 'country'
  THEN
    FOR country IN
      SELECT name FROM country_name WHERE country_code = lower(NEW.address->'country')
    LOOP
      NEW.name = country.name || NEW.name;
    END LOOP;
  END IF;

  -- When an area is changed from large to small: log and discard change
  IF existing.geometry is not null AND ST_IsValid(existing.geometry)
    AND ST_Area(existing.geometry) > 0.02
    AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon')
    AND ST_Area(NEW.geometry) < ST_Area(existing.geometry) * 0.5
  THEN
    INSERT INTO import_polygon_error (osm_type, osm_id, class, type, name,
                                      country_code, updated, errormessage,
                                      prevgeometry, newgeometry)
      VALUES (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name,
              NEW.address->'country', now(),
              'Area reduced from '||st_area(existing.geometry)||' to '||st_area(NEW.geometry),
              existing.geometry, NEW.geometry);

    RETURN null;
  END IF;

  -- If an address node is part of a interpolation line and changes or is
  -- newly inserted (happens when the node already existed but now gets address
  -- information), then mark the interpolation line for reparenting.
  -- (Already here, because interpolation lines are reindexed before nodes,
  --  so in the second call it would be too late.)
  IF NEW.osm_type='N'
     and coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
  THEN
      FOR interpol IN
        SELECT DISTINCT osm_id, address, geometry FROM place, planet_osm_ways w
        WHERE NEW.geometry && place.geometry
              and place.osm_type = 'W'
              and exists (SELECT * FROM location_property_osmline
                          WHERE osm_id = place.osm_id
                                and indexed_status in (0, 2))
              and w.id = place.osm_id and NEW.osm_id = any (w.nodes)
      LOOP
        PERFORM reinsert_interpolation(interpol.osm_id, interpol.address,
                                       interpol.geometry);
      END LOOP;
  END IF;

  -- Get the existing placex entry.
  SELECT * INTO existingplacex
    FROM placex
    WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
          and class = NEW.class and type = NEW.type;

  {% if debug %}RAISE WARNING 'Existing PlaceX: %',existingplacex.place_id;{% endif %}

  -- To paraphrase: if there isn't an existing item, OR if the admin level has changed
  IF existingplacex.osm_type IS NULL
     or (existingplacex.class = 'boundary'
         and ((coalesce(existingplacex.admin_level, 15) != coalesce(NEW.admin_level, 15)
               and existingplacex.type = 'administrative')
              or existingplacex.type != NEW.type))
  THEN
    {% if config.get_bool('LIMIT_REINDEXING') %}
    -- sanity check: ignore admin_level changes on places with too many active children
    -- or we end up reindexing entire countries because somebody accidentally deleted admin_level
    IF existingplacex.osm_type IS NOT NULL THEN
      SELECT count(*) INTO i FROM
        (SELECT 'a' FROM placex, place_addressline
          WHERE address_place_id = existingplacex.place_id
                and placex.place_id = place_addressline.place_id
                and indexed_status = 0 and place_addressline.isaddress LIMIT 100001) sub;
      IF i > 100000 THEN
        RETURN null;
      END IF;
    END IF;
    {% endif %}

    IF existing.osm_type IS NOT NULL THEN
      -- Pathological case caused by the triggerless copy into place during initial import
      -- force delete even for large areas, it will be reinserted later
      UPDATE place SET geometry = ST_SetSRID(ST_Point(0,0), 4326)
        WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
              and class = NEW.class and type = NEW.type;
      DELETE FROM place
        WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
              and class = NEW.class and type = NEW.type;
    END IF;

    -- Process it as a new insertion
    INSERT INTO placex (osm_type, osm_id, class, type, name,
                        admin_level, address, extratags, geometry)
      VALUES (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name,
              NEW.admin_level, NEW.address, NEW.extratags, NEW.geometry);

    {% if debug %}RAISE WARNING 'insert done % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,NEW.name;{% endif %}

    RETURN NEW;
  END IF;

  -- Special case for polygon shape changes because they tend to be large
  -- and we can be a bit clever about how we handle them
  IF existing.geometry::text != NEW.geometry::text
     AND ST_GeometryType(existing.geometry) in ('ST_Polygon','ST_MultiPolygon')
     AND ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon')
  THEN
    -- Performance limit
    IF ST_Area(NEW.geometry) < 0.000000001 AND ST_Area(existingplacex.geometry) < 1
    THEN
      -- re-index points that have moved in / out of the polygon.
      -- Could be done as a single query but postgres gets the index usage wrong.
      update placex set indexed_status = 2 where indexed_status = 0
          AND ST_Intersects(NEW.geometry, placex.geometry)
          AND NOT ST_Intersects(existingplacex.geometry, placex.geometry)
          AND rank_search > existingplacex.rank_search AND (rank_search < 28 or name is not null);

      update placex set indexed_status = 2 where indexed_status = 0
          AND ST_Intersects(existingplacex.geometry, placex.geometry)
          AND NOT ST_Intersects(NEW.geometry, placex.geometry)
          AND rank_search > existingplacex.rank_search AND (rank_search < 28 or name is not null);
    END IF;
  END IF;


  -- Has something relevant changed?
  IF coalesce(existing.name::text, '') != coalesce(NEW.name::text, '')
     OR coalesce(existing.extratags::text, '') != coalesce(NEW.extratags::text, '')
     OR coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
     OR coalesce(existing.admin_level, 15) != coalesce(NEW.admin_level, 15)
     OR existing.geometry::text != NEW.geometry::text
  THEN
    UPDATE place
      SET name = NEW.name,
          address = NEW.address,
          extratags = NEW.extratags,
          admin_level = NEW.admin_level,
          geometry = NEW.geometry
      WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
            and class = NEW.class and type = NEW.type;

    -- Postcode areas are only kept, when there is an actual postcode assigned.
    IF NEW.class = 'boundary' AND NEW.type = 'postal_code' THEN
      IF NEW.address is NULL OR NOT NEW.address ? 'postcode' THEN
        -- postcode was deleted, no longer retain in placex
        DELETE FROM placex where place_id = existingplacex.place_id;
        RETURN NULL;
      END IF;

      NEW.name := hstore('ref', NEW.address->'postcode');
    END IF;

    -- Boundaries must be areas.
    IF NEW.class in ('boundary')
       AND ST_GeometryType(NEW.geometry) not in ('ST_Polygon','ST_MultiPolygon')
    THEN
      DELETE FROM placex where place_id = existingplacex.place_id;
      RETURN NULL;
    END IF;

    -- Update the placex entry in-place.
    UPDATE placex
      SET name = NEW.name,
          address = NEW.address,
          parent_place_id = null,
          extratags = NEW.extratags,
          admin_level = NEW.admin_level,
          indexed_status = 2,
          geometry = NEW.geometry
      WHERE place_id = existingplacex.place_id;

    -- Invalidate linked places: they potentially get a new name and addresses.
    IF existingplacex.linked_place_id is not NULL THEN
      UPDATE placex x
        SET name = p.name,
            extratags = p.extratags,
            indexed_status = 2
        FROM place p
        WHERE x.place_id = existingplacex.linked_place_id
              and x.indexed_status = 0
              and x.osm_type = p.osm_type
              and x.osm_id = p.osm_id
              and x.class = p.class;
    END IF;

    -- Invalidate dependent objects effected by name changes
    IF coalesce(existing.name::text, '') != coalesce(NEW.name::text, '')
    THEN
      IF existingplacex.rank_address between 26 and 27 THEN
        -- When streets change their name, this may have an effect on POI objects
        -- with addr:street tags.
        UPDATE placex SET indexed_status = 2
          WHERE indexed_status = 0 and address ? 'street'
                and parent_place_id = existingplacex.place_id;
        UPDATE placex SET indexed_status = 2
          WHERE indexed_status = 0 and rank_search = 30 and address ? 'street'
                and ST_DWithin(NEW.geometry, geometry, 0.002);
      ELSEIF existingplacex.rank_address between 16 and 25 THEN
        -- When places change their name, this may have an effect on POI objects
        -- with addr:place tags.
        UPDATE placex SET indexed_status = 2
          WHERE indexed_status = 0 and address ? 'place' and rank_search = 30
                and parent_place_id = existingplacex.place_id;
        -- No update of surrounding objects, potentially too expensive.
      END IF;
    END IF;
  END IF;

  -- Abort the insertion (we modified the existing place instead)
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION place_delete()
  RETURNS TRIGGER
  AS $$
DECLARE
  has_rank BOOLEAN;
BEGIN

  {% if debug %}RAISE WARNING 'delete: % % % %',OLD.osm_type,OLD.osm_id,OLD.class,OLD.type;{% endif %}

  -- deleting large polygons can have a massive effect on the system - require manual intervention to let them through
  IF st_area(OLD.geometry) > 2 and st_isvalid(OLD.geometry) THEN
    SELECT bool_or(not (rank_address = 0 or rank_address > 25)) as ranked FROM placex WHERE osm_type = OLD.osm_type and osm_id = OLD.osm_id and class = OLD.class and type = OLD.type INTO has_rank;
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

