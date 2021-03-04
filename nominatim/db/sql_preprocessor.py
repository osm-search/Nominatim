"""
Preprocessing of SQL files.
"""
import jinja2


def _get_partitions(conn):
    """ Get the set of partitions currently in use.
    """
    with conn.cursor() as cur:
        cur.execute('SELECT DISTINCT partition FROM country_name')
        partitions = set([0])
        for row in cur:
            partitions.add(row[0])

    return partitions


def _get_tables(conn):
    """ Return the set of tables currently in use.
        Only includes non-partitioned
    """
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")

        return set((row[0] for row in list(cur)))


def _setup_tablespace_sql(config):
    """ Returns a dict with tablespace expressions for the different tablespace
        kinds depending on whether a tablespace is configured or not.
    """
    out = {}
    for subset in ('ADDRESS', 'SEARCH', 'AUX'):
        for kind in ('DATA', 'INDEX'):
            tspace = getattr(config, 'TABLESPACE_{}_{}'.format(subset, kind))
            if tspace:
                tspace = 'TABLESPACE "{}"'.format(tspace)
            out['{}_{}'.format(subset.lower, kind.lower())] = tspace

    return out


def _setup_postgres_sql(conn):
    """ Set up a dictionary with various Postgresql/Postgis SQL terms which
        are dependent on the database version in use.
    """
    out = {}
    pg_version = conn.server_version_tuple()
    # CREATE INDEX IF NOT EXISTS was introduced in PG9.5.
    # Note that you need to ignore failures on older versions when
    # unsing this construct.
    out['if_index_not_exists'] = ' IF NOT EXISTS ' if pg_version >= (9, 5, 0) else ''

    return out


class SQLPreprocessor: # pylint: disable=too-few-public-methods
    """ A environment for preprocessing SQL files from the
        lib-sql directory.

        The preprocessor provides a number of default filters and variables.
        The variables may be overwritten when rendering an SQL file.

        The preprocessing is currently based on the jinja2 templating library
        and follows its syntax.
    """

    def __init__(self, conn, config, sqllib_dir):
        self.env = jinja2.Environment(autoescape=False,
                                      loader=jinja2.FileSystemLoader(str(sqllib_dir)))

        db_info = {}
        db_info['partitions'] = _get_partitions(conn)
        db_info['tables'] = _get_tables(conn)
        db_info['reverse_only'] = 'search_name' not in db_info['tables']
        db_info['tablespace'] = _setup_tablespace_sql(config)

        self.env.globals['config'] = config
        self.env.globals['db'] = db_info
        self.env.globals['sql'] = _setup_postgres_sql(conn)
        self.env.globals['modulepath'] = config.DATABASE_MODULE_PATH or \
                                         str((config.project_dir / 'module').resolve())


    def run_sql_file(self, conn, name, **kwargs):
        """ Execute the given SQL file on the connection. The keyword arguments
            may supply additional parameters for preprocessing.
        """
        sql = self.env.get_template(name).render(**kwargs)

        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
