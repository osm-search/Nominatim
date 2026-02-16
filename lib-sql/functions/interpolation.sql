-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- Functions for address interpolation objects in location_property_osmline.

CREATE OR REPLACE FUNCTION place_interpolation_insert()
  RETURNS TRIGGER
  AS $$
DECLARE
  existing RECORD;
  existingplacex BIGINT[];

BEGIN
  -- Remove the place from the list of places to be deleted
  DELETE FROM place_interpolation_to_be_deleted pdel
    WHERE pdel.osm_type = NEW.osm_type and pdel.osm_id = NEW.osm_id;

  SELECT * INTO existing FROM place_interpolation p
    WHERE p.osm_type = NEW.osm_type AND p.osm_id = NEW.osm_id;

  IF NOT (NEW.type in ('odd', 'even', 'all') OR NEW.type similar to '[1-9]') THEN
    -- the new interpolation is illegal, simply remove existing entries
    DELETE FROM location_property_osmline o
      WHERE o.osm_type = NEW.osm_type AND o.osm_id = NEW.osm_id;
  ELSE
    -- Get the existing entry from the interpolation table.
    SELECT array_agg(place_id) INTO existingplacex
      FROM location_property_osmline o
      WHERE o.osm_type = NEW.osm_type AND o.osm_id = NEW.osm_id;

    IF array_length(existingplacex, 1) is NULL THEN
      INSERT INTO location_property_osmline (osm_type, osm_id, type, address, linegeo)
        VALUES (NEW.osm_type, NEW.osm_id, NEW.type, NEW.address, NEW.geometry);
    ELSE
      -- Update the interpolation table:
      --   The first entry gets the original data, all other entries
      --   are removed and will be recreated on indexing.
      --   (An interpolation can be split up, if it has more than 2 address nodes)
      -- Update unconditionally here as the changes might be coming from the
      -- nodes on the interpolation.
      UPDATE location_property_osmline
        SET type = NEW.type,
            address = NEW.address,
            linegeo = NEW.geometry,
            startnumber = null,
            indexed_status = 1
        WHERE place_id = existingplacex[1];
      IF array_length(existingplacex, 1) > 1 THEN
        DELETE FROM location_property_osmline
          WHERE place_id = any(existingplacex[2:]);
      END IF;
    END IF;

    -- need to invalidate nodes because they might copy address info
    IF NEW.address is not NULL
       AND (existing.osm_type is NULL
            OR coalesce(existing.address, ''::hstore) != NEW.address)
    THEN
      UPDATE placex SET indexed_status = 2
        WHERE osm_type = 'N' AND osm_id = ANY(NEW.nodes)
              AND indexed_status = 0;
    END IF;
  END IF;

  -- finally update/insert place_interpolation itself

  IF existing.osm_type is not NULL THEN
    IF existing.type != NEW.type
       OR coalesce(existing.address, ''::hstore) != coalesce(NEW.address, ''::hstore)
       OR existing.geometry::text != NEW.geometry::text
    THEN
      UPDATE place_interpolation p
        SET type = NEW.type,
            address = NEW.address,
            geometry = NEW.geometry
        WHERE p.osm_type = NEW.osm_type AND p.osm_id = NEW.osm_id;
    END IF;

    RETURN NULL;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION place_interpolation_delete()
  RETURNS TRIGGER
  AS $$
DECLARE
  deferred BOOLEAN;
BEGIN
  {% if debug %}RAISE WARNING 'Delete for % % %/%', OLD.osm_type, OLD.osm_id, OLD.class, OLD.type;{% endif %}

  INSERT INTO place_interpolation_to_be_deleted (osm_type, osm_id)
    VALUES(OLD.osm_type, OLD.osm_id);

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_interpolation_address(in_address HSTORE, wayid BIGINT)
RETURNS HSTORE
  AS $$
DECLARE
  location RECORD;
  waynodes BIGINT[];
BEGIN
  IF in_address ? 'street' or in_address ? 'place' THEN
    RETURN in_address;
  END IF;

  SELECT nodes INTO waynodes FROM planet_osm_ways WHERE id = wayid;
  FOR location IN
    SELECT placex.address, placex.osm_id FROM placex
     WHERE osm_type = 'N' and osm_id = ANY(waynodes)
           and placex.address is not null
           and (placex.address ? 'street' or placex.address ? 'place')
           and indexed_status < 100
  LOOP
    -- mark it as a derived address
    RETURN location.address || coalesce(in_address, '{}'::hstore) || hstore('_inherited', '');
  END LOOP;

  RETURN in_address;
END;
$$
LANGUAGE plpgsql STABLE PARALLEL SAFE;



-- find the parent road of the cut road parts
CREATE OR REPLACE FUNCTION get_interpolation_parent(token_info JSONB,
                                                    partition SMALLINT,
                                                    centroid GEOMETRY, geom GEOMETRY)
  RETURNS BIGINT
  AS $$
DECLARE
  parent_place_id BIGINT;
  location RECORD;
BEGIN
  parent_place_id := find_parent_for_address(token_info, partition, centroid);

  IF parent_place_id is null THEN
    FOR location IN SELECT place_id FROM placex
        WHERE ST_DWithin(geom, placex.geometry, 0.001)
              and placex.rank_search = 26
              and placex.osm_type = 'W' -- needed for index selection
        ORDER BY CASE WHEN ST_GeometryType(geom) = 'ST_Line' THEN
                  (ST_distance(placex.geometry, ST_LineInterpolatePoint(geom,0))+
                  ST_distance(placex.geometry, ST_LineInterpolatePoint(geom,0.5))+
                  ST_distance(placex.geometry, ST_LineInterpolatePoint(geom,1)))
                 ELSE ST_distance(placex.geometry, geom) END
              ASC
        LIMIT 1
    LOOP
      parent_place_id := location.place_id;
    END LOOP;
  END IF;

  RETURN parent_place_id;
END;
$$
LANGUAGE plpgsql STABLE PARALLEL SAFE;


CREATE OR REPLACE FUNCTION osmline_insert()
  RETURNS TRIGGER
  AS $$
DECLARE
  centroid GEOMETRY;
BEGIN
  NEW.place_id := nextval('seq_place');
  NEW.indexed_date := now();

  IF NEW.indexed_status IS NULL THEN
    IF NOT(NEW.type in ('odd', 'even', 'all') OR NEW.type similar to '[1-9]') THEN
        -- alphabetic interpolation is not supported
        RETURN NULL;
    END IF;

    IF NEW.address is not NULL AND NEW.address ? 'housenumber' THEN
      IF NEW.address->'housenumber' not similar to '[0-9]+-[0-9]+' THEN
          -- housenumber needs to look like an interpolation
          RETURN NULL;
      END IF;

      centroid := ST_Centroid(NEW.linegeo);
      -- interpolation of a housenumber, make sure we have a line to interpolate on
      NEW.geometry := ST_MakeLine(centroid, ST_Project(centroid, 0.0000001, 0));
    ELSE
      centroid := get_center_point(NEW.linegeo);
      IF NEW.osm_type != 'W' THEN
        RETURN NULL;
      END IF;
    END IF;

    NEW.indexed_status := 1; --STATUS_NEW
    NEW.country_code := lower(get_country_code(centroid));

    NEW.partition := get_partition(NEW.country_code);
    NEW.geometry_sector := geometry_sector(NEW.partition, centroid);
  END IF;

  RETURN NEW;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION osmline_update()
  RETURNS TRIGGER
  AS $$
DECLARE
  waynodes BIGINT[];
  prevnode RECORD;
  nextnode RECORD;
  startnumber INTEGER;
  endnumber INTEGER;
  newstart INTEGER;
  newend INTEGER;
  moddiff SMALLINT;
  linegeo GEOMETRY;
  splitpoint FLOAT;
  sectiongeo GEOMETRY;
  postcode TEXT;
  stepmod SMALLINT;
  splitstring TEXT[];
BEGIN
  -- deferred delete
  IF OLD.indexed_status = 100 THEN
    delete from location_property_osmline where place_id = OLD.place_id;
    RETURN NULL;
  END IF;

  IF NEW.indexed_status != 0 OR OLD.indexed_status = 0 THEN
    RETURN NEW;
  END IF;

  NEW.parent_place_id := get_interpolation_parent(NEW.token_info, NEW.partition,
                                                  get_center_point(NEW.linegeo),
                                                  NEW.linegeo);

  NEW.token_info := token_strip_info(NEW.token_info);
  IF NEW.address ? '_inherited' THEN
    NEW.address := NULL;
  END IF;

  -- If the line was newly inserted, split the line as necessary.
  IF NEW.parent_place_id is not NULL AND NEW.startnumber is NULL THEN
    IF NEW.type in ('odd', 'even') THEN
      NEW.step := 2;
      stepmod := CASE WHEN NEW.type = 'odd' THEN 1 ELSE 0 END;
    ELSE
      NEW.step := CASE WHEN NEW.type = 'all' THEN 1 ELSE (NEW.type)::SMALLINT END;
      stepmod := NULL;
    END IF;

    IF NEW.address is not NULL AND NEW.address ? 'housenumer' THEN
      -- interpolation interval is in housenumber
      splitstring := string_to_array(NEW.address->'housenumber', '-');
      NEW.startnumber := (splitstring[1])::INTEGER;
      NEW.endnumber := (splitstring[2])::INTEGER;

      IF stepmod is not NULL THEN
        IF NEW.startnumber % NEW.step != stepmod THEN
          NEW.startnumber := NEW.startnumber + 1;
        END IF;
        IF NEW.endnumber % NEW.step != stepmod THEN
          NEW.endnumber := NEW.endnumber - 1;
        END IF;
      ELSE
        NEW.endnumber := NEW.startnumber + ((NEW.endnumber - NEW.startnumber) / NEW.step) * NEW.step;
      END IF;

      IF NEW.startnumber = NEW.endnumber THEN
        NEW.geometry := ST_PointN(NEW.geometry, 1);
      ELSEIF NEW.startnumber > NEW.endnumber THEN
        NEW.startnumber := NULL;
      END IF;
    ELSE
      -- classic interpolation way
      SELECT nodes INTO waynodes
        FROM planet_osm_ways WHERE id = NEW.osm_id;

      IF array_upper(waynodes, 1) IS NULL THEN
        RETURN NEW;
      END IF;

      linegeo := null;
      SELECT null::integer as hnr INTO prevnode;

      -- Go through all nodes on the interpolation line that have a housenumber.
      FOR nextnode IN
        SELECT DISTINCT ON (nodeidpos)
            osm_id, address, geometry,
            -- Take the postcode from the node only if it has a housenumber itself.
            -- Note that there is a corner-case where the node has a wrongly
            -- formatted postcode and therefore 'postcode' contains a derived
            -- variant.
            CASE WHEN address ? 'postcode' THEN placex.postcode ELSE NULL::text END as postcode,
            (address->'housenumber')::integer as hnr
          FROM placex, generate_series(1, array_upper(waynodes, 1)) nodeidpos
          WHERE osm_type = 'N' and osm_id = waynodes[nodeidpos]::BIGINT
                and address is not NULL and address ? 'housenumber'
                and address->'housenumber' ~ '^[0-9]{1,6}$'
                and ST_Distance(NEW.linegeo, geometry) < 0.0005
          ORDER BY nodeidpos
      LOOP
        {% if debug %}RAISE WARNING 'processing point % (%)', nextnode.hnr, ST_AsText(nextnode.geometry);{% endif %}
        IF linegeo is null THEN
          linegeo := NEW.linegeo;
        ELSE
          splitpoint := ST_LineLocatePoint(linegeo, nextnode.geometry);
          IF splitpoint = 0 THEN
            -- Corner case where the splitpoint falls on the first point
            -- and thus would not return a geometry. Skip that section.
            sectiongeo := NULL;
          ELSEIF splitpoint = 1 THEN
            -- Point is at the end of the line.
            sectiongeo := linegeo;
            linegeo := NULL;
          ELSE
            -- Split the line.
            sectiongeo := ST_LineSubstring(linegeo, 0, splitpoint);
            linegeo := ST_LineSubstring(linegeo, splitpoint, 1);
          END IF;
        END IF;

        IF prevnode.hnr is not null
           -- Check if there are housenumbers to interpolate between the
           -- regularly mapped housenumbers.
           -- (Conveniently also fails if one of the house numbers is not a number.)
           and abs(prevnode.hnr - nextnode.hnr) > NEW.step
           -- If the interpolation geometry is broken or two nodes are at the
           -- same place, then splitting might produce a point. Ignore that.
           and ST_GeometryType(sectiongeo) = 'ST_LineString'
        THEN
          IF prevnode.hnr < nextnode.hnr THEN
            startnumber := prevnode.hnr;
            endnumber := nextnode.hnr;
          ELSE
            startnumber := nextnode.hnr;
            endnumber := prevnode.hnr;
            sectiongeo := ST_Reverse(sectiongeo);
          END IF;

          -- Adjust the interpolation, so that only inner housenumbers
          -- are taken into account.
          IF stepmod is null THEN
            newstart := startnumber + NEW.step;
          ELSE
            newstart := startnumber + 1;
            moddiff := newstart % NEW.step - stepmod;
            IF moddiff < 0 THEN
              newstart := newstart + (NEW.step + moddiff);
            ELSE
              newstart := newstart + moddiff;
            END IF;
          END IF;
          newend := newstart + ((endnumber - 1 - newstart) / NEW.step) * NEW.step;

          -- If newstart and newend are the same, then this returns a point.
          sectiongeo := ST_LineSubstring(sectiongeo,
                                (newstart - startnumber)::float / (endnumber - startnumber)::float,
                                (newend - startnumber)::float / (endnumber - startnumber)::float);
          startnumber := newstart;
          endnumber := newend;

          -- determine postcode
          postcode := coalesce(prevnode.postcode, nextnode.postcode, postcode);
          IF postcode is NULL and NEW.parent_place_id > 0 THEN
              SELECT placex.postcode FROM placex
                WHERE place_id = NEW.parent_place_id INTO postcode;
          END IF;
          IF postcode is NULL THEN
              postcode := get_nearest_postcode(NEW.country_code, nextnode.geometry);
          END IF;

          -- Add the interpolation. If this is the first segment, just modify
          -- the interpolation to be inserted, otherwise add an additional one
          -- (marking it indexed already).
          IF NEW.startnumber IS NULL THEN
              NEW.startnumber := startnumber;
              NEW.endnumber := endnumber;
              NEW.linegeo := ST_ReducePrecision(sectiongeo, 0.0000001);
              NEW.postcode := postcode;
          ELSE
            INSERT INTO location_property_osmline
                   (linegeo, partition, osm_type, osm_id, parent_place_id,
                    startnumber, endnumber, step, type,
                    address, postcode, country_code,
                    geometry_sector, indexed_status)
            VALUES (ST_ReducePrecision(sectiongeo, 0.0000001),
                    NEW.partition, NEW.osm_type, NEW.osm_id, NEW.parent_place_id,
                    startnumber, endnumber, NEW.step, NEW.type,
                    NEW.address, postcode,
                    NEW.country_code, NEW.geometry_sector, 0);
          END IF;
        END IF;

        -- early break if we are out of line string,
        -- might happen when a line string loops back on itself
        IF linegeo is null or ST_GeometryType(linegeo) != 'ST_LineString' THEN
            RETURN NEW;
        END IF;

        prevnode := nextnode;
      END LOOP;
    END IF;
  END IF;

  RETURN NEW;
END;
$$
LANGUAGE plpgsql;
