"""
Sanitizer handling names with addendums in braces.
"""

def create(_):
    """ Create a name processing function that creates additional name variants
        when a name has an addendum in brackets (e.g. "Halle (Saale)"). The
        additional variant only contains the main name without the bracket part.
    """
    def _process(obj):
        """ Add variants for names that have a bracket extension.
        """
        new_names = []
        if obj.names:
            for name in (n for n in obj.names if '(' in n.name):
                new_name = name.name.split('(')[0].strip()
                if new_name:
                    new_names.append(name.clone(name=new_name))

        obj.names.extend(new_names)

    return _process
