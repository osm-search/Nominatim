# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Handling of arbitrary postcode tokens in tokenized query string.
"""
from typing import Tuple, Set
import re
from collections import defaultdict

import yaml

from ..config import Configuration
from . import query as qmod


class PostcodeParser:
    """ Pattern-based parser for postcodes in tokenized queries.

        The postcode patterns are read from the country configuration.
        The parser does currently not return country restrictions.
    """

    def __init__(self, config: Configuration) -> None:
        # skip over includes here to avoid loading the complete country name data
        yaml.add_constructor('!include', lambda loader, node: [],
                             Loader=yaml.SafeLoader)
        cdata = yaml.safe_load(config.find_config_file('country_settings.yaml')
                                     .read_text(encoding='utf-8'))

        unique_patterns = defaultdict(set)
        for cc, data in cdata.items():
            if data.get('postcode'):
                pat = data['postcode']['pattern']
                out = data['postcode'].get('output')
                unique_patterns[pat.replace('d', '[0-9]').replace('l', '[a-z]')].add(out)

        self.global_pattern = re.compile(
                '(?:' +
                '|'.join(f"(?:{k})" for k in unique_patterns)
                + ')[:, >]')

        self.local_patterns = [(re.compile(f"(?:{k})[:, >]"), v)
                               for k, v in unique_patterns.items()]

    def parse(self, query: qmod.QueryStruct) -> Set[Tuple[int, int, str]]:
        """ Parse postcodes in the given list of query tokens taking into
            account the list of breaks from the nodes.

            The result is a sequence of tuples with
            [start node id, end node id, postcode token]
        """
        nodes = query.nodes
        outcodes = set()

        for i in range(query.num_token_slots()):
            if nodes[i].btype in '<,: ' and nodes[i + 1].btype != '`':
                word = nodes[i + 1].term_normalized + nodes[i + 1].btype
                if word[-1] in ' -' and nodes[i + 2].btype != '`':
                    word += nodes[i + 2].term_normalized + nodes[i + 2].btype
                    if word[-1] in ' -' and nodes[i + 3].btype != '`':
                        word += nodes[i + 3].term_normalized + nodes[i + 3].btype

                # Use global pattern to check for presence of any postocde.
                m = self.global_pattern.match(word)
                if m:
                    # If there was a match, check against each pattern separately
                    # because multiple patterns might be machting at the end.
                    for pattern, info in self.local_patterns:
                        lm = pattern.match(word)
                        if lm:
                            trange = (i, i + sum(c in ' ,-:>' for c in lm.group(0)))
                            for out in info:
                                if out:
                                    outcodes.add((*trange, lm.expand(out).upper()))
                                else:
                                    outcodes.add((*trange, lm.group(0)[:-1].upper()))
        return outcodes
