import os
import psycopg2
import logging
LOG = logging.getLogger()

def calc_postcodes(conn, bCMDResultAll, sqllib_dir, data_dir):
    with conn.cursor() as cur:
        file = open(os.path.join(osqllib_dir, "postcode_tables.sql")).read()
        cur.execute(file)

        postcode_filename = os.path.join(data_dir, "gb_postcode_data.sql.gz")

        if os.path.isfile(postcode_filename):
            cur.execute(open(postcode_filename).read())
        else:
            LOG.warning(f'optional external GB postcode table file ({postcode_filename}) not found. Skipping.')

        postcode_filename = os.path.join(data_dir, "us_postcode_data.sql.gz")

        if os.path.isfile(postcode_filename):
            cur.execute(postcode_filename)
        else:
            LOG.warning(f'optional external US postcode table file ({postcode_filename}) not found. Skipping.')

        cur.execute('TRUNCATE location_postcode')

        sSQL = (
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
        cur.execute(sSQL)

        # only add postcodes that are not yet available in OSM
        sSQL = (
            "INSERT INTO location_postcode"
            " (place_id, indexed_status, country_code, postcode, geometry) "
            "SELECT nextval('seq_place'), 1, 'us', postcode,"
            " ST_SetSRID(ST_Point(x,y),4326)"
            " FROM us_postcode WHERE postcode NOT IN"
            " (SELECT postcode FROM location_postcode"
            " WHERE country_code = 'us')"
            )
        cur.execute(sSQL)

        # add missing postcodes for GB (if available)
        sSQL = (
            "INSERT INTO location_postcode"
            " (place_id, indexed_status, country_code, postcode, geometry) "
            "SELECT nextval('seq_place'), 1, 'gb', postcode, geometry"
            " FROM gb_postcode WHERE postcode NOT IN"
            " (SELECT postcode FROM location_postcode"
            " WHERE country_code = 'gb')"
            )
        cur.execute(sSQL)

        if not bCMDResultAll:
            sSQL = (
                "DELETE FROM word WHERE class='place' and type='postcode'"
                " and word NOT IN (SELECT postcode FROM location_postcode)"
                )
            cur.execute(sSQL)
        
        sSQL = (
            "SELECT count(getorcreate_postcode_id(v)) FROM "
            "(SELECT distinct(postcode) as v FROM location_postcode) p"
            )
        cur.execute(sSQL)
    conn.commit()
