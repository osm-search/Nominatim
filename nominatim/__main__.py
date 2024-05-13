if __name__ == '__main__':
    from nominatim import cli

    exit(cli.nominatim(module_dir=None, osm2pgsql_path=None))
