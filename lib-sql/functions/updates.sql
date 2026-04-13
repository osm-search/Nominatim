-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.
 
-- Helper functions for updates.

-- Invalidate all placex affected by inserting a new place into the placex table.
CREATE OR REPLACE FUNCTION update_invalidate_for_new_place(address_rank SMALLINT,
                                                           is_area BOOLEAN, area_size FLOAT,
                                                           otype TEXT, newgeom GEOMETRY)
  RETURNS BOOLEAN
  AS $$
DECLARE
  diameter FLOAT;
BEGIN
  diameter := update_place_diameter(address_rank);
  is_area := COALESCE(is_area, ST_GeometryType(newgeom) in ('ST_Polygon','ST_MultiPolygon'));
  -- Update dependencies for address parts.
  -- Leaving countries out here because a newly inserted country is
  -- more likely incorrect mapping.
  IF address_rank BETWEEN 4 AND 25 THEN
    IF is_area THEN
      IF COALESCE(area_size, ST_Area(newgeom)) <= 2.0 THEN
        UPDATE placex SET indexed_status = 2
          WHERE ST_Intersects(newgeom, placex.geometry)
            AND indexed_status = 0
            AND ((rank_address = 0 and rank_search > address_rank)
                 or rank_address > address_rank
                 or (osm_type = 'N' and rank_address between 4 and 25))
            AND (rank_search < 28 or name is not null);
      END IF;
    ELSEIF otype = 'N' THEN
      IF diameter > 0 THEN
        UPDATE placex SET indexed_status = 2
          WHERE ST_DWithin(newgeom, placex.geometry, diameter)
            AND indexed_status = 0
            AND ((rank_address = 0 and rank_search > address_rank)
                 or rank_address > address_rank
                 or (osm_type = 'N' and rank_address between 4 and 25))
            AND (rank_search < 28 or name is not null);
      END IF;
    END IF;
    -- Addressable places may cause reparenting of addr:place-based addresses.
    IF address_rank BETWEEN 16 AND 25 THEN
      UPDATE placex SET indexed_status = 2
        WHERE indexed_status = 0
          AND rank_search > 27
          AND address ? 'place'
          AND ST_DWithin(newgeom, placex.geometry, diameter);
    END IF;
  END IF;
  -- Roads may cause reparenting for POI places
  IF address_rank BETWEEN 26 AND 27 THEN
    UPDATE placex SET indexed_status = 2
      WHERE indexed_status = 0
        AND rank_search > 27
        AND ST_DWithin(newgeom, placex.geometry, diameter);
    UPDATE location_property_osmline SET indexed_status = 2
      WHERE indexed_status = 0
        AND startnumber is not null
        AND ST_DWithin(newgeom, linegeo, diameter);
  END IF;

  RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
