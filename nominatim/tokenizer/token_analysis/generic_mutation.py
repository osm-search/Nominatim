# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Creator for mutation variants for the generic token analysis.
"""
import itertools
import logging
import re

from nominatim.errors import UsageError

LOG = logging.getLogger()

def _zigzag(outer, inner):
    return itertools.chain.from_iterable(itertools.zip_longest(outer, inner, fillvalue=''))


class MutationVariantGenerator:
    """ Generates name variants by applying a regular expression to the name
        and replacing it with one or more variants. When the regular expression
        matches more than once, each occurence is replaced with all replacement
        patterns.
    """

    def __init__(self, pattern, replacements):
        self.pattern = re.compile(pattern)
        self.replacements = replacements

        if self.pattern.groups > 0:
            LOG.fatal("The mutation pattern %s contains a capturing group. "
                      "This is not allowed.", pattern)
            raise UsageError("Bad mutation pattern in configuration.")


    def generate(self, names):
        """ Generator function for the name variants. 'names' is an iterable
            over a set of names for which the variants are to be generated.
        """
        for name in names:
            parts = self.pattern.split(name)
            if len(parts) == 1:
                yield name
            else:
                for seps in self._fillers(len(parts)):
                    yield ''.join(_zigzag(parts, seps))


    def _fillers(self, num_parts):
        """ Returns a generator for strings to join the given number of string
            parts in all possible combinations.
        """
        return itertools.product(self.replacements, repeat=num_parts - 1)
