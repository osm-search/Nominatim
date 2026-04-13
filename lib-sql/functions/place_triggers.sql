-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

CREATE OR REPLACE FUNCTION place_insert()
  RETURNS TRIGGER
  AS $$
DECLARE
  existing RECORD;
  existingplacex RECORD;
  newplacex RECORD;
  is_area BOOLEAN;
  existing_is_area BOOLEAN;
  area_size FLOAT;
  address_rank SMALLINT;
  search_rank SMALLINT;
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

  -- Remove the place from the list of places to be deleted
  DELETE FROM place_to_be_deleted pdel
    WHERE pdel.osm_type = NEW.osm_type and pdel.osm_id = NEW.osm_id
          and pdel.class = NEW.class and pdel.type = NEW.type;

  -- Have we already done this place?
  SELECT * INTO existing
    FROM place
    WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
          and class = NEW.class and type = NEW.type;

  {% if debug %}RAISE WARNING 'Existing: %',existing.osm_id;{% endif %}

  IF existing.osm_type IS NULL THEN
    DELETE FROM place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class;
  END IF;

  -- Remove any old logged data.
  DELETE from import_polygon_error where osm_type = NEW.osm_type and osm_id = NEW.osm_id;
  DELETE from import_polygon_delete where osm_type = NEW.osm_type and osm_id = NEW.osm_id;

  is_area := ST_GeometryType(NEW.geometry) in ('ST_Polygon','ST_MultiPolygon');
  IF is_area THEN
    area_size = ST_Area(NEW.geometry);
  END IF;

  -- When an area is changed from large to small: log and discard change
  IF existing.geometry is not null AND ST_IsValid(existing.geometry)
    AND ST_Area(existing.geometry) > 0.02
    AND is_area AND area_size < ST_Area(existing.geometry) * 0.5
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

  -- Get the existing placex entry.
  SELECT * INTO existingplacex
    FROM placex
    WHERE osm_type = NEW.osm_type and osm_id = NEW.osm_id
          and class = NEW.class and type = NEW.type;

  {% if debug %}RAISE WARNING 'Existing PlaceX: %',existingplacex.place_id;{% endif %}

  IF existingplacex.osm_type IS NULL THEN
    -- Inserting a new placex.
    FOR newplacex IN
      INSERT INTO placex (osm_type, osm_id, class, type, name,
                        admin_level, address, extratags, geometry)
      VALUES (NEW.osm_type, NEW.osm_id, NEW.class, NEW.type, NEW.name,
              NEW.admin_level, NEW.address, NEW.extratags, NEW.geometry)
      RETURNING rank_address
    LOOP
      PERFORM update_invalidate_for_new_place(newplacex.rank_address,
                                              is_area, area_size,
                                              NEW.osm_Type, NEW.geometry);
    END LOOP;
  ELSE
    -- Modify an existing placex.
    IF is_rankable_place(NEW.osm_type, NEW.class, NEW.admin_level,
                         NEW.name, NEW.extratags, is_area)
    THEN
      -- Recompute the ranks to look out for changes.
      -- We use the old country assignment here which is good enough for the
      -- purpose.
      SELECT * INTO search_rank, address_rank
        FROM compute_place_rank(existingplacex.country_code,
                                CASE WHEN is_area THEN 'A' ELSE NEW.osm_type END,
                                NEW.class, NEW.type, NEW.admin_level,
                                (NEW.extratags->'capital') = 'yes',
                                NEW.address->'postcode');

      existing_is_area := ST_GeometryType(existingplacex.geometry) in ('ST_Polygon','ST_MultiPolygon');

      IF (address_rank BETWEEN 4 and 27
          AND (existingplacex.rank_address <= 0 OR existingplacex.rank_address > 27))
         OR (not existing_is_area and is_area)
      THEN
        -- object newly relevant for addressing, invalidate new version
        PERFORM update_invalidate_for_new_place(address_rank,
                                                is_area, area_size,
                                                NEW.osm_type, NEW.geometry);
      ELSEIF (existingplacex.rank_address BETWEEN 4 and 27
              AND (address_rank <= 0 OR address_rank > 27))
             OR (existing_is_area and not is_area)
      THEN
        -- object no longer relevant for addressing, invalidate old version
        PERFORM update_invalidate_for_new_place(existingplacex.rank_address,
                                                existing_is_area, null,
                                                existingplacex.osm_type,
                                                existingplacex.geometry);
      ELSEIF address_rank BETWEEN 4 and 27 THEN
        IF coalesce(existing.name, ''::hstore) != coalesce(NEW.name, ''::hstore)
           OR existing.admin_level != NEW.admin_level
        THEN
          -- Name changes may have an effect on searchable objects and parenting
          -- for new and old areas.
          PERFORM update_invalidate_for_new_place(address_rank, is_area, null,
                                                  NEW.osm_type,
                                                  CASE WHEN is_area and existing_is_area
                                                    THEN ST_Union(NEW.geometry, existingplacex.geometry)
                                                    ELSE ST_Collect(NEW.geometry, existingplacex.geometry)
                                                  END);
        ELSEIF existingplacex.geometry::text != NEW.geometry::text THEN
            -- Geometry change, just invalidate the changed areas.
            -- Changes of other geometry types are currently ignored.
          IF is_area and existing_is_area THEN
            PERFORM update_invalidate_for_new_place(address_rank, true, null,
                                                    NEW.osm_type,
                                                    ST_SymDifference(existingplacex.geometry,
                                                                     NEW.geometry));
          END IF;
        END IF;
      END IF;

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

      -- update placex in place
      UPDATE placex
        SET name = NEW.name,
            address = NEW.address,
            parent_place_id = null,
            extratags = NEW.extratags,
            admin_level = NEW.admin_level,
            rank_address = address_rank,
            rank_search = search_rank,
            indexed_status = 2,
            geometry = CASE WHEN address_rank = 0
                            THEN simplify_large_polygons(NEW.geometry)
                            ELSE NEW.geometry END
        WHERE place_id = existingplacex.place_id;
    ELSE
      -- New place is not really valid, remove the placex entry
      UPDATE placex SET indexed_status = 100 WHERE place_id = existingplacex.place_id;
    END IF;

    -- When an existing way is updated, recalculate entrances
    IF existingplacex.osm_type = 'W' and (existingplacex.rank_search > 27 or existingplacex.class IN ('landuse', 'leisure')) THEN
      PERFORM place_update_entrances(existingplacex.place_id, existingplacex.osm_id);
    END IF;
  END IF;

  -- Finally update place itself.
  IF existing.osm_type is not NULL THEN
    -- If there is already an entry in place, just update that, if necessary.
    IF coalesce(existing.name, ''::hstore) != coalesce(NEW.name, ''::hstore)
       or coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
       or coalesce(existing.extratags, ''::hstore) != coalesce(NEW.extratags, ''::hstore)
       or coalesce(existing.admin_level, 15) != coalesce(NEW.admin_level, 15)
       or existing.geometry::text != NEW.geometry::text
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
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION place_delete()
  RETURNS TRIGGER
  AS $$
DECLARE
  deferred BOOLEAN;
BEGIN
  {% if debug %}RAISE WARNING 'Delete for % % %/%', OLD.osm_type, OLD.osm_id, OLD.class, OLD.type;{% endif %}

  deferred := ST_IsValid(OLD.geometry) and ST_Area(OLD.geometry) > 2;
  IF deferred THEN
    SELECT bool_or(not (rank_address = 0 or rank_address > 25)) INTO deferred
      FROM placex
      WHERE osm_type = OLD.osm_type and osm_id = OLD.osm_id
            and class = OLD.class and type = OLD.type;
  END IF;

  INSERT INTO place_to_be_deleted (osm_type, osm_id, class, type, deferred)
    VALUES(OLD.osm_type, OLD.osm_id, OLD.class, OLD.type, deferred);

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;
