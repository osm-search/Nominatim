-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2022 by the Nominatim developer community.
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

CREATE TRIGGER location_postcode_before_update BEFORE UPDATE ON location_postcode
    FOR EACH ROW EXECUTE PROCEDURE postcode_update();
