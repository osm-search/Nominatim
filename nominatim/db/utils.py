"""
Helper functions for handling DB accesses.
"""

def execute_file(conn, fname):
    """ Read an SQL file and run its contents against the given connection.
    """
    with fname.open('r') as fdesc:
        sql = fdesc.read()
    with conn.cursor() as cur:
        cur.execute(sql)
