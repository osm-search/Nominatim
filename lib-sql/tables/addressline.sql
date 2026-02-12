-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

DROP TABLE IF EXISTS place_addressline;

CREATE TABLE place_addressline (
  place_id BIGINT NOT NULL,
  address_place_id BIGINT NOT NULL,
  distance FLOAT NOT NULL,
  cached_rank_address SMALLINT NOT NULL,
  fromarea boolean NOT NULL,
  isaddress boolean NOT NULL
  ) {{db.tablespace.search_data}};

CREATE INDEX idx_place_addressline_place_id ON place_addressline
  USING BTREE (place_id) {{db.tablespace.search_index}};
