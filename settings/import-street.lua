local flex = require('flex-base')

flex.set_main_tags{
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
    boundary = {administrative = 'named'},
    landuse = 'fallback',
    place = 'always'
}

flex.set_prefilters{delete_keys = {'building', 'source',
                                   'addr:housenumber', 'addr:street',
                                   'source', '*source', 'type',
                                   'is_in:postcode', '*:wikidata', '*:wikipedia',
                                   '*:prefix', '*:suffix', 'name:prefix:*', 'name:suffix:*',
                                   'name:etymology', 'name:signed', 'name:botanical',
                                   'addr:street:name', 'addr:street:type'},
                    delete_tags = {highway = {'no', 'turning_circle', 'mini_roundabout',
                                              'noexit', 'crossing', 'give_way', 'stop'},
                                   landuse = {'cemetry', 'no'},
                                   boundary = {'place'}},
                    extra_keys = {'wikipedia', 'wikipedia:*', 'wikidata', 'capital', 'area'}
                   }

flex.set_name_tags{main = {'name', 'name:*',
                          'int_name', 'int_name:*',
                          'nat_name', 'nat_name:*',
                          'reg_name', 'reg_name:*',
                          'loc_name', 'loc_name:*',
                          'old_name', 'old_name:*',
                          'alt_name', 'alt_name:*', 'alt_name_*',
                          'official_name', 'official_name:*',
                          'place_name', 'place_name:*',
                          'short_name', 'short_name:*'},
                   extra = {'ref', 'int_ref', 'nat_ref', 'reg_ref',
                            'loc_ref', 'old_ref',
                            'iata', 'icao', 'pcode', 'pcode:*', 'ISO3166-2'}
                  }

flex.set_address_tags{main = {'addr:housenumber',
                              'addr:conscriptionnumber',
                              'addr:streetnumber'},
                      extra = {'addr:*', 'is_in:*', 'tiger:county'},
                      postcode = {'postal_code', 'postcode', 'addr:postcode',
                                  'tiger:zip_left', 'tiger:zip_right'},
                      country = {'country_code', 'ISO3166-1',
                                 'addr:country_code', 'is_in:country_code',
                                 'addr:country', 'is_in:country'},
                      interpolation = {'addr:interpolation'},
                      postcode_fallback = false
                     }

flex.set_unused_handling{extra_keys = {'place'}}

return flex
