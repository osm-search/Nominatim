"""
Functions for importing, updating and otherwise maintaining the table
of artificial postcode centroids.
"""

from nominatim.db.utils import execute_file
from nominatim.db.connection import connect

def import_postcodes(dsn, project_dir):
    """ Set up the initial list of postcodes.
    """

    with connect(dsn) as conn:
        conn.drop_table('gb_postcode')
        conn.drop_table('us_postcode')

        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE gb_postcode (
                            id integer,
                            postcode character varying(9),
                            geometry GEOMETRY(Point, 4326))""")

        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE us_postcode (
                            postcode text,
                            x double precision,
                            y double precision)""")
        conn.commit()

        gb_postcodes = project_dir / 'gb_postcode_data.sql.gz'
        if gb_postcodes.is_file():
            execute_file(dsn, gb_postcodes)

        us_postcodes = project_dir / 'us_postcode_data.sql.gz'
        if us_postcodes.is_file():
            execute_file(dsn, us_postcodes)

        with conn.cursor() as cur:
            cur.execute("TRUNCATE location_postcode")
            cur.execute("""
                INSERT INTO location_postcode
                 (place_id, indexed_status, country_code, postcode, geometry)
                SELECT nextval('seq_place'), 1, country_code,
                       upper(trim (both ' ' from address->'postcode')) as pc,
                       ST_Centroid(ST_Collect(ST_Centroid(geometry)))
                  FROM placex
                 WHERE address ? 'postcode' AND address->'postcode' NOT SIMILAR TO '%(,|;)%'
                       AND geometry IS NOT null
                 GROUP BY country_code, pc
            """)

            cur.execute("""
                INSERT INTO location_postcode
                 (place_id, indexed_status, country_code, postcode, geometry)
                SELECT nextval('seq_place'), 1, 'us', postcode,
                       ST_SetSRID(ST_Point(x,y),4326)
                  FROM us_postcode WHERE postcode NOT IN
                        (SELECT postcode FROM location_postcode
                          WHERE country_code = 'us')
            """)

            cur.execute("""
                INSERT INTO location_postcode
                 (place_id, indexed_status, country_code, postcode, geometry)
                SELECT nextval('seq_place'), 1, 'gb', postcode, geometry
                  FROM gb_postcode WHERE postcode NOT IN
                           (SELECT postcode FROM location_postcode
                             WHERE country_code = 'gb')
            """)

            cur.execute("""
                    DELETE FROM word WHERE class='place' and type='postcode'
                    and word NOT IN (SELECT postcode FROM location_postcode)
            """)

            cur.execute("""
                SELECT count(getorcreate_postcode_id(v)) FROM
                (SELECT distinct(postcode) as v FROM location_postcode) p
            """)
        conn.commit()
