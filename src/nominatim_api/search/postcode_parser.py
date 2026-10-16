# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Handling of arbitrary postcode tokens in tokenized query string.
"""
from typing import Tuple, Set, Dict, List
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

        unique_patterns: Dict[str, Dict[str, List[str]]] = {}
        for cc, data in cdata.items():
            if data.get('postcode'):
                pat = data['postcode']['pattern'].replace('d', '[0-9]').replace('l', '[A-Z]')
                out = data['postcode'].get('output')
                if pat not in unique_patterns:
                    unique_patterns[pat] = defaultdict(list)
                unique_patterns[pat][out].append(cc.upper())

        self.global_pattern = re.compile(
                '(?:(?P<cc>[A-Z][A-Z])(?P<space>[ -]?))?(?P<pc>(?:(?:'
                + ')|(?:'.join(unique_patterns) + '))[:, >].*)')

        self.local_patterns = [(re.compile(f"{pat}[:, >]"), list(info.items()))
                               for pat, info in unique_patterns.items()]

    def parse(self, query: qmod.QueryStruct) -> Set[Tuple[int, int, str]]:
        """ Parse postcodes in the given list of query tokens taking into
            account the list of breaks from the nodes.

            The result is a sequence of tuples with
            [start node id, end node id, postcode token]
        """
        nodes = query.nodes
        outcodes: Set[Tuple[int, int, str]] = set()

        start = 0
        endnode = query.num_token_slots()
        while start < endnode:
            ptype = nodes[start].ptype
            end = start + 1
            while nodes[end].btype not in '>,:' and nodes[end].ptype == ptype:
                end += 1

            subnodes = nodes[start:end]
            if ptype == qmod.PHRASE_POSTCODE:
                self._match_word(''.join((n.btype if n.btype in ' -' else '')
                                         + n.partial.lookup_word.upper()
                                         for n in subnodes) + qmod.BREAK_PHRASE,
                                 [start, end], True, outcodes)
            elif ptype == qmod.PHRASE_ANY:
                subnodes.reverse()
                word = qmod.BREAK_PHRASE
                space_pos = [end]
                substart = end - 1
                for n in subnodes:
                    word = n.partial.lookup_word.upper() + word
                    if n.btype in '<,: ':
                        space_pos = [substart] + space_pos
                        self._match_word(word, space_pos, False, outcodes)
                        word = n.btype + word
                    elif n.btype == qmod.BREAK_PART:
                        space_pos = [substart] + space_pos
                        word = qmod.BREAK_PART + word
                    substart -= 1

            start = end

        return outcodes

    def _match_word(self, word: str, space_pos: list[int], fullmatch: bool,
                    outcodes: Set[Tuple[int, int, str]]) -> None:
        # Use global pattern to check for presence of any postcode.
        m = self.global_pattern.fullmatch(word)
        if m:
            # If there was a match, check against each pattern separately
            # because multiple patterns might be machting at the end.
            cc = m.group('cc')
            pc_word = m.group('pc')
            cc_spaces = len(m.group('space') or '')
            for pattern, info in self.local_patterns:
                lm = pattern.fullmatch(pc_word) if fullmatch else pattern.match(pc_word)
                if lm:
                    if fullmatch:
                        trange = (space_pos[0], space_pos[-1])
                    else:
                        trange = (space_pos[0],
                                  space_pos[cc_spaces
                                            + sum(c in ' ,-:>' for c in lm.group(0))])
                    for out, out_ccs in info:
                        if cc is None or cc in out_ccs:
                            if out:
                                outcodes.add((*trange, lm.expand(out)))
                            else:
                                outcodes.add((*trange, lm.group(0)[:-1]))
