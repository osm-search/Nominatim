-- Functions related to search and address ranks

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
LANGUAGE plpgsql IMMUTABLE;


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
LANGUAGE plpgsql IMMUTABLE;


-- Guess a ranking for postcodes from country and postcode format.
CREATE OR REPLACE FUNCTION get_postcode_rank(country_code VARCHAR(2), postcode TEXT,
                                             OUT rank_search SMALLINT,
                                             OUT rank_address SMALLINT)
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


-- Get standard search and address rank for an object.
--
-- \param country        Two-letter country code where the object is in.
-- \param extended_type  OSM type (N, W, R) or area type (A).
-- \param place_class    Class (or tag key) of object.
-- \param place_type     Type (or tag value) of object.
-- \param admin_level    Value of admin_level tag.
-- \param is_major       If true, boost search rank by one.
-- \param postcode       Value of addr:postcode tag.
-- \param[out] search_rank   Computed search rank.
-- \param[out] address_rank  Computed address rank.
--
CREATE OR REPLACE FUNCTION compute_place_rank(country VARCHAR(2),
                                              extended_type VARCHAR(1),
                                              place_class TEXT, place_type TEXT,
                                              admin_level SMALLINT,
                                              is_major BOOLEAN,
                                              postcode TEXT,
                                              OUT search_rank SMALLINT,
                                              OUT address_rank SMALLINT)
AS $$
DECLARE
  classtype TEXT;
BEGIN
  IF place_class in ('place','boundary')
     and place_type in ('postcode','postal_code')
  THEN
    SELECT * INTO search_rank, address_rank
      FROM get_postcode_rank(country, postcode);
  ELSEIF extended_type = 'N' AND place_class = 'highway' THEN
    search_rank = 30;
    address_rank = 0;
  ELSEIF place_class = 'landuse' AND extended_type != 'A' THEN
    search_rank = 30;
    address_rank = 0;
  ELSE
    IF place_class = 'boundary' and place_type = 'administrative' THEN
      classtype = place_type || admin_level::TEXT;
    ELSE
      classtype = place_type;
    END IF;

    SELECT l.rank_search, l.rank_address INTO search_rank, address_rank
      FROM address_levels l
     WHERE (l.country_code = country or l.country_code is NULL)
           AND l.class = place_class AND (l.type = classtype or l.type is NULL)
     ORDER BY l.country_code, l.class, l.type LIMIT 1;

    IF search_rank is NULL THEN
      search_rank := 30;
    END IF;

    IF address_rank is NULL THEN
      address_rank := 30;
    END IF;

    -- some postcorrections
    IF place_class = 'waterway' AND extended_type = 'R' THEN
        -- Slightly promote waterway relations so that they are processed
        -- before their members.
        search_rank := search_rank - 1;
    END IF;

    IF is_major THEN
      search_rank := search_rank - 1;
    END IF;
  END IF;
END;
$$
LANGUAGE plpgsql IMMUTABLE;
