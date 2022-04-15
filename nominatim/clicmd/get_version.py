# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
import nominatim.version
import logging
import requests

LOG = logging.getLogger()

class Version:
    """\
    Show version of Nominatim and looks for new ones.

    Takes an optional argument -offline to not check online for new versions.
    """

    def add_args(parser):
        group = parser.add_argument_group('Input arguments')
        group.add_argument('--offline',
                    help='It won´t check for last version available online',
                    dest='offline',
                    action='store_false')

    def run(args):
        version = nominatim.version.NOMINATIM_VERSION

        #Checks also for new versions. Link is supposed to be kept alive.
        if (args.offline):
            r = requests.get('https://raw.githubusercontent.com/osm-search/Nominatim/master/nominatim/version.py')
            checking_keywords = 'NOMINATIM_VERSION = '
            if (r.status_code != 200): 
                LOG.warning("No internet connection to check for updates.")
            else:
                index = r.text.find(checking_keywords)
                if (index == -1):
                    LOG.warning("No internet connection to check for updates.")
                else:
                    index += len(checking_keywords)
                    raw_version = r.text[index+1:(r.text.find(')', index))]
                    last_version = [int(n) for n in raw_version.split(',')]

                    if (len(last_version) != 4):
                        LOG.warning("Failed while parsing last version from repository.")
                    else:
                        for x in range(4):
                            if (version[x] != last_version[x]):
                                LOG.warning("You are not using the last version: %d.%d.%d.%d", last_version[0], last_version[1], last_version[2], last_version[3])
                                break
                            if (x == 3):
                                LOG.warning("You are using the last version available.")
                    
        LOG.warning("Current version: %d.%d.%d.%d", version[0], version[1], version[2], version[3])
        return 0
