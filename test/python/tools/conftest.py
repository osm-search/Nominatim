import pytest

@pytest.fixture
def osm2pgsql_options(temp_db):
    """ A standard set of options for osm2pgsql.
    """
    return dict(osm2pgsql='echo',
                osm2pgsql_cache=10,
                osm2pgsql_style='style.file',
                threads=1,
                dsn='dbname=' + temp_db,
                flatnode_file='',
                tablespaces=dict(slim_data='', slim_index='',
                                 main_data='', main_index=''))
