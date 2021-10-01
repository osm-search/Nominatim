"""
Data structures for saving variant expansions for ICU tokenizer.
"""
from collections import namedtuple

_ICU_VARIANT_PORPERTY_FIELDS = ['lang']


class ICUVariantProperties(namedtuple('_ICUVariantProperties', _ICU_VARIANT_PORPERTY_FIELDS)):
    """ Data container for saving properties that describe when a variant
        should be applied.

        Property instances are hashable.
    """
    @classmethod
    def from_rules(cls, _):
        """ Create a new property type from a generic dictionary.

            The function only takes into account the properties that are
            understood presently and ignores all others.
        """
        return cls(lang=None)


ICUVariant = namedtuple('ICUVariant', ['source', 'replacement', 'properties'])
