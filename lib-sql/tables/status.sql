-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

DROP TABLE IF EXISTS import_status;
CREATE TABLE import_status (
  lastimportdate TIMESTAMP WITH TIME ZONE NOT NULL,
  sequence_id INTEGER,
  indexed BOOLEAN
  );

DROP TABLE IF EXISTS import_osmosis_log;
CREATE TABLE import_osmosis_log (
  batchend TIMESTAMP,
  batchseq INTEGER,
  batchsize BIGINT,
  starttime TIMESTAMP,
  endtime TIMESTAMP,
  event TEXT
  );
