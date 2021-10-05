"""
Name processor that splits name values with multiple values into their components.
"""
import re

from nominatim.errors import UsageError

def create(func):
    """ Create a name processing function that splits name values with
        multiple values into their components. The optional parameter
        'delimiters' can be used to define the characters that should be used
        for splitting. The default is ',;'.
    """
    delimiter_set = set(func.get('delimiters', ',;'))
    if not delimiter_set:
        raise UsageError("Set of delimiters in split-name-list sanitizer is empty.")

    regexp = re.compile('\\s*[{}]\\s*'.format(''.join('\\' + d for d in delimiter_set)))

    def _process(obj):
        if not obj.names:
            return

        new_names = []
        for name in obj.names:
            split_names = regexp.split(name.name)
            if len(split_names) == 1:
                new_names.append(name)
            else:
                new_names.extend(name.clone(name=n) for n in split_names if n)

        obj.names = new_names

    return _process
