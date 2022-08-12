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

class MockIcuWordTable:
    """ A word table for testing using legacy word table structure.
    """
    def __init__(self, conn):
        self.conn = conn
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE word (word_id INTEGER,
                                              word_token text NOT NULL,
                                              type text NOT NULL,
                                              word text,
                                              info jsonb)""")

        conn.commit()

    def add_full_word(self, word_id, word, word_token=None):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_id, word_token, type, word, info)
                           VALUES(%s, %s, 'W', %s, '{}'::jsonb)""",
                        (word_id, word or word_token, word))
        self.conn.commit()


    def add_special(self, word_token, word, cls, typ, oper):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_token, type, word, info)
                              VALUES (%s, 'S', %s,
                                      json_build_object('class', %s,
                                                        'type', %s,
                                                        'op', %s))
                        """, (word_token, word, cls, typ, oper))
        self.conn.commit()


    def add_country(self, country_code, word_token):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_token, type, word)
                           VALUES(%s, 'C', %s)""",
                        (word_token, country_code))
        self.conn.commit()


    def add_postcode(self, word_token, postcode):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO word (word_token, type, word)
                              VALUES (%s, 'P', %s)
                        """, (word_token, postcode))
        self.conn.commit()


    def add_housenumber(self, word_id, word_tokens, word=None):
        with self.conn.cursor() as cur:
            if isinstance(word_tokens, str):
                # old style without analyser
                cur.execute("""INSERT INTO word (word_id, word_token, type)
                                  VALUES (%s, %s, 'H')
                            """, (word_id, word_tokens))
            else:
                if word is None:
                    word = word_tokens[0]
                for token in word_tokens:
                    cur.execute("""INSERT INTO word (word_id, word_token, type, word, info)
                                      VALUES (%s, %s, 'H', %s, jsonb_build_object('lookup', %s))
                                """, (word_id, token, word, word_tokens[0]))

        self.conn.commit()


    def count(self):
        with self.conn.cursor() as cur:
            return cur.scalar("SELECT count(*) FROM word")


    def count_special(self):
        with self.conn.cursor() as cur:
            return cur.scalar("SELECT count(*) FROM word WHERE type = 'S'")


    def count_housenumbers(self):
        with self.conn.cursor() as cur:
            return cur.scalar("SELECT count(*) FROM word WHERE type = 'H'")


    def get_special(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT word_token, info, word FROM word WHERE type = 'S'")
            result = set(((row[0], row[2], row[1]['class'],
                           row[1]['type'], row[1]['op']) for row in cur))
            assert len(result) == cur.rowcount, "Word table has duplicates."
            return result


    def get_country(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT word, word_token FROM word WHERE type = 'C'")
            result = set((tuple(row) for row in cur))
            assert len(result) == cur.rowcount, "Word table has duplicates."
            return result


    def get_postcodes(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT word FROM word WHERE type = 'P'")
            return set((row[0] for row in cur))


    def get_partial_words(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT word_token, info FROM word WHERE type ='w'")
            return set(((row[0], row[1]['count']) for row in cur))

