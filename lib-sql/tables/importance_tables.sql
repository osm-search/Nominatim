-- SPDX-License-Identifier: GPL-2.0-only
--
-- This file is part of Nominatim. (https://nominatim.org)
--
-- Copyright (C) 2026 by the Nominatim developer community.
-- For a full list of authors see the git log.

{% if 'wikimedia_importance' not in db.tables and 'wikipedia_article' not in db.tables %}
-- create dummy tables here if nothing was imported
CREATE TABLE wikimedia_importance (
  language TEXT NOT NULL,
  title TEXT NOT NULL,
  importance double precision NOT NULL,
  wikidata TEXT
)  {{db.tablespace.address_data}};
{% endif %}
