"""
Legacy word table for testing with functions to prefil and test contents
of the table.
"""

class MockIcuWordTable:
    """ A word table for testing using legacy word table structure.
    """
    def __init__(self, conn):
        self.conn = conn
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE word (word_id INTEGER,
                                              word_token text NOT NULL,
                                              type text NOT NULL,
                                              info jsonb)""")

        conn.commit()

    def add_special(self, word_token, word, cls, typ, oper):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_token, type, info)
                              VALUES (%s, 'S',
                                      json_build_object('word', %s,
                                                        'class', %s,
                                                        'type', %s,
                                                        'op', %s))
                        """, (word_token, word, cls, typ, oper))
        self.conn.commit()


    def add_country(self, country_code, word_token):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_token, type, info)
                           VALUES(%s, 'C', json_build_object('cc', %s))""",
                        (word_token, country_code))
        self.conn.commit()


    def add_postcode(self, word_token, postcode):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_token, type, info)
                              VALUES (%s, 'P', json_build_object('postcode', %s))
                        """, (word_token, postcode))
        self.conn.commit()


    def count(self):
        with self.conn.cursor() as cur:
            return cur.scalar("SELECT count(*) FROM word")


    def count_special(self):
        with self.conn.cursor() as cur:
            return cur.scalar("SELECT count(*) FROM word WHERE type = 'S'")


    def get_special(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT word_token, info FROM word WHERE type = 'S'")
            result = set(((row[0], row[1]['word'], row[1]['class'],
                           row[1]['type'], row[1]['op']) for row in cur))
            assert len(result) == cur.rowcount, "Word table has duplicates."
            return result


    def get_country(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT info->>'cc', word_token FROM word WHERE type = 'C'")
            result = set((tuple(row) for row in cur))
            assert len(result) == cur.rowcount, "Word table has duplicates."
            return result


    def get_postcodes(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT info->>'postcode' FROM word WHERE type = 'P'")
            return set((row[0] for row in cur))


    def get_partial_words(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT word_token, info FROM word WHERE type ='w'")
            return set(((row[0], row[1]['count']) for row in cur))

