"""
Data structures for saving variant expansions for ICU tokenizer.
"""
from collections import namedtuple
import json

from nominatim.errors import UsageError

_ICU_VARIANT_PORPERTY_FIELDS = ['lang']

def _get_strtuple_prop(rules, field):
    """ Return the given field of the rules dictionary as a list.

        If the field is not defined or empty, returns None. If the field is
        a singe string, it is converted into a tuple with a single element.
        If the field is a list of strings, return as a string tuple.
        Raise a usage error in all other cases.
    """
    value = rules.get(field)

    if not value:
        return None

    if isinstance(value, str):
        return (value,)

    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise UsageError("YAML variant property '{}' should be a list.".format(field))

    return tuple(value)


class ICUVariantProperties(namedtuple('_ICUVariantProperties', _ICU_VARIANT_PORPERTY_FIELDS,
                                      defaults=(None, )*len(_ICU_VARIANT_PORPERTY_FIELDS))):
    """ Data container for saving properties that describe when a variant
        should be applied.

        Porperty instances are hashable.
    """
    @classmethod
    def from_rules(cls, rules):
        """ Create a new property type from a generic dictionary.

            The function only takes into account the properties that are
            understood presently and ignores all others.
        """
        return cls(lang=_get_strtuple_prop(rules, 'lang'))


ICUVariant = namedtuple('ICUVariant', ['source', 'replacement', 'properties'])

def pickle_variant_set(variants):
    """ Serializes an iterable of variant rules to a string.
    """
    # Create a list of property sets. So they don't need to be duplicated
    properties = {}
    pid = 1
    for variant in variants:
        if variant.properties not in properties:
            properties[variant.properties] = pid
            pid += 1

    # Convert the variants into a simple list.
    variants = [(v.source, v.replacement, properties[v.properties]) for v in variants]

    # Convert everythin to json.
    return json.dumps({'properties': {v: k._asdict() for k, v in properties.items()},
                       'variants': variants})


def unpickle_variant_set(variant_string):
    """ Deserializes a variant string that was previously created with
        pickle_variant_set() into a set of ICUVariants.
    """
    data = json.loads(variant_string)

    properties = {int(k): ICUVariantProperties(**v) for k, v in data['properties'].items()}
    print(properties)

    return set((ICUVariant(src, repl, properties[pid]) for src, repl, pid in data['variants']))
