<?php

namespace Nominatim\ClassTypes;

/**
 * Create a label tag for the given place that can be used as an XML name.
 *
 * @param array[] $aPlace  Information about the place to label.
 *
 * A label tag groups various object types together under a common
 * label. The returned value is lower case and has no spaces
 */
function getLabelTag($aPlace, $sCountry = null)
{
    $iRank = (int) ($aPlace['rank_address'] ?? 30);
    $sLabel;
    if (isset($aPlace['place_type'])) {
        $sLabel = $aPlace['place_type'];
    } elseif ($aPlace['class'] == 'boundary' && $aPlace['type'] == 'administrative') {
        $sLabel = getBoundaryLabel($iRank/2, $sCountry);
    } elseif ($aPlace['type'] == 'postal_code') {
        $sLabel = 'postcode';
    } elseif ($iRank < 26) {
        $sLabel = $aPlace['type'];
    } elseif ($iRank < 28) {
        $sLabel = 'road';
    } elseif ($aPlace['class'] == 'place'
            && ($aPlace['type'] == 'house_number' ||
                $aPlace['type'] == 'house_name' ||
                $aPlace['type'] == 'country_code')
    ) {
        $sLabel = $aPlace['type'];
    } else {
        $sLabel = $aPlace['class'];
    }

    return strtolower(str_replace(' ', '_', $sLabel));
}

/**
 * Create a label for the given place.
 *
 * @param array[] $aPlace  Information about the place to label.
 */
function getLabel($aPlace, $sCountry = null)
{
    if (isset($aPlace['place_type'])) {
        return ucwords(str_replace('_', ' ', $aPlace['place_type']));
    }

    if ($aPlace['class'] == 'boundary' && $aPlace['type'] == 'administrative') {
        return getBoundaryLabel(($aPlace['rank_address'] ?? 30)/2, $sCountry ?? null);
    }

    // Return a label only for 'important' class/type combinations
    if (getImportance($aPlace) !== null) {
        return ucwords(str_replace('_', ' ', $aPlace['type']));
    }

    return null;
}


/**
 * Return a simple label for an administrative boundary for the given country.
 *
 * @param int $iAdminLevel   Content of admin_level tag.
 * @param string $sCountry   Country code of the country where the object is
 *                           in. May be null, in which case a world-wide
 *                           fallback is used.
 * @param string $sFallback  String to return if no explicit string is listed.
 *
 * @return string
 */
function getBoundaryLabel($iAdminLevel, $sCountry, $sFallback = 'Administrative')
{
    static $aBoundaryList = array (
                             'default' => array (
                                           1 => 'Continent',
                                           2 => 'Country',
                                           3 => 'Region',
                                           4 => 'State',
                                           5 => 'State District',
                                           6 => 'County',
                                           7 => 'Municipality',
                                           8 => 'City',
                                           9 => 'City District',
                                           10 => 'Suburb',
                                           11 => 'Neighbourhood',
                                           12 => 'City Block'
                                          ),
                             'no' => array (
                                      3 => 'State',
                                      4 => 'County'
                                     ),
                             'se' => array (
                                      3 => 'State',
                                      4 => 'County'
                                     )
            );

    if (isset($aBoundaryList[$sCountry])
        && isset($aBoundaryList[$sCountry][$iAdminLevel])
    ) {
        return $aBoundaryList[$sCountry][$iAdminLevel];
    }

    return $aBoundaryList['default'][$iAdminLevel] ?? $sFallback;
}

/**
 * Return an estimated radius of how far the object node extends.
 *
 * @param array[] $aPlace  Information about the place. This must be a node
 *                         feature.
 *
 * @return float  The radius around the feature in degrees.
 */
function getDefRadius($aPlace)
{
    $aSpecialRadius = array(
                       'place:continent' => 25,
                       'place:country' => 7,
                       'place:state' => 2.6,
                       'place:province' => 2.6,
                       'place:region' => 1.0,
                       'place:county' => 0.7,
                       'place:city' => 0.16,
                       'place:municipality' => 0.16,
                       'place:island' => 0.32,
                       'place:postcode' => 0.16,
                       'place:town' => 0.04,
                       'place:village' => 0.02,
                       'place:hamlet' => 0.02,
                       'place:district' => 0.02,
                       'place:borough' => 0.02,
                       'place:suburb' => 0.02,
                       'place:locality' => 0.01,
                       'place:neighbourhood'=> 0.01,
                       'place:quarter' => 0.01,
                       'place:city_block' => 0.01,
                       'landuse:farm' => 0.01,
                       'place:farm' => 0.01,
                       'place:airport' => 0.015,
                       'aeroway:aerodrome' => 0.015,
                       'railway:station' => 0.005
           );

    $sClassPlace = $aPlace['class'].':'.$aPlace['type'];

    return $aSpecialRadius[$sClassPlace] ?? 0.00005;
}

/**
 * Get the icon to use with the given object.
 */
function getIcon($aPlace)
{
    $aIcons = array(
               'boundary:administrative' => 'poi_boundary_administrative',
               'place:city' => 'poi_place_city',
               'place:town' => 'poi_place_town',
               'place:village' => 'poi_place_village',
               'place:hamlet' => 'poi_place_village',
               'place:suburb' => 'poi_place_village',
               'place:locality' => 'poi_place_village',
               'place:airport' => 'transport_airport2',
               'aeroway:aerodrome' => 'transport_airport2',
               'railway:station' => 'transport_train_station2',
               'amenity:place_of_worship' => 'place_of_worship_unknown3',
               'amenity:pub' => 'food_pub',
               'amenity:bar' => 'food_bar',
               'amenity:university' => 'education_university',
               'tourism:museum' => 'tourist_museum',
               'amenity:arts_centre' => 'tourist_art_gallery2',
               'tourism:zoo' => 'tourist_zoo',
               'tourism:theme_park' => 'poi_point_of_interest',
               'tourism:attraction' => 'poi_point_of_interest',
               'leisure:golf_course' => 'sport_golf',
               'historic:castle' => 'tourist_castle',
               'amenity:hospital' => 'health_hospital',
               'amenity:school' => 'education_school',
               'amenity:theatre' => 'tourist_theatre',
               'amenity:library' => 'amenity_library',
               'amenity:fire_station' => 'amenity_firestation3',
               'amenity:police' => 'amenity_police2',
               'amenity:bank' => 'money_bank2',
               'amenity:post_office' => 'amenity_post_office',
               'tourism:hotel' => 'accommodation_hotel2',
               'amenity:cinema' => 'tourist_cinema',
               'tourism:artwork' => 'tourist_art_gallery2',
               'historic:archaeological_site' => 'tourist_archaeological2',
               'amenity:doctors' => 'health_doctors',
               'leisure:sports_centre' => 'sport_leisure_centre',
               'leisure:swimming_pool' => 'sport_swimming_outdoor',
               'shop:supermarket' => 'shopping_supermarket',
               'shop:convenience' => 'shopping_convenience',
               'amenity:restaurant' => 'food_restaurant',
               'amenity:fast_food' => 'food_fastfood',
               'amenity:cafe' => 'food_cafe',
               'tourism:guest_house' => 'accommodation_bed_and_breakfast',
               'amenity:pharmacy' => 'health_pharmacy_dispensing',
               'amenity:fuel' => 'transport_fuel',
               'natural:peak' => 'poi_peak',
               'natural:wood' => 'landuse_coniferous_and_deciduous',
               'shop:bicycle' => 'shopping_bicycle',
               'shop:clothes' => 'shopping_clothes',
               'shop:hairdresser' => 'shopping_hairdresser',
               'shop:doityourself' => 'shopping_diy',
               'shop:estate_agent' => 'shopping_estateagent2',
               'shop:car' => 'shopping_car',
               'shop:garden_centre' => 'shopping_garden_centre',
               'shop:car_repair' => 'shopping_car_repair',
               'shop:bakery' => 'shopping_bakery',
               'shop:butcher' => 'shopping_butcher',
               'shop:apparel' => 'shopping_clothes',
               'shop:laundry' => 'shopping_laundrette',
               'shop:beverages' => 'shopping_alcohol',
               'shop:alcohol' => 'shopping_alcohol',
               'shop:optician' => 'health_opticians',
               'shop:chemist' => 'health_pharmacy',
               'shop:gallery' => 'tourist_art_gallery2',
               'shop:jewelry' => 'shopping_jewelry',
               'tourism:information' => 'amenity_information',
               'historic:ruins' => 'tourist_ruin',
               'amenity:college' => 'education_school',
               'historic:monument' => 'tourist_monument',
               'historic:memorial' => 'tourist_monument',
               'historic:mine' => 'poi_mine',
               'tourism:caravan_site' => 'accommodation_caravan_park',
               'amenity:bus_station' => 'transport_bus_station',
               'amenity:atm' => 'money_atm2',
               'tourism:viewpoint' => 'tourist_view_point',
               'tourism:guesthouse' => 'accommodation_bed_and_breakfast',
               'railway:tram' => 'transport_tram_stop',
               'amenity:courthouse' => 'amenity_court',
               'amenity:recycling' => 'amenity_recycling',
               'amenity:dentist' => 'health_dentist',
               'natural:beach' => 'tourist_beach',
               'railway:tram_stop' => 'transport_tram_stop',
               'amenity:prison' => 'amenity_prison',
               'highway:bus_stop' => 'transport_bus_stop2'
    );

    $sClassPlace = $aPlace['class'].':'.$aPlace['type'];

    return $aIcons[$sClassPlace] ?? null;
}

/**
 * Get an icon for the given object with its full URL.
 */
function getIconFile($aPlace)
{
    $sIcon = getIcon($aPlace);

    if (!isset($sIcon)) {
        return null;
    }

    return CONST_Website_BaseURL.'images/mapicons/'.$sIcon.'.p.20.png';
}

/**
 * Return a class importance value for the given place.
 *
 * @param array[] $aPlace  Information about the place.
 *
 * @return int  An importance value. The lower the value, the more
 *              important the class.
 */
function getImportance($aPlace)
{
    static $aWithImportance = null;

    if ($aWithImportance === null) {
        $aWithImportance = array_flip(array(
                                           'boundary:administrative',
                                           'place:country',
                                           'place:state',
                                           'place:province',
                                           'place:county',
                                           'place:city',
                                           'place:region',
                                           'place:island',
                                           'place:town',
                                           'place:village',
                                           'place:hamlet',
                                           'place:suburb',
                                           'place:locality',
                                           'landuse:farm',
                                           'place:farm',
                                           'highway:motorway_junction',
                                           'highway:motorway',
                                           'highway:trunk',
                                           'highway:primary',
                                           'highway:secondary',
                                           'highway:tertiary',
                                           'highway:residential',
                                           'highway:unclassified',
                                           'highway:living_street',
                                           'highway:service',
                                           'highway:track',
                                           'highway:road',
                                           'highway:byway',
                                           'highway:bridleway',
                                           'highway:cycleway',
                                           'highway:pedestrian',
                                           'highway:footway',
                                           'highway:steps',
                                           'highway:motorway_link',
                                           'highway:trunk_link',
                                           'highway:primary_link',
                                           'landuse:industrial',
                                           'landuse:residential',
                                           'landuse:retail',
                                           'landuse:commercial',
                                           'place:airport',
                                           'aeroway:aerodrome',
                                           'railway:station',
                                           'amenity:place_of_worship',
                                           'amenity:pub',
                                           'amenity:bar',
                                           'amenity:university',
                                           'tourism:museum',
                                           'amenity:arts_centre',
                                           'tourism:zoo',
                                           'tourism:theme_park',
                                           'tourism:attraction',
                                           'leisure:golf_course',
                                           'historic:castle',
                                           'amenity:hospital',
                                           'amenity:school',
                                           'amenity:theatre',
                                           'amenity:public_building',
                                           'amenity:library',
                                           'amenity:townhall',
                                           'amenity:community_centre',
                                           'amenity:fire_station',
                                           'amenity:police',
                                           'amenity:bank',
                                           'amenity:post_office',
                                           'leisure:park',
                                           'amenity:park',
                                           'landuse:park',
                                           'landuse:recreation_ground',
                                           'tourism:hotel',
                                           'tourism:motel',
                                           'amenity:cinema',
                                           'tourism:artwork',
                                           'historic:archaeological_site',
                                           'amenity:doctors',
                                           'leisure:sports_centre',
                                           'leisure:swimming_pool',
                                           'shop:supermarket',
                                           'shop:convenience',
                                           'amenity:restaurant',
                                           'amenity:fast_food',
                                           'amenity:cafe',
                                           'tourism:guest_house',
                                           'amenity:pharmacy',
                                           'amenity:fuel',
                                           'natural:peak',
                                           'waterway:waterfall',
                                           'natural:wood',
                                           'natural:water',
                                           'landuse:forest',
                                           'landuse:cemetery',
                                           'landuse:allotments',
                                           'landuse:farmyard',
                                           'railway:rail',
                                           'waterway:canal',
                                           'waterway:river',
                                           'waterway:stream',
                                           'shop:bicycle',
                                           'shop:clothes',
                                           'shop:hairdresser',
                                           'shop:doityourself',
                                           'shop:estate_agent',
                                           'shop:car',
                                           'shop:garden_centre',
                                           'shop:car_repair',
                                           'shop:newsagent',
                                           'shop:bakery',
                                           'shop:furniture',
                                           'shop:butcher',
                                           'shop:apparel',
                                           'shop:electronics',
                                           'shop:department_store',
                                           'shop:books',
                                           'shop:yes',
                                           'shop:outdoor',
                                           'shop:mall',
                                           'shop:florist',
                                           'shop:charity',
                                           'shop:hardware',
                                           'shop:laundry',
                                           'shop:shoes',
                                           'shop:beverages',
                                           'shop:dry_cleaning',
                                           'shop:carpet',
                                           'shop:computer',
                                           'shop:alcohol',
                                           'shop:optician',
                                           'shop:chemist',
                                           'shop:gallery',
                                           'shop:mobile_phone',
                                           'shop:sports',
                                           'shop:jewelry',
                                           'shop:pet',
                                           'shop:beauty',
                                           'shop:stationery',
                                           'shop:shopping_centre',
                                           'shop:general',
                                           'shop:electrical',
                                           'shop:toys',
                                           'shop:jeweller',
                                           'shop:betting',
                                           'shop:household',
                                           'shop:travel_agency',
                                           'shop:hifi',
                                           'amenity:shop',
                                           'tourism:information',
                                           'place:house',
                                           'place:house_name',
                                           'place:house_number',
                                           'place:country_code',
                                           'leisure:pitch',
                                           'highway:unsurfaced',
                                           'historic:ruins',
                                           'amenity:college',
                                           'historic:monument',
                                           'railway:subway',
                                           'historic:memorial',
                                           'leisure:nature_reserve',
                                           'leisure:common',
                                           'waterway:lock_gate',
                                           'natural:fell',
                                           'amenity:nightclub',
                                           'highway:path',
                                           'leisure:garden',
                                           'landuse:reservoir',
                                           'leisure:playground',
                                           'leisure:stadium',
                                           'historic:mine',
                                           'natural:cliff',
                                           'tourism:caravan_site',
                                           'amenity:bus_station',
                                           'amenity:kindergarten',
                                           'highway:construction',
                                           'amenity:atm',
                                           'amenity:emergency_phone',
                                           'waterway:lock',
                                           'waterway:riverbank',
                                           'natural:coastline',
                                           'tourism:viewpoint',
                                           'tourism:hostel',
                                           'tourism:bed_and_breakfast',
                                           'railway:halt',
                                           'railway:platform',
                                           'railway:tram',
                                           'amenity:courthouse',
                                           'amenity:recycling',
                                           'amenity:dentist',
                                           'natural:beach',
                                           'place:moor',
                                           'amenity:grave_yard',
                                           'waterway:drain',
                                           'landuse:grass',
                                           'landuse:village_green',
                                           'natural:bay',
                                           'railway:tram_stop',
                                           'leisure:marina',
                                           'highway:stile',
                                           'natural:moor',
                                           'railway:light_rail',
                                           'railway:narrow_gauge',
                                           'natural:land',
                                           'amenity:village_hall',
                                           'waterway:dock',
                                           'amenity:veterinary',
                                           'landuse:brownfield',
                                           'leisure:track',
                                           'railway:historic_station',
                                           'landuse:construction',
                                           'amenity:prison',
                                           'landuse:quarry',
                                           'amenity:telephone',
                                           'highway:traffic_signals',
                                           'natural:heath',
                                           'historic:house',
                                           'amenity:social_club',
                                           'landuse:military',
                                           'amenity:health_centre',
                                           'historic:building',
                                           'amenity:clinic',
                                           'highway:services',
                                           'amenity:ferry_terminal',
                                           'natural:marsh',
                                           'natural:hill',
                                           'highway:raceway',
                                           'amenity:taxi',
                                           'amenity:take_away',
                                           'amenity:car_rental',
                                           'place:islet',
                                           'amenity:nursery',
                                           'amenity:nursing_home',
                                           'amenity:toilets',
                                           'amenity:hall',
                                           'waterway:boatyard',
                                           'highway:mini_roundabout',
                                           'historic:manor',
                                           'tourism:chalet',
                                           'amenity:bicycle_parking',
                                           'amenity:hotel',
                                           'waterway:weir',
                                           'natural:wetland',
                                           'natural:cave_entrance',
                                           'amenity:crematorium',
                                           'tourism:picnic_site',
                                           'landuse:wood',
                                           'landuse:basin',
                                           'natural:tree',
                                           'leisure:slipway',
                                           'landuse:meadow',
                                           'landuse:piste',
                                           'amenity:care_home',
                                           'amenity:club',
                                           'amenity:medical_centre',
                                           'historic:roman_road',
                                           'historic:fort',
                                           'railway:subway_entrance',
                                           'historic:yes',
                                           'highway:gate',
                                           'leisure:fishing',
                                           'historic:museum',
                                           'amenity:car_wash',
                                           'railway:level_crossing',
                                           'leisure:bird_hide',
                                           'natural:headland',
                                           'tourism:apartments',
                                           'amenity:shopping',
                                           'natural:scrub',
                                           'natural:fen',
                                           'building:yes',
                                           'mountain_pass:yes',
                                           'amenity:parking',
                                           'highway:bus_stop',
                                           'place:postcode',
                                           'amenity:post_box',
                                           'place:houses',
                                           'railway:preserved',
                                           'waterway:derelict_canal',
                                           'amenity:dead_pub',
                                           'railway:disused_station',
                                           'railway:abandoned',
                                           'railway:disused'
                ));
    }

    $sClassPlace = $aPlace['class'].':'.$aPlace['type'];

    return $aWithImportance[$sClassPlace] ?? null;
}
