# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
    Module containing the class SpecialPhrase.

    This class is a model used to transfer a special phrase through
    the process of load and importation.
"""
class SpecialPhrase():
    """
        Model representing a special phrase.
    """
    def __init__(self, p_label, p_class, p_type, p_operator):
        self.p_label = p_label.strip()
        self.p_class = p_class.strip()
        # Hack around a bug where building=yes was imported with quotes into the wiki
        self.p_type = p_type.strip()
        # Needed if some operator in the wiki are not written in english
        p_operator = p_operator.strip().lower()
        self.p_operator = '-' if p_operator not in ('near', 'in') else p_operator
