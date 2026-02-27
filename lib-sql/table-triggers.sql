-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

-- insert creates the location tables, creates location indexes if indexed == true
CREATE TRIGGER placex_before_insert BEFORE INSERT ON placex
    FOR EACH ROW EXECUTE PROCEDURE placex_insert();
CREATE TRIGGER osmline_before_insert BEFORE INSERT ON location_property_osmline
    FOR EACH ROW EXECUTE PROCEDURE osmline_insert();

-- update insert creates the location tables
CREATE TRIGGER placex_before_update BEFORE UPDATE ON placex
    FOR EACH ROW EXECUTE PROCEDURE placex_update();
CREATE TRIGGER osmline_before_update BEFORE UPDATE ON location_property_osmline
    FOR EACH ROW EXECUTE PROCEDURE osmline_update();

-- diff update triggers
CREATE TRIGGER placex_before_delete AFTER DELETE ON placex
    FOR EACH ROW EXECUTE PROCEDURE placex_delete();
CREATE TRIGGER place_before_delete BEFORE DELETE ON place
    FOR EACH ROW EXECUTE PROCEDURE place_delete();
CREATE TRIGGER place_before_insert BEFORE INSERT ON place
    FOR EACH ROW EXECUTE PROCEDURE place_insert();

CREATE TRIGGER location_postcode_before_update BEFORE UPDATE ON location_postcodes
    FOR EACH ROW EXECUTE PROCEDURE postcodes_update();
CREATE TRIGGER location_postcodes_before_delete BEFORE DELETE ON location_postcodes
    FOR EACH ROW EXECUTE PROCEDURE postcodes_delete();
CREATE TRIGGER location_postcodes_before_insert BEFORE INSERT ON location_postcodes
    FOR EACH ROW EXECUTE PROCEDURE postcodes_insert();

CREATE TRIGGER place_interpolation_before_insert BEFORE INSERT ON place_interpolation
    FOR EACH ROW EXECUTE PROCEDURE place_interpolation_insert();
CREATE TRIGGER place_interpolation_before_delete BEFORE DELETE ON place_interpolation
    FOR EACH ROW EXECUTE PROCEDURE place_interpolation_delete();

-- Trigger to propagate changes to associatedStreet relations to house members
-- so that the indexer re-computes their parent_place_id.
{% if db.middle_db_format != '1' %}
CREATE TRIGGER planet_osm_rels_associated_street_update
    AFTER INSERT OR UPDATE OR DELETE ON planet_osm_rels
    FOR EACH ROW EXECUTE FUNCTION invalidate_associated_street_members();
{% endif %}
