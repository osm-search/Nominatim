"""
    Module containing the class SpecialPhrase.

    This class is a model used to transfer a special phrase through
    the process of load and importation.
"""
import re

class SpecialPhrase():
    """
        Model representing a special phrase.
    """
    def __init__(self, p_label, p_class, p_type, p_operator):
        self.p_label = p_label.strip()
        self.p_class = p_class.strip()
        # Hack around a bug where building=yes was imported with quotes into the wiki
        self.p_type = re.sub(r'\"|&quot;', '', p_type.strip())
        # Needed if some operator in the wiki are not written in english
        p_operator = p_operator.strip()
        self.p_operator = '-' if p_operator not in ('near', 'in') else p_operator
