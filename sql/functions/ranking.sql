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
