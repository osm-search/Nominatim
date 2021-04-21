"""
Tokenizer implementing normalisation as used before Nominatim 4.
"""
from nominatim.db.connection import connect
from nominatim.db import properties

DBCFG_NORMALIZATION = "tokenizer_normalization"

def create(dsn, data_dir):
    """ Create a new instance of the tokenizer provided by this module.
    """
    return LegacyTokenizer(dsn, data_dir)

class LegacyTokenizer:
    """ The legacy tokenizer uses a special PostgreSQL module to normalize
        names and queries. The tokenizer thus implements normalization through
        calls to the database.
    """

    def __init__(self, dsn, data_dir):
        self.dsn = dsn
        self.data_dir = data_dir
        self.normalization = None


    def init_new_db(self, config):
        """ Set up a new tokenizer for the database.

            This copies all necessary data in the project directory to make
            sure the tokenizer remains stable even over updates.
        """
        self.normalization = config.TERM_NORMALIZATION

        # Stable configuration is saved in the database.
        with connect(self.dsn) as conn:
            properties.set_property(conn, DBCFG_NORMALIZATION,
                                    self.normalization)


    def init_from_project(self):
        """ Initialise the tokenizer from the project directory.
        """
        with connect(self.dsn) as conn:
            self.normalization = properties.get_property(conn, DBCFG_NORMALIZATION)
