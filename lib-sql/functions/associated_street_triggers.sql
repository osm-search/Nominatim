-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- Trigger functions for associated street relations.


-- Invalidates house members of associatedStreet relations
-- whenever the place_associated_street table is modified.
-- osm2pgsql flex handles updates as DELETE-all + re-INSERT, so each
-- row-level trigger call covers exactly one member.
CREATE OR REPLACE FUNCTION invalidate_associated_street_members()
  RETURNS TRIGGER
  AS $$
DECLARE
  object RECORD;
BEGIN
  IF TG_OP = 'DELETE' THEN
    object := OLD;
  ELSE
    object := NEW;
  END IF;

  IF object.member_role = 'house' THEN
    {% for otype in ('N', 'W', 'R') %}
    IF object.member_type = '{{ otype }}' THEN
      UPDATE placex SET indexed_status = 2
       WHERE osm_type = '{{ otype }}'
         AND osm_id = object.member_id
         AND indexed_status = 0;
    END IF;
    {% endfor %}
  END IF;

  RETURN object;
END;
$$
LANGUAGE plpgsql;
