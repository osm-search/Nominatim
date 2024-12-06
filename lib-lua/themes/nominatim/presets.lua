-- Defines defaults used in the topic definitions.

local module = {}

-- Main tag definition

module.MAIN_TAGS = {}

module.MAIN_TAGS.admin = {
    boundary = {administrative = 'named'},
    landuse = {residential = 'fallback',
               farm = 'fallback',
               farmyard = 'fallback',
               industrial = 'fallback',
               commercial = 'fallback',
               allotments = 'fallback',
               retail = 'fallback'},
    place = {county = 'always',
             district = 'always',
             municipality = 'always',
             city = 'always',
             town = 'always',
             borough = 'always',
             village = 'always',
             suburb = 'always',
             hamlet = 'always',
             croft = 'always',
             subdivision = 'always',
             allotments = 'always',
             neighbourhood = 'always',
             quarter = 'always',
             isolated_dwelling = 'always',
             farm = 'always',
             city_block = 'always',
             locality = 'always'}
}

module.MAIN_TAGS.all_boundaries = {
    boundary = {'named',
                place = 'delete',
                land_area = 'delete',
                postal_code = 'always'},
    landuse = 'fallback',
    place = 'always'
}

module.MAIN_TAGS.natural = {
    waterway = {'named',
                riverbank = 'delete'},
    natural = {'named',
               yes = 'delete',
               no = 'delete',
               coastline = 'delete',
               saddle = 'fallback'},
    mountain_pass = {'always',
                     no = 'delete'}
}

module.MAIN_TAGS_POIS = function (group)
    group = group or 'delete'
    return {
    aerialway = {'always',
                 no = group,
                 pylon = group},
    aeroway = {'always',
               no = group},
    amenity = {'always',
               no = group,
               parking_space = group,
               parking_entrance = group,
               waste_disposal = group,
               hunting_stand = group},
    building = {'fallback',
                no = group},
    bridge = {'named_with_key',
              no = group},
    club = {'always',
            no = group},
    craft = {'always',
             no = group},
    emergency = {'always',
                 no = group,
                 yes = group,
                 fire_hydrant = group},
    healthcare = {'fallback',
                  yes = group,
                  no = group},
    highway = {'always',
               no = group,
               turning_circle = group,
               mini_roundabout = group,
               noexit = group,
               crossing = group,
               give_way = group,
               stop = group,
               turning_loop = group,
               passing_place = group,
               street_lamp = 'named',
               traffic_signals = 'named'},
    historic = {'always',
                yes = group,
                no = group},
    junction = {'fallback',
                no = group},
    leisure = {'always',
               nature_reserve = 'fallback',
               no = group},
    man_made = {pier = 'always',
                tower = 'always',
                bridge = 'always',
                works = 'named',
                water_tower = 'always',
                dyke = 'named',
                adit = 'named',
                lighthouse = 'always',
                watermill = 'always',
                tunnel = 'always'},
    military = {'always',
                yes = group,
                no = group},
    office = {'always',
              no = group},
    railway = {'named',
               rail = group,
               no = group,
               abandoned = group,
               disused = group,
               razed = group,
               level_crossing = group,
               switch = group,
               signal = group,
               buffer_stop = group},
    shop = {'always',
            no = group},
    tourism = {'always',
               no = group,
               yes = group},
    tunnel = {'named_with_key',
              no = group}
} end

module.MAIN_TAGS_STREETS = {}

module.MAIN_TAGS_STREETS.default = {
    place = {square = 'always'},
    highway = {motorway = 'always',
               trunk = 'always',
               primary = 'always',
               secondary = 'always',
               tertiary = 'always',
               unclassified = 'always',
               residential = 'always',
               road = 'always',
               living_street = 'always',
               pedestrian = 'always',
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
               tertiary_link = 'named'}
}

module.MAIN_TAGS_STREETS.car = {
    place = {square = 'always'},
    highway = {motorway = 'always',
               trunk = 'always',
               primary = 'always',
               secondary = 'always',
               tertiary = 'always',
               unclassified = 'always',
               residential = 'always',
               road = 'always',
               living_street = 'always',
               service = 'always',
               track = 'always',
               motorway_link = 'always',
               trunk_link = 'always',
               primary_link = 'always',
               secondary_link = 'always',
               tertiary_link = 'always'}
}

module.MAIN_TAGS_STREETS.all = {
    place = {square = 'always'},
    highway = {motorway = 'always',
               trunk = 'always',
               primary = 'always',
               secondary = 'always',
               tertiary = 'always',
               unclassified = 'always',
               residential = 'always',
               road = 'always',
               living_street = 'always',
               pedestrian = 'always',
               service = 'always',
               cycleway = 'always',
               path = 'always',
               footway = 'always',
               steps = 'always',
               bridleway = 'always',
               track = 'always',
               motorway_link = 'always',
               trunk_link = 'always',
               primary_link = 'always',
               secondary_link = 'always',
               tertiary_link = 'always'}
}


-- name tags

module.NAME_TAGS = {}

module.NAME_TAGS.core = {main = {'name', 'name:*',
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
                                  'loc_ref', 'old_ref', 'ISO3166-2'}
                        }
module.NAME_TAGS.address = {house = {'addr:housename'}}
module.NAME_TAGS.poi = {extra = {'ref', 'int_ref', 'nat_ref', 'reg_ref',
                                       'loc_ref', 'old_ref',
                                       'iata', 'icao',
                                       'ISO3166-2'}}

-- Address tagging

module.ADDRESS_TAGS = {}

module.ADDRESS_TAGS.core = { extra = {'addr:*', 'is_in:*', 'tiger:county'},
                             postcode = {'postal_code', 'postcode', 'addr:postcode',
                                         'tiger:zip_left', 'tiger:zip_right'},
                             country = {'country_code', 'ISO3166-1',
                                        'addr:country_code', 'is_in:country_code',
                                        'addr:country', 'is_in:country'}
                           }

module.ADDRESS_TAGS.houses = { main = {'addr:housenumber',
                                       'addr:conscriptionnumber',
                                       'addr:streetnumber'},
                               interpolation = {'addr:interpolation'}
                             }

-- Ignored tags (prefiltered away)

module.IGNORE_KEYS = {}

module.IGNORE_KEYS.metatags = {'note', 'note:*', 'source', 'source:*', '*source',
                               'attribution', 'comment', 'fixme', 'created_by',
                               'tiger:cfcc', 'tiger:reviewed', 'nysgissam:*',
                               'NHD:*', 'nhd:*', 'gnis:*', 'geobase:*', 'yh:*',
                               'osak:*', 'naptan:*', 'CLC:*', 'import', 'it:fvg:*',
                               'lacounty:*', 'ref:linz:*',
                               'ref:bygningsnr', 'ref:ruian:*', 'building:ruian:type',
                               'type',
                               'is_in:postcode'}
module.IGNORE_KEYS.name = {'*:prefix', '*:suffix', 'name:prefix:*', 'name:suffix:*',
                           'name:etymology', 'name:signed', 'name:botanical'}
module.IGNORE_KEYS.address = {'addr:street:*', 'addr:TW:dataset'}

-- Extra tags (prefiltered away)

module.EXTRATAGS = {}

module.EXTRATAGS.required = {'wikipedia', 'wikipedia:*', 'wikidata', 'capital'}

return module
