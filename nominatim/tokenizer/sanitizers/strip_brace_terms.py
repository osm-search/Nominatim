# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This sanitizer creates additional name variants for names that have
addendums in brackets (e.g. "Halle (Saale)"). The additional variant contains
only the main name part with the bracket part removed.
"""

def create(_):
    """ Create a name processing function that creates additional name variants
        for bracket addendums.
    """
    def _process(obj):
        """ Add variants for names that have a bracket extension.
        """
        if obj.names:
            new_names = []
            for name in (n for n in obj.names if '(' in n.name):
                new_name = name.name.split('(')[0].strip()
                if new_name:
                    new_names.append(name.clone(name=new_name))

            obj.names.extend(new_names)

    return _process
