"""
Tokenizer for testing.
"""

def create(dsn, data_dir):
    """ Create a new instance of the tokenizer provided by this module.
    """
    return DummyTokenizer(dsn, data_dir)

class DummyTokenizer:

    def __init__(self, dsn, data_dir):
        self.dsn = dsn
        self.data_dir = data_dir
        self.init_state = None


    def init_new_db(self, config):
        assert self.init_state == None
        self.init_state = "new"


    def init_from_project(self):
        assert self.init_state == None
        self.init_state = "loaded"


    def name_analyzer(self):
        return DummyNameAnalyzer()


class DummyNameAnalyzer:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def close(self):
        """ Free all resources used by the analyzer.
        """
        pass

    def process_place(self, place):
        """ Determine tokenizer information about the given place.

            Returns a JSON-serialisable structure that will be handed into
            the database via the token_info field.
        """
        return {}
