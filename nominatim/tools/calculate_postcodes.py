"""
Function to calculate postcodes
"""
import os
import logging
LOG = logging.getLogger()


def calc_postcodes(conn, b_cmd_result_all, sqllib_dir, data_dir):
    """Calculate the intial postcode table
    """
    with conn.cursor() as cur:
        file = open(os.path.join(sqllib_dir, "postcode_tables.sql")).read()
        cur.execute(file)

        postcode_filename = os.path.join(data_dir, "gb_postcode_data.sql.gz")

        if os.path.isfile(postcode_filename):
            cur.execute(open(postcode_filename).read())
        else:
            LOG.warning(
                'optional external GB postcode table file (%s) not found. Skipping.',
                postcode_filename)

        postcode_filename = os.path.join(data_dir, "us_postcode_data.sql.gz")

        if os.path.isfile(postcode_filename):
            cur.execute(postcode_filename)
        else:
            LOG.warning(
                'optional external GB postcode table file (%s) not found. Skipping.',
                postcode_filename)

        cur.execute('TRUNCATE location_postcode')

        sql = (
            "INSERT INTO location_postcode "
            "(place_id, indexed_status, country_code, postcode, geometry) "
            "SELECT nextval('seq_place'), 1, country_code, "
            "upper(trim (both ' ' from address->'postcode')) as pc, "
            "ST_Centroid(ST_Collect(ST_Centroid(geometry))) "
            "FROM placex "
            "WHERE address ? 'postcode' AND address->'postcode' NOT SIMILAR TO '%(,|;)% "
            "AND geometry IS NOT null "
            "GROUP BY country_code, pc"
        )
        cur.execute(sql)

        # only add postcodes that are not yet available in OSM
        sql = (
            "INSERT INTO location_postcode"
            " (place_id, indexed_status, country_code, postcode, geometry) "
            "SELECT nextval('seq_place'), 1, 'us', postcode,"
            " ST_SetSRID(ST_Point(x,y),4326)"
            " FROM us_postcode WHERE postcode NOT IN"
            " (SELECT postcode FROM location_postcode"
            " WHERE country_code = 'us')"
        )
        cur.execute(sql)

        # add missing postcodes for GB (if available)
        sql = (
            "INSERT INTO location_postcode"
            " (place_id, indexed_status, country_code, postcode, geometry) "
            "SELECT nextval('seq_place'), 1, 'gb', postcode, geometry"
            " FROM gb_postcode WHERE postcode NOT IN"
            " (SELECT postcode FROM location_postcode"
            " WHERE country_code = 'gb')"
        )
        cur.execute(sql)

        if not b_cmd_result_all:
            sql = (
                "DELETE FROM word WHERE class='place' and type='postcode'"
                " and word NOT IN (SELECT postcode FROM location_postcode)"
            )
            cur.execute(sql)

        sql = (
            "SELECT count(getorcreate_postcode_id(v)) FROM "
            "(SELECT distinct(postcode) as v FROM location_postcode) p"
        )
        cur.execute(sql)
    conn.commit()
