-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

DROP TABLE IF EXISTS location_property_tiger;
CREATE TABLE location_property_tiger (
  place_id BIGINT NOT NULL,
  parent_place_id BIGINT,
  startnumber INTEGER NOT NULL,
  endnumber INTEGER NOT NULL,
  step SMALLINT NOT NULL,
  partition SMALLINT NOT NULL,
  linegeo GEOMETRY NOT NULL,
  postcode TEXT);
