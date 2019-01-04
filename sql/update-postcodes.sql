-- Create a temporary table with postcodes from placex.

CREATE TEMP TABLE tmp_new_postcode_locations AS
SELECT country_code,
       upper(trim (both ' ' from address->'postcode')) as pc,
       ST_Centroid(ST_Collect(ST_Centroid(geometry))) as centroid
  FROM placex
 WHERE address ? 'postcode'
       AND address->'postcode' NOT SIMILAR TO '%(,|;)%'
       AND geometry IS NOT null
GROUP BY country_code, pc;

CREATE INDEX idx_tmp_new_postcode_locations
          ON tmp_new_postcode_locations (pc, country_code);

-- add extra US postcodes
INSERT INTO tmp_new_postcode_locations (country_code, pc, centroid)
    SELECT 'us', postcode, ST_SetSRID(ST_Point(x,y),4326)
      FROM us_postcode u
      WHERE NOT EXISTS (SELECT 0 FROM tmp_new_postcode_locations new
                         WHERE new.country_code = 'us' AND new.pc = u.postcode);
-- add extra UK postcodes
INSERT INTO tmp_new_postcode_locations (country_code, pc, centroid)
    SELECT 'gb', postcode, geometry FROM gb_postcode g
     WHERE NOT EXISTS (SELECT 0 FROM tmp_new_postcode_locations new
                             WHERE new.country_code = 'gb' and new.pc = g.postcode);

-- Remove all postcodes that are no longer valid
DELETE FROM location_postcode old
  WHERE NOT EXISTS(SELECT 0 FROM tmp_new_postcode_locations new
                   WHERE old.postcode = new.pc
                         AND old.country_code = new.country_code);

-- Update geometries where necessary
UPDATE location_postcode old SET geometry = new.centroid, indexed_status = 1
  FROM tmp_new_postcode_locations new
 WHERE old.postcode = new.pc AND old.country_code = new.country_code
       AND ST_AsText(old.geometry) != ST_AsText(new.centroid);

-- Remove all postcodes that already exist from the temporary table
DELETE FROM tmp_new_postcode_locations new
    WHERE EXISTS(SELECT 0 FROM location_postcode old
                 WHERE old.postcode = new.pc AND old.country_code = new.country_code);

-- Add newly added postcode
INSERT INTO location_postcode
  (place_id, indexed_status, country_code, postcode, geometry)
  SELECT nextval('seq_place'), 1, country_code, pc, centroid
    FROM tmp_new_postcode_locations new;

-- Remove unused word entries
DELETE FROM word
    WHERE class = 'place' AND type = 'postcode'
          AND NOT EXISTS (SELECT 0 FROM location_postcode p
                          WHERE p.postcode = word.word);

-- Finally index the newly inserted postcodes
UPDATE location_postcode SET indexed_status = 0 WHERE indexed_status > 0;
