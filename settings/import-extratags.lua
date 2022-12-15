require('flex-base')

RELATION_TYPES = {
    multipolygon = relation_as_multipolygon,
    boundary = relation_as_multipolygon,
    waterway = relation_as_multiline
}

MAIN_KEYS = {
    building = 'fallback',
    emergency = 'always',
    healthcare = 'fallback',
    historic = 'always',
    military = 'always',
    natural = 'named',
    landuse = 'named',
    highway = {'always',
               street_lamp = 'named',
               traffic_signals = 'named',
               service = 'named',
               cycleway = 'named',
               path = 'named',
               footway = 'named',
               steps = 'named',
               bridleway = 'named',
               track = 'named',
               motorway_link = 'named',
               trunk_link = 'named',
               primary_link = 'named',
               secondary_link = 'named',
               tertiary_link = 'named'},
    railway = 'named',
    man_made = 'always',
    aerialway = 'always',
    boundary = {'named',
                postal_code = 'named'},
    aeroway = 'always',
    amenity = 'always',
    club = 'always',
    craft = 'always',
    junction = 'fallback',
    landuse = 'fallback',
    leisure = 'always',
    office = 'always',
    mountain_pass = 'always',
    shop = 'always',
    tourism = 'always',
    bridge = 'named_with_key',
    tunnel = 'named_with_key',
    waterway = 'named',
    place = 'always'
}


PRE_DELETE = tag_match{keys = {'note', 'note:*', 'source', 'source*', 'attribution',
                               'comment', 'fixme', 'FIXME', 'created_by', 'NHD:*',
                               'nhd:*', 'gnis:*', 'geobase:*', 'KSJ2:*', 'yh:*',
                               'osak:*', 'naptan:*', 'CLC:*', 'import', 'it:fvg:*',
                               'type', 'lacounty:*', 'ref:ruian:*', 'building:ruian:type',
                               'ref:linz:*', 'is_in:postcode'},
                       tags = {emergency = {'yes', 'no', 'fire_hydrant'},
                               historic = {'yes', 'no'},
                               military = {'yes', 'no'},
                               natural = {'yes', 'no', 'coastline'},
                               highway = {'no', 'turning_circle', 'mini_roundabout',
                                          'noexit', 'crossing', 'give_way', 'stop'},
                               railway = {'level_crossing', 'no', 'rail'},
                               man_made = {'survey_point', 'cutline'},
                               aerialway = {'pylon', 'no'},
                               aeroway = {'no'},
                               amenity = {'no'},
                               club = {'no'},
                               craft = {'no'},
                               leisure = {'no'},
                               office = {'no'},
                               mountain_pass = {'no'},
                               shop = {'no'},
                               tourism = {'yes', 'no'},
                               bridge = {'no'},
                               tunnel = {'no'},
                               waterway = {'riverbank'},
                               building = {'no'},
                               boundary = {'place'}}
                      }

POST_DELETE = tag_match{keys = {'tiger:*'}}

PRE_EXTRAS = tag_match{keys = {'*:prefix', '*:suffix', 'name:prefix:*', 'name:suffix:*',
                               'name:etymology', 'name:signed', 'name:botanical',
                               'wikidata', '*:wikidata',
                               'addr:street:name', 'addr:street:type'}
                      }


NAMES = tag_match{keys = {'name', 'name:*',
                          'int_name', 'int_name:*',
                          'nat_name', 'nat_name:*',
                          'reg_name', 'reg_name:*',
                          'loc_name', 'loc_name:*',
                          'old_name', 'old_name:*',
                          'alt_name', 'alt_name:*', 'alt_name_*',
                          'official_name', 'official_name:*',
                          'place_name', 'place_name:*',
                          'short_name', 'short_name:*', 'brand'}}

REFS = tag_match{keys = {'ref', 'int_ref', 'nat_ref', 'reg_ref', 'loc_ref', 'old_ref',
                         'iata', 'icao', 'pcode', 'pcode:*', 'ISO3166-2'}}

HOUSENAME_TAGS = tag_match{keys = {'addr:housename'}}

ADDRESS_TAGS = key_group{main = {'addr:housenumber',
                                 'addr:conscriptionnumber',
                                 'addr:streetnumber'},
                         extra = {'addr:*', 'is_in:*', 'tiger:county'},
                         postcode = {'postal_code', 'postcode', 'addr:postcode',
                                     'tiger:zip_left', 'tiger:zip_right'},
                         country = {'country_code', 'ISO3166-1',
                                    'addr:country_code', 'is_in:country_code',
                                    'addr:country', 'is_in:country'},
                         interpolation = {'addr:interpolation'}
                        }

SAVE_EXTRA_MAINS = true

