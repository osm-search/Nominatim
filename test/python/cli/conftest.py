import pytest

import nominatim.cli

@pytest.fixture
def cli_call(src_dir):
    """ Call the nominatim main function with the correct paths set.
        Returns a function that can be called with the desired CLI arguments.
    """
    def _call_nominatim(*args):
        return nominatim.cli.nominatim(module_dir='MODULE NOT AVAILABLE',
                                       osm2pgsql_path='OSM2PGSQL NOT AVAILABLE',
                                       phplib_dir=str(src_dir / 'lib-php'),
                                       data_dir=str(src_dir / 'data'),
                                       phpcgi_path='/usr/bin/php-cgi',
                                       sqllib_dir=str(src_dir / 'lib-sql'),
                                       config_dir=str(src_dir / 'settings'),
                                       cli_args=args)

    return _call_nominatim

