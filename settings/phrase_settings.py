"""
    These settings control the import of special phrases from the wiki.
"""
#class/type combinations to exclude
BLACK_LIST = {
    'bounday': [
        'administrative'
    ],
    'place': [
        'house',
        'houses'
    ]
}

#If a class is in the white list then all types will
#be ignored except the ones given in the list.
#Also use this list to exclude an entire class from
#special phrases.
WHITE_LIST = {
    'highway': [
        'bus_stop',
        'rest_area',
        'raceway'
    ],
    'building': []
}
