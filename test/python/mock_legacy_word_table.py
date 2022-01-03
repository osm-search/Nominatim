# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Legacy word table for testing with functions to prefil and test contents
of the table.
"""

class MockLegacyWordTable:
    """ A word table for testing using legacy word table structure.
    """
    def __init__(self, conn):
        self.conn = conn
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE word (word_id INTEGER,
                                              word_token text,
                                              word text,
                                              class text,
                                              type text,
                                              country_code varchar(2),
                                              search_name_count INTEGER,
                                              operator TEXT)""")

        conn.commit()

    def add_full_word(self, word_id, word, word_token=None):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_id, word_token, word)
                           VALUES (%s, %s, %s)
                        """, (word_id, ' ' + (word_token or word), word))
        self.conn.commit()


    def add_special(self, word_token, word, cls, typ, oper):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_token, word, class, type, operator)
                              VALUES (%s, %s, %s, %s, %s)
                        """, (word_token, word, cls, typ, oper))
        self.conn.commit()


    def add_country(self, country_code, word_token):
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO word (word_token, country_code) VALUES(%s, %s)",
                        (word_token, country_code))
        self.conn.commit()


    def add_postcode(self, word_token, postcode):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_token, word, class, type)
                              VALUES (%s, %s, 'place', 'postcode')
                        """, (word_token, postcode))
        self.conn.commit()


    def count(self):
        with self.conn.cursor() as cur:
            return cur.scalar("SELECT count(*) FROM word")


    def count_special(self):
        with self.conn.cursor() as cur:
            return cur.scalar("SELECT count(*) FROM word WHERE class != 'place'")


    def get_special(self):
        with self.conn.cursor() as cur:
            cur.execute("""SELECT word_token, word, class, type, operator
                           FROM word WHERE class != 'place'""")
            result = set((tuple(row) for row in cur))
            assert len(result) == cur.rowcount, "Word table has duplicates."
            return result


    def get_country(self):
        with self.conn.cursor() as cur:
            cur.execute("""SELECT country_code, word_token
                           FROM word WHERE country_code is not null""")
            result = set((tuple(row) for row in cur))
            assert len(result) == cur.rowcount, "Word table has duplicates."
            return result


    def get_postcodes(self):
        with self.conn.cursor() as cur:
            cur.execute("""SELECT word FROM word
                           WHERE class = 'place' and type = 'postcode'""")
            return set((row[0] for row in cur))

    def get_partial_words(self):
        with self.conn.cursor() as cur:
            cur.execute("""SELECT word_token, search_name_count FROM word
                           WHERE class is null and country_code is null
                                 and not word_token like ' %'""")
            return set((tuple(row) for row in cur))

