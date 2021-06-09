CREATE OR REPLACE FUNCTION place_insert()
  RETURNS TRIGGER
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

  {% if debug %}
    RAISE WARNING '-----------------------------------------------------------------------------------';
    RAISE WARNING 'place_insert: % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,st_area(NEW.geometry);
  {% endif %}
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

    -- Pure postcodes are never queried from placex so we don't add them.
    -- location_postcodes is filled from the place table directly.
    IF NEW.class = 'place' AND NEW.type = 'postcode' THEN
      -- Remove old placex entry if the type changed to postcode.
      IF existingplacex.type IS NOT NULL AND existingplacex.type != 'postcode' THEN
        DELETE FROM placex where osm_type = NEW.osm_type and osm_id = NEW.osm_id;
      END IF;
      RETURN NEW;
    END IF;

    -- Handle a place changing type by removing the old data
    -- My generated 'place' types are causing havok because they overlap with real keys
    -- TODO: move them to their own special purpose key/class to avoid collisions
    IF existing.osm_type IS NULL THEN
      DELETE FROM place where osm_type = NEW.osm_type and osm_id = NEW.osm_id and class = NEW.class;
    END IF;

    {% if debug %}RAISE WARNING 'Existing: %',existing.osm_id;{% endif %}
    {% if debug %}RAISE WARNING 'Existing PlaceX: %',existingplacex.place_id;{% endif %}

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

      {% if config.get_bool('LIMIT_REINDEXING') %}
      IF existingplacex.osm_type IS NOT NULL THEN
        -- sanity check: ignore admin_level changes on places with too many active children
        -- or we end up reindexing entire countries because somebody accidentally deleted admin_level
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

      {% if debug %}RAISE WARNING 'insert done % % % % %',NEW.osm_type,NEW.osm_id,NEW.class,NEW.type,NEW.name;{% endif %}

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
        update placex set indexed_status = 2 where indexed_status = 0
            AND ST_Intersects(NEW.geometry, placex.geometry)
            AND NOT ST_Intersects(existinggeometry, placex.geometry)
            AND rank_search > existingplacex.rank_search AND (rank_search < 28 or name is not null);

        update placex set indexed_status = 2 where indexed_status = 0
            AND ST_Intersects(existinggeometry, placex.geometry)
            AND NOT ST_Intersects(NEW.geometry, placex.geometry)
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


      IF NEW.class = 'boundary' AND NEW.type = 'postal_code' THEN
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
      IF NEW.osm_type='N'
         and (coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
             or existing.geometry::text != NEW.geometry::text)
      THEN
          result:= osmline_reinsert(NEW.osm_id, NEW.geometry);
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

