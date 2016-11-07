""" Steps that run search queries.

    Queries may either be run directly via PHP using the query script
    or via the HTTP interface.
"""

import os
import subprocess

class SearchResponse(object):

    def __init__(response, 

@when(u'searching for "(?P<query>.*)"( with params)?$')
def query_cmd(context, query):
    """ Query directly via PHP script.
    """
    cmd = [os.path.join(context.nominatim.build_dir, 'utils', 'query.php'),
           '--search', query]
    # add more parameters in table form
    if context.table:
        for h in context.table.headings:
            value = context.table[0][h].strip()
            if value:
                cmd.extend(('--' + h, value))

    proc = subprocess.Popen(cmd, cwd=context.nominatim.build_dir,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (outp, err) = proc.communicate()

    assert_equals (0, proc.returncode), "query.php failed with message: %s" % err

    context.
    world.page = outp
    world.response_format = 'json'
    world.request_type = 'search'
    world.returncode = 200

