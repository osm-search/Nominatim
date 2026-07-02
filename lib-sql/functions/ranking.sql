-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- Functions related to search and address ranks

-- Check if a place is rankable at all.
-- These really should be dropped at the lua level eventually.
CREATE OR REPLACE FUNCTION is_rankable_place(osm_type TEXT, categories ltree[],
                                             admin_level SMALLINT, name HSTORE,
                                             extratags HSTORE, is_area BOOLEAN)
  RETURNS BOOLEAN
  AS $$
DECLARE
  cat ltree;
  cat_class TEXT;
BEGIN
  IF categories IS NULL THEN
    RETURN TRUE;
  END IF;
  FOREACH cat IN ARRAY categories LOOP
    -- Only check osm.* categories
    IF cat ~ 'osm.*'::lquery THEN
      cat_class := split_part(cat::text, '.', 2);

      -- Check unnamed highway area
      IF cat_class = 'highway' AND is_area AND name IS NULL
         AND extratags ? 'area' AND extratags->'area' = 'yes'
      THEN
        CONTINUE;
      END IF;

      -- Check non-area boundary
      IF cat_class = 'boundary' THEN
        IF NOT is_area
           OR (admin_level <= 4 AND osm_type = 'W')
        THEN
          CONTINUE;
        END IF;
      END IF;

      RETURN TRUE;
    END IF;
  END LOOP;

  RETURN FALSE;
END;
$$
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;


-- Return an approximate search radius according to the search rank.
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
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;


-- Return an approximate update radius according to the search rank.
CREATE OR REPLACE FUNCTION update_place_diameter(rank_search SMALLINT)
  RETURNS FLOAT
  AS $$
BEGIN
  -- postcodes
  IF rank_search = 11 or rank_search = 5 THEN
    RETURN 0.05;
  -- anything higher than city is effectively ignored (polygon required)
  ELSIF rank_search < 16 THEN
    RETURN 0;
  ELSIF rank_search < 18 THEN
    RETURN 0.1;
  ELSIF rank_search < 20 THEN
    RETURN 0.05;
  ELSIF rank_search = 21 THEN
    RETURN 0.001;
  ELSIF rank_search < 24 THEN
    RETURN 0.02;
  ELSIF rank_search < 26 THEN
    RETURN 0.002;
  ELSIF rank_search < 28 THEN
    RETURN 0.001;
  END IF;

  RETURN 0;
END;
$$
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;

-- Compute a base address rank from the extent of the given geometry.
--
-- This is all simple guess work. We don't need particularly good estimates
-- here. This just avoids to have very high ranked address parts in features
-- that span very large areas (or vice versa).
CREATE OR REPLACE FUNCTION geometry_to_rank(search_rank SMALLINT, geometry GEOMETRY, country_code TEXT)
  RETURNS SMALLINT
  AS $$
DECLARE
  area FLOAT;
BEGIN
  IF ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') THEN
      area := ST_Area(geometry);
  ELSIF ST_GeometryType(geometry) in ('ST_LineString','ST_MultiLineString') THEN
      area := (ST_Length(geometry)^2) * 0.1;
  ELSE
    RETURN search_rank;
  END IF;

  -- adjust for the fact that countries come in different sizes
  IF country_code IN ('ca', 'au', 'ru') THEN
    area := area / 5;
  ELSIF country_code IN ('br', 'kz', 'cn', 'us', 'ne', 'gb', 'za', 'sa', 'id', 'eh', 'ml', 'tm') THEN
    area := area / 3;
  ELSIF country_code IN ('bo', 'ar', 'sd', 'mn', 'in', 'et', 'cd', 'mz', 'ly', 'cl', 'zm') THEN
    area := area / 2;
  ELSIF country_code IN ('sg', 'ws', 'st', 'kn') THEN
    area := area * 5;
  ELSIF country_code IN ('dm', 'mt', 'lc', 'gg', 'sc', 'nr') THEN
    area := area * 20;
  END IF;

  IF area > 1 THEN
    RETURN 7;
  ELSIF area > 0.1 THEN
    RETURN 9;
  ELSIF area > 0.01 THEN
    RETURN 13;
  ELSIF area > 0.001 THEN
    RETURN 17;
  ELSIF area > 0.0001 THEN
    RETURN 19;
  ELSIF area > 0.000005 THEN
    RETURN 21;
  END IF;

   RETURN 23;
END;
$$
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;


-- Get standard search and address rank for an object.
-- Iterates all osm.* categories and finds the one with the lowest positive
-- address rank. Address rank of 0 has the lowest priority. Ties broken by
-- lower search rank.
--
-- \param country        Two-letter country code where the object is in.
-- \param extended_type  OSM type (N, W, R) or area type (A).
-- \param categories     ltree[] of osm.<class>.<type> categories.
-- \param admin_level    Value of admin_level tag.
-- \param is_major       If true, boost search rank by one.
-- \param postcode       Value of addr:postcode tag.
-- \param[out] search_rank   Computed search rank.
-- \param[out] address_rank  Computed address rank.
--
CREATE OR REPLACE FUNCTION compute_place_rank(country VARCHAR(2),
                                              extended_type VARCHAR(1),
                                              categories ltree[],
                                              admin_level SMALLINT,
                                              is_major BOOLEAN,
                                              postcode TEXT,
                                              OUT search_rank SMALLINT,
                                              OUT address_rank SMALLINT)
AS $$
DECLARE
  cat ltree;
  cat_class TEXT;
  cat_type TEXT;
  classtype TEXT;
  best_search SMALLINT := 99;
  best_address SMALLINT := 99;
  cand_search SMALLINT;
  cand_address SMALLINT;
  has_boundary_admin BOOLEAN;
BEGIN
  IF categories IS NULL THEN
    search_rank := 30;
    address_rank := 30;
    RETURN;
  END IF;

  -- Hoist: skip place categories when boundary/administrative is also present.
  has_boundary_admin := categories <@ 'osm.boundary.administrative';

  FOREACH cat IN ARRAY categories LOOP
    -- Only consider osm.* categories
    IF NOT (cat ~ 'osm.*'::lquery) THEN
      CONTINUE;
    END IF;

    -- Place ranks are handled by the post-hoc adjustment in placex_update.
    IF has_boundary_admin AND cat ~ 'osm.place.*'::lquery THEN
      CONTINUE;
    END IF;

    cat_class := split_part(cat::text, '.', 2);
    cat_type := split_part(cat::text, '.', 3);
    -- Short-circuits for special cases
    IF extended_type = 'N' AND cat_class = 'highway' THEN
      cand_search := 30;
      cand_address := 30;
    ELSIF cat_class = 'landuse' AND extended_type != 'A' THEN
      cand_search := 30;
      cand_address := 30;
    ELSE
      -- Build classtype for boundary/administrative
      IF cat_class = 'boundary' AND cat_type = 'administrative' THEN
        classtype := cat_type || admin_level::TEXT;
      ELSE
        classtype := cat_type;
      END IF;

      SELECT l.rank_search, l.rank_address INTO cand_search, cand_address
        FROM address_levels l
       WHERE (l.country_code = country OR l.country_code IS NULL)
             AND l.class = cat_class AND (l.type = classtype OR l.type IS NULL)
       ORDER BY l.country_code, l.class, l.type LIMIT 1;

      IF cand_search IS NULL OR cand_address IS NULL THEN
        cand_search := 30;
        cand_address := 30;
      END IF;

      -- Waterway relation boost
      IF cat_class = 'waterway' AND extended_type = 'R' THEN
        cand_search := cand_search - 1;
      END IF;
    END IF;

    -- Selection: pick the candidate with lowest positive address rank.
    -- Address rank of 0 has lowest priority (fallback only). Tiebreak: lower search rank.
    -- A positive address rank always overrides a zero-address fallback (best_address = 0).
    IF cand_address > 0 AND (best_address = 0 OR cand_address < best_address) THEN
      best_search := cand_search;
      best_address := cand_address;
    ELSIF cand_address > 0 AND cand_address = best_address
          AND cand_search < best_search THEN
      best_search := cand_search;
      best_address := cand_address;
    ELSIF cand_address = 0 AND (best_address = 99 OR best_address = 0)
          AND cand_search < best_search THEN
      -- Fallback: when no addressable category found, pick best search rank
      best_search := cand_search;
      best_address := cand_address;
    END IF;
  END LOOP;

  -- Apply is_major boost to the winner
  IF is_major THEN
    best_search := best_search - 1;
  END IF;

  search_rank := best_search;
  address_rank := best_address;
END;
$$
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION get_addr_tag_rank(key TEXT, country TEXT,
                                             OUT from_rank SMALLINT,
                                             OUT to_rank SMALLINT,
                                             OUT extent FLOAT)
  AS $$
DECLARE
  ranks RECORD;
BEGIN
  from_rank := null;

  FOR ranks IN
    SELECT * FROM
      (SELECT l.rank_search, l.rank_address FROM address_levels l
        WHERE (l.country_code = country or l.country_code is NULL)
               AND l.class = 'place' AND l.type = key
        ORDER BY l.country_code LIMIT 1) r
      WHERE rank_address > 0
  LOOP
    extent := reverse_place_diameter(ranks.rank_search);

    IF ranks.rank_address <= 4 THEN
        from_rank := 4;
        to_rank := 4;
    ELSEIF ranks.rank_address <= 9 THEN
        from_rank := 5;
        to_rank := 9;
    ELSEIF ranks.rank_address <= 12 THEN
        from_rank := 10;
        to_rank := 12;
    ELSEIF ranks.rank_address <= 16 THEN
        from_rank := 13;
        to_rank := 16;
    ELSEIF ranks.rank_address <= 21 THEN
        from_rank := 17;
        to_rank := 21;
    ELSEIF ranks.rank_address <= 24 THEN
        from_rank := 22;
        to_rank := 24;
    ELSE
        from_rank := 25;
        to_rank := 25;
    END IF;
  END LOOP;
END;
$$
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;


CREATE OR REPLACE FUNCTION weigh_search(search_vector INT[],
                                        rankings TEXT,
                                        def_weight FLOAT)
  RETURNS FLOAT
  AS $$
DECLARE
  rank JSON;
BEGIN
  FOR rank IN
    SELECT * FROM json_array_elements(rankings::JSON)
  LOOP
    IF true = ALL(SELECT x::int = ANY(search_vector) FROM json_array_elements_text(rank->1) as x) THEN
      RETURN (rank->>0)::float;
    END IF;
  END LOOP;
  RETURN def_weight;
END;
$$
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;
