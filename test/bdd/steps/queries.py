""" Steps that run search queries.

    Queries may either be run directly via PHP using the query script
    or via the HTTP interface.
"""

import json
import os
import subprocess
from collections import OrderedDict
from nose.tools import * # for assert functions

class SearchResponse(object):

    def __init__(self, page, fmt='json', errorcode=200):
        self.page = page
        self.format = fmt
        self.errorcode = errorcode
        getattr(self, 'parse_' + fmt)()

    def parse_json(self):
        self.result = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(self.page)

    def match_row(self, row):
        if 'ID' in row.headings:
            todo = [int(row['ID'])]
        else:
            todo = range(len(self.result))

        for i in todo:
            res = self.result[i]
            for h in row.headings:
                if h == 'ID':
                    pass
                elif h == 'osm':
                    assert_equal(res['osm_type'], row[h][0])
                    assert_equal(res['osm_id'], row[h][1:])
                elif h == 'centroid':
                    x, y = row[h].split(' ')
                    assert_almost_equal(float(y), float(res['lat']))
                    assert_almost_equal(float(x), float(res['lon']))
                else:
                    assert_in(h, res)
                    assert_equal(str(res[h]), str(row[h]))


@when(u'searching for "(?P<query>.*)"')
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

    assert_equals (0, proc.returncode, "query.php failed with message: %s" % err)

    context.response = SearchResponse(outp.decode('utf-8'), 'json')
