# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
import pytest

@pytest.fixture
def osm2pgsql_options(temp_db, tmp_path):
    """ A standard set of options for osm2pgsql
        together with a osm2pgsql mock that just reflects the command line.
    """
    osm2pgsql_exec = tmp_path / 'osm2pgsql_mock'

    osm2pgsql_exec.write_text("""#!/bin/sh

if [ "$*" = "--version" ]; then
  >&2 echo "2024-08-09 11:16:23  osm2pgsql version 11.7.2 (11.7.2)"
else
  echo "$@"
fi
    """)
    osm2pgsql_exec.chmod(0o777)

    return dict(osm2pgsql=str(osm2pgsql_exec),
                osm2pgsql_cache=10,
                osm2pgsql_style='style.file',
                threads=1,
                dsn='dbname=' + temp_db,
                flatnode_file='',
                tablespaces=dict(slim_data='', slim_index='',
                                 main_data='', main_index=''))
