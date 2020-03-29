<?php

namespace Nominatim\ClassTypes;

function getInfo($aPlace)
{
    $aClassType = getList();

    if ($aPlace['type'] == 'administrative' && isset($aPlace['place_type'])) {
        $sName = 'place:'.$aPlace['place_type'];
        if (isset($aClassType[$sName])) {
            return $aClassType[$sName];
        }
    }

    if (isset($aPlace['admin_level'])) {
        $sName = $aPlace['class'].':'.$aPlace['type'].':'.$aPlace['admin_level'];
        if (isset($aClassType[$sName])) {
            return $aClassType[$sName];
        }
    }

    $sName = $aPlace['class'].':'.$aPlace['type'];
    if (isset($aClassType[$sName])) {
        return $aClassType[$sName];
    }

    return false;
}

function getFallbackInfo($aPlace)
{
    $aClassType = getList();

    $sFallback = 'boundary:administrative:'.((int)($aPlace['rank_address']/2));
    if (isset($aClassType[$sFallback])) {
        return $aClassType[$sFallback];
    }

    return array('simplelabel' => 'address'.$aPlace['rank_address']);
}

function getProperty($aPlace, $sProp, $mDefault = false)
{
    $aClassType = getList();

    if (isset($aPlace['admin_level'])) {
        $sName = $aPlace['class'].':'.$aPlace['type'].':'.$aPlace['admin_level'];
        if (isset($aClassType[$sName]) && isset($aClassType[$sName][$sProp])) {
            return $aClassType[$sName][$sProp];
        }
    }

    $sName = $aPlace['class'].':'.$aPlace['type'];
    if (isset($aClassType[$sName]) && isset($aClassType[$sName][$sProp])) {
        return $aClassType[$sName][$sProp];
    }

    return $mDefault;
}

function getListWithImportance()
{
    static $aOrders = null;
    if ($aOrders === null) {
        $aOrders = getList();
        $i = 1;
        foreach ($aOrders as $sID => $a) {
            $aOrders[$sID]['importance'] = $i++;
        }
    }

    return $aOrders;
}

function getList()
{
    return array(
            'boundary:administrative:1' => array('label' => 'Continent', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'boundary:administrative:2' => array('label' => 'Country', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'place:country' => array('label' => 'Country', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defzoom' => 6, 'defdiameter' => 15),
            'boundary:administrative:3' => array('label' => 'State', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'boundary:administrative:4' => array('label' => 'State', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'place:state' => array('label' => 'State', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defzoom' => 8, 'defdiameter' => 5.12),
            'boundary:administrative:5' => array('label' => 'State District', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'boundary:administrative:6' => array('label' => 'County', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'boundary:administrative:7' => array('label' => 'County', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'place:county' => array('label' => 'County', 'frequency' => 108, 'icon' => 'poi_boundary_administrative', 'defzoom' => 10, 'defdiameter' => 1.28),
            'boundary:administrative:8' => array('label' => 'City', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'place:city' => array('label' => 'City', 'frequency' => 66, 'icon' => 'poi_place_city', 'defzoom' => 12, 'defdiameter' => 0.32),
            'boundary:administrative:9' => array('label' => 'City District', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'boundary:administrative:10' => array('label' => 'Suburb', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'boundary:administrative:11' => array('label' => 'Neighbourhood', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'place:region' => array('label' => 'Region', 'frequency' => 0, 'icon' => 'poi_boundary_administrative', 'defzoom' => 8, 'defdiameter' => 0.04),
            'place:island' => array('label' => 'Island', 'frequency' => 288, 'defzoom' => 11, 'defdiameter' => 0.64),
            'boundary:administrative' => array('label' => 'Administrative', 'frequency' => 413, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'boundary:postal_code' => array('label' => 'Postcode', 'frequency' => 413, 'icon' => 'poi_boundary_administrative', 'defdiameter' => 0.32),
            'place:town' => array('label' => 'Town', 'frequency' => 1497, 'icon' => 'poi_place_town', 'defzoom' => 14, 'defdiameter' => 0.08),
            'place:village' => array('label' => 'Village', 'frequency' => 11230, 'icon' => 'poi_place_village', 'defzoom' => 15, 'defdiameter' => 0.04),
            'place:hamlet' => array('label' => 'Hamlet', 'frequency' => 7075, 'icon' => 'poi_place_village', 'defzoom' => 15, 'defdiameter' => 0.04),
            'place:suburb' => array('label' => 'Suburb', 'frequency' => 2528, 'icon' => 'poi_place_village', 'defdiameter' => 0.04),
            'place:locality' => array('label' => 'Locality', 'frequency' => 4113, 'icon' => 'poi_place_village', 'defdiameter' => 0.02),
            'landuse:farm' => array('label' => 'Farm', 'frequency' => 1201, 'defdiameter' => 0.02),
            'place:farm' => array('label' => 'Farm', 'frequency' => 1162, 'defdiameter' => 0.02),

            'highway:motorway_junction' => array('label' => 'Motorway Junction', 'frequency' => 1126, 'simplelabel' => 'Junction'),
            'highway:motorway' => array('label' => 'Motorway', 'frequency' => 4627, 'simplelabel' => 'Road'),
            'highway:trunk' => array('label' => 'Trunk', 'frequency' => 23084, 'simplelabel' => 'Road'),
            'highway:primary' => array('label' => 'Primary', 'frequency' => 32138, 'simplelabel' => 'Road'),
            'highway:secondary' => array('label' => 'Secondary', 'frequency' => 25807, 'simplelabel' => 'Road'),
            'highway:tertiary' => array('label' => 'Tertiary', 'frequency' => 29829, 'simplelabel' => 'Road'),
            'highway:residential' => array('label' => 'Residential', 'frequency' => 361498, 'simplelabel' => 'Road'),
            'highway:unclassified' => array('label' => 'Unclassified', 'frequency' => 66441, 'simplelabel' => 'Road'),
            'highway:living_street' => array('label' => 'Living Street', 'frequency' => 710, 'simplelabel' => 'Road'),
            'highway:service' => array('label' => 'Service', 'frequency' => 9963, 'simplelabel' => 'Road'),
            'highway:track' => array('label' => 'Track', 'frequency' => 2565, 'simplelabel' => 'Road'),
            'highway:road' => array('label' => 'Road', 'frequency' => 591, 'simplelabel' => 'Road'),
            'highway:byway' => array('label' => 'Byway', 'frequency' => 346, 'simplelabel' => 'Road'),
            'highway:bridleway' => array('label' => 'Bridleway', 'frequency' => 1556),
            'highway:cycleway' => array('label' => 'Cycleway', 'frequency' => 2419),
            'highway:pedestrian' => array('label' => 'Pedestrian', 'frequency' => 2757),
            'highway:footway' => array('label' => 'Footway', 'frequency' => 15008),
            'highway:steps' => array('label' => 'Steps', 'frequency' => 444, 'simplelabel' => 'Footway'),
            'highway:motorway_link' => array('label' => 'Motorway Link', 'frequency' => 795, 'simplelabel' => 'Road'),
            'highway:trunk_link' => array('label' => 'Trunk Link', 'frequency' => 1258, 'simplelabel' => 'Road'),
            'highway:primary_link' => array('label' => 'Primary Link', 'frequency' => 313, 'simplelabel' => 'Road'),

            'landuse:industrial' => array('label' => 'Industrial', 'frequency' => 1062),
            'landuse:residential' => array('label' => 'Residential', 'frequency' => 886),
            'landuse:retail' => array('label' => 'Retail', 'frequency' => 754),
            'landuse:commercial' => array('label' => 'Commercial', 'frequency' => 657),

            'place:airport' => array('label' => 'Airport', 'frequency' => 36, 'icon' => 'transport_airport2', 'defdiameter' => 0.03),
            'aeroway:aerodrome' => array('label' => 'Aerodrome', 'frequency' => 36, 'icon' => 'transport_airport2', 'defdiameter' => 0.03),
            'aeroway' => array('label' => 'Aeroway', 'frequency' => 36, 'icon' => 'transport_airport2', 'defdiameter' => 0.03),
            'railway:station' => array('label' => 'Station', 'frequency' => 3431, 'icon' => 'transport_train_station2', 'defdiameter' => 0.01),
            'amenity:place_of_worship' => array('label' => 'Place Of Worship', 'frequency' => 9049, 'icon' => 'place_of_worship_unknown3'),
            'amenity:pub' => array('label' => 'Pub', 'frequency' => 18969, 'icon' => 'food_pub'),
            'amenity:bar' => array('label' => 'Bar', 'frequency' => 164, 'icon' => 'food_bar'),
            'amenity:university' => array('label' => 'University', 'frequency' => 607, 'icon' => 'education_university'),
            'tourism:museum' => array('label' => 'Museum', 'frequency' => 543, 'icon' => 'tourist_museum'),
            'amenity:arts_centre' => array('label' => 'Arts Centre', 'frequency' => 136, 'icon' => 'tourist_art_gallery2'),
            'tourism:zoo' => array('label' => 'Zoo', 'frequency' => 47, 'icon' => 'tourist_zoo'),
            'tourism:theme_park' => array('label' => 'Theme Park', 'frequency' => 24, 'icon' => 'poi_point_of_interest'),
            'tourism:attraction' => array('label' => 'Attraction', 'frequency' => 1463, 'icon' => 'poi_point_of_interest'),
            'leisure:golf_course' => array('label' => 'Golf Course', 'frequency' => 712, 'icon' => 'sport_golf'),
            'historic:castle' => array('label' => 'Castle', 'frequency' => 316, 'icon' => 'tourist_castle'),
            'amenity:hospital' => array('label' => 'Hospital', 'frequency' => 879, 'icon' => 'health_hospital'),
            'amenity:school' => array('label' => 'School', 'frequency' => 8192, 'icon' => 'education_school'),
            'amenity:theatre' => array('label' => 'Theatre', 'frequency' => 371, 'icon' => 'tourist_theatre'),
            'amenity:public_building' => array('label' => 'Public Building', 'frequency' => 985),
            'amenity:library' => array('label' => 'Library', 'frequency' => 794, 'icon' => 'amenity_library'),
            'amenity:townhall' => array('label' => 'Townhall', 'frequency' => 242),
            'amenity:community_centre' => array('label' => 'Community Centre', 'frequency' => 157),
            'amenity:fire_station' => array('label' => 'Fire Station', 'frequency' => 221, 'icon' => 'amenity_firestation3'),
            'amenity:police' => array('label' => 'Police', 'frequency' => 334, 'icon' => 'amenity_police2'),
            'amenity:bank' => array('label' => 'Bank', 'frequency' => 1248, 'icon' => 'money_bank2'),
            'amenity:post_office' => array('label' => 'Post Office', 'frequency' => 859, 'icon' => 'amenity_post_office'),
            'leisure:park' => array('label' => 'Park', 'frequency' => 2378),
            'amenity:park' => array('label' => 'Park', 'frequency' => 53),
            'landuse:park' => array('label' => 'Park', 'frequency' => 50),
            'landuse:recreation_ground' => array('label' => 'Recreation Ground', 'frequency' => 517),
            'tourism:hotel' => array('label' => 'Hotel', 'frequency' => 2150, 'icon' => 'accommodation_hotel2'),
            'tourism:motel' => array('label' => 'Motel', 'frequency' => 43),
            'amenity:cinema' => array('label' => 'Cinema', 'frequency' => 277, 'icon' => 'tourist_cinema'),
            'tourism:artwork' => array('label' => 'Artwork', 'frequency' => 171, 'icon' => 'tourist_art_gallery2'),
            'historic:archaeological_site' => array('label' => 'Archaeological Site', 'frequency' => 407, 'icon' => 'tourist_archaeological2'),
            'amenity:doctors' => array('label' => 'Doctors', 'frequency' => 581, 'icon' => 'health_doctors'),
            'leisure:sports_centre' => array('label' => 'Sports Centre', 'frequency' => 767, 'icon' => 'sport_leisure_centre'),
            'leisure:swimming_pool' => array('label' => 'Swimming Pool', 'frequency' => 24, 'icon' => 'sport_swimming_outdoor'),
            'shop:supermarket' => array('label' => 'Supermarket', 'frequency' => 2673, 'icon' => 'shopping_supermarket'),
            'shop:convenience' => array('label' => 'Convenience', 'frequency' => 1469, 'icon' => 'shopping_convenience'),
            'amenity:restaurant' => array('label' => 'Restaurant', 'frequency' => 3179, 'icon' => 'food_restaurant'),
            'amenity:fast_food' => array('label' => 'Fast Food', 'frequency' => 2289, 'icon' => 'food_fastfood'),
            'amenity:cafe' => array('label' => 'Cafe', 'frequency' => 1780, 'icon' => 'food_cafe'),
            'tourism:guest_house' => array('label' => 'Guest House', 'frequency' => 223, 'icon' => 'accommodation_bed_and_breakfast'),
            'amenity:pharmacy' => array('label' => 'Pharmacy', 'frequency' => 733, 'icon' => 'health_pharmacy_dispensing'),
            'amenity:fuel' => array('label' => 'Fuel', 'frequency' => 1308, 'icon' => 'transport_fuel'),
            'natural:peak' => array('label' => 'Peak', 'frequency' => 3212, 'icon' => 'poi_peak'),
            'waterway:waterfall' => array('label' => 'Waterfall', 'frequency' => 24),
            'natural:wood' => array('label' => 'Wood', 'frequency' => 1845, 'icon' => 'landuse_coniferous_and_deciduous'),
            'natural:water' => array('label' => 'Water', 'frequency' => 1790),
            'landuse:forest' => array('label' => 'Forest', 'frequency' => 467),
            'landuse:cemetery' => array('label' => 'Cemetery', 'frequency' => 463),
            'landuse:allotments' => array('label' => 'Allotments', 'frequency' => 408),
            'landuse:farmyard' => array('label' => 'Farmyard', 'frequency' => 397),
            'railway:rail' => array('label' => 'Rail', 'frequency' => 4894),
            'waterway:canal' => array('label' => 'Canal', 'frequency' => 1723),
            'waterway:river' => array('label' => 'River', 'frequency' => 4089),
            'waterway:stream' => array('label' => 'Stream', 'frequency' => 2684),
            'shop:bicycle' => array('label' => 'Bicycle', 'frequency' => 349, 'icon' => 'shopping_bicycle'),
            'shop:clothes' => array('label' => 'Clothes', 'frequency' => 315, 'icon' => 'shopping_clothes'),
            'shop:hairdresser' => array('label' => 'Hairdresser', 'frequency' => 312, 'icon' => 'shopping_hairdresser'),
            'shop:doityourself' => array('label' => 'Doityourself', 'frequency' => 247, 'icon' => 'shopping_diy'),
            'shop:estate_agent' => array('label' => 'Estate Agent', 'frequency' => 162, 'icon' => 'shopping_estateagent2'),
            'shop:car' => array('label' => 'Car', 'frequency' => 159, 'icon' => 'shopping_car'),
            'shop:garden_centre' => array('label' => 'Garden Centre', 'frequency' => 143, 'icon' => 'shopping_garden_centre'),
            'shop:car_repair' => array('label' => 'Car Repair', 'frequency' => 141, 'icon' => 'shopping_car_repair'),
            'shop:newsagent' => array('label' => 'Newsagent', 'frequency' => 132),
            'shop:bakery' => array('label' => 'Bakery', 'frequency' => 129, 'icon' => 'shopping_bakery'),
            'shop:furniture' => array('label' => 'Furniture', 'frequency' => 124),
            'shop:butcher' => array('label' => 'Butcher', 'frequency' => 105, 'icon' => 'shopping_butcher'),
            'shop:apparel' => array('label' => 'Apparel', 'frequency' => 98, 'icon' => 'shopping_clothes'),
            'shop:electronics' => array('label' => 'Electronics', 'frequency' => 96),
            'shop:department_store' => array('label' => 'Department Store', 'frequency' => 86),
            'shop:books' => array('label' => 'Books', 'frequency' => 85),
            'shop:yes' => array('label' => 'Shop', 'frequency' => 68),
            'shop:outdoor' => array('label' => 'Outdoor', 'frequency' => 67),
            'shop:mall' => array('label' => 'Mall', 'frequency' => 63),
            'shop:florist' => array('label' => 'Florist', 'frequency' => 61),
            'shop:charity' => array('label' => 'Charity', 'frequency' => 60),
            'shop:hardware' => array('label' => 'Hardware', 'frequency' => 59),
            'shop:laundry' => array('label' => 'Laundry', 'frequency' => 51, 'icon' => 'shopping_laundrette'),
            'shop:shoes' => array('label' => 'Shoes', 'frequency' => 49),
            'shop:beverages' => array('label' => 'Beverages', 'frequency' => 48, 'icon' => 'shopping_alcohol'),
            'shop:dry_cleaning' => array('label' => 'Dry Cleaning', 'frequency' => 46),
            'shop:carpet' => array('label' => 'Carpet', 'frequency' => 45),
            'shop:computer' => array('label' => 'Computer', 'frequency' => 44),
            'shop:alcohol' => array('label' => 'Alcohol', 'frequency' => 44, 'icon' => 'shopping_alcohol'),
            'shop:optician' => array('label' => 'Optician', 'frequency' => 55, 'icon' => 'health_opticians'),
            'shop:chemist' => array('label' => 'Chemist', 'frequency' => 42, 'icon' => 'health_pharmacy'),
            'shop:gallery' => array('label' => 'Gallery', 'frequency' => 38, 'icon' => 'tourist_art_gallery2'),
            'shop:mobile_phone' => array('label' => 'Mobile Phone', 'frequency' => 37),
            'shop:sports' => array('label' => 'Sports', 'frequency' => 37),
            'shop:jewelry' => array('label' => 'Jewelry', 'frequency' => 32, 'icon' => 'shopping_jewelry'),
            'shop:pet' => array('label' => 'Pet', 'frequency' => 29),
            'shop:beauty' => array('label' => 'Beauty', 'frequency' => 28),
            'shop:stationery' => array('label' => 'Stationery', 'frequency' => 25),
            'shop:shopping_centre' => array('label' => 'Shopping Centre', 'frequency' => 25),
            'shop:general' => array('label' => 'General', 'frequency' => 25),
            'shop:electrical' => array('label' => 'Electrical', 'frequency' => 25),
            'shop:toys' => array('label' => 'Toys', 'frequency' => 23),
            'shop:jeweller' => array('label' => 'Jeweller', 'frequency' => 23),
            'shop:betting' => array('label' => 'Betting', 'frequency' => 23),
            'shop:household' => array('label' => 'Household', 'frequency' => 21),
            'shop:travel_agency' => array('label' => 'Travel Agency', 'frequency' => 21),
            'shop:hifi' => array('label' => 'Hifi', 'frequency' => 21),
            'amenity:shop' => array('label' => 'Shop', 'frequency' => 61),
            'tourism:information' => array('label' => 'Information', 'frequency' => 224, 'icon' => 'amenity_information'),

            'place:house' => array('label' => 'House', 'frequency' => 2086, 'defzoom' => 18),
            'place:house_name' => array('label' => 'House', 'frequency' => 2086, 'defzoom' => 18),
            'place:house_number' => array('label' => 'House Number', 'frequency' => 2086, 'defzoom' => 18),
            'place:country_code' => array('label' => 'Country Code', 'frequency' => 2086, 'defzoom' => 18),

            //

            'leisure:pitch' => array('label' => 'Pitch', 'frequency' => 762),
            'highway:unsurfaced' => array('label' => 'Unsurfaced', 'frequency' => 492),
            'historic:ruins' => array('label' => 'Ruins', 'frequency' => 483, 'icon' => 'tourist_ruin'),
            'amenity:college' => array('label' => 'College', 'frequency' => 473, 'icon' => 'education_school'),
            'historic:monument' => array('label' => 'Monument', 'frequency' => 470, 'icon' => 'tourist_monument'),
            'railway:subway' => array('label' => 'Subway', 'frequency' => 385),
            'historic:memorial' => array('label' => 'Memorial', 'frequency' => 382, 'icon' => 'tourist_monument'),
            'leisure:nature_reserve' => array('label' => 'Nature Reserve', 'frequency' => 342),
            'leisure:common' => array('label' => 'Common', 'frequency' => 322),
            'waterway:lock_gate' => array('label' => 'Lock Gate', 'frequency' => 321),
            'natural:fell' => array('label' => 'Fell', 'frequency' => 308),
            'amenity:nightclub' => array('label' => 'Nightclub', 'frequency' => 292),
            'highway:path' => array('label' => 'Path', 'frequency' => 287),
            'leisure:garden' => array('label' => 'Garden', 'frequency' => 285),
            'landuse:reservoir' => array('label' => 'Reservoir', 'frequency' => 276),
            'leisure:playground' => array('label' => 'Playground', 'frequency' => 264),
            'leisure:stadium' => array('label' => 'Stadium', 'frequency' => 212),
            'historic:mine' => array('label' => 'Mine', 'frequency' => 193, 'icon' => 'poi_mine'),
            'natural:cliff' => array('label' => 'Cliff', 'frequency' => 193),
            'tourism:caravan_site' => array('label' => 'Caravan Site', 'frequency' => 183, 'icon' => 'accommodation_caravan_park'),
            'amenity:bus_station' => array('label' => 'Bus Station', 'frequency' => 181, 'icon' => 'transport_bus_station'),
            'amenity:kindergarten' => array('label' => 'Kindergarten', 'frequency' => 179),
            'highway:construction' => array('label' => 'Construction', 'frequency' => 176),
            'amenity:atm' => array('label' => 'Atm', 'frequency' => 172, 'icon' => 'money_atm2'),
            'amenity:emergency_phone' => array('label' => 'Emergency Phone', 'frequency' => 164),
            'waterway:lock' => array('label' => 'Lock', 'frequency' => 146),
            'waterway:riverbank' => array('label' => 'Riverbank', 'frequency' => 143),
            'natural:coastline' => array('label' => 'Coastline', 'frequency' => 142),
            'tourism:viewpoint' => array('label' => 'Viewpoint', 'frequency' => 140, 'icon' => 'tourist_view_point'),
            'tourism:hostel' => array('label' => 'Hostel', 'frequency' => 140),
            'tourism:bed_and_breakfast' => array('label' => 'Bed And Breakfast', 'frequency' => 140, 'icon' => 'accommodation_bed_and_breakfast'),
            'railway:halt' => array('label' => 'Halt', 'frequency' => 135),
            'railway:platform' => array('label' => 'Platform', 'frequency' => 134),
            'railway:tram' => array('label' => 'Tram', 'frequency' => 130, 'icon' => 'transport_tram_stop'),
            'amenity:courthouse' => array('label' => 'Courthouse', 'frequency' => 129, 'icon' => 'amenity_court'),
            'amenity:recycling' => array('label' => 'Recycling', 'frequency' => 126, 'icon' => 'amenity_recycling'),
            'amenity:dentist' => array('label' => 'Dentist', 'frequency' => 124, 'icon' => 'health_dentist'),
            'natural:beach' => array('label' => 'Beach', 'frequency' => 121, 'icon' => 'tourist_beach'),
            'place:moor' => array('label' => 'Moor', 'frequency' => 118),
            'amenity:grave_yard' => array('label' => 'Grave Yard', 'frequency' => 110),
            'waterway:drain' => array('label' => 'Drain', 'frequency' => 108),
            'landuse:grass' => array('label' => 'Grass', 'frequency' => 106),
            'landuse:village_green' => array('label' => 'Village Green', 'frequency' => 106),
            'natural:bay' => array('label' => 'Bay', 'frequency' => 102),
            'railway:tram_stop' => array('label' => 'Tram Stop', 'frequency' => 101, 'icon' => 'transport_tram_stop'),
            'leisure:marina' => array('label' => 'Marina', 'frequency' => 98),
            'highway:stile' => array('label' => 'Stile', 'frequency' => 97),
            'natural:moor' => array('label' => 'Moor', 'frequency' => 95),
            'railway:light_rail' => array('label' => 'Light Rail', 'frequency' => 91),
            'railway:narrow_gauge' => array('label' => 'Narrow Gauge', 'frequency' => 90),
            'natural:land' => array('label' => 'Land', 'frequency' => 86),
            'amenity:village_hall' => array('label' => 'Village Hall', 'frequency' => 82),
            'waterway:dock' => array('label' => 'Dock', 'frequency' => 80),
            'amenity:veterinary' => array('label' => 'Veterinary', 'frequency' => 79),
            'landuse:brownfield' => array('label' => 'Brownfield', 'frequency' => 77),
            'leisure:track' => array('label' => 'Track', 'frequency' => 76),
            'railway:historic_station' => array('label' => 'Historic Station', 'frequency' => 74),
            'landuse:construction' => array('label' => 'Construction', 'frequency' => 72),
            'amenity:prison' => array('label' => 'Prison', 'frequency' => 71, 'icon' => 'amenity_prison'),
            'landuse:quarry' => array('label' => 'Quarry', 'frequency' => 71),
            'amenity:telephone' => array('label' => 'Telephone', 'frequency' => 70),
            'highway:traffic_signals' => array('label' => 'Traffic Signals', 'frequency' => 66),
            'natural:heath' => array('label' => 'Heath', 'frequency' => 62),
            'historic:house' => array('label' => 'House', 'frequency' => 61),
            'amenity:social_club' => array('label' => 'Social Club', 'frequency' => 61),
            'landuse:military' => array('label' => 'Military', 'frequency' => 61),
            'amenity:health_centre' => array('label' => 'Health Centre', 'frequency' => 59),
            'historic:building' => array('label' => 'Building', 'frequency' => 58),
            'amenity:clinic' => array('label' => 'Clinic', 'frequency' => 57),
            'highway:services' => array('label' => 'Services', 'frequency' => 56),
            'amenity:ferry_terminal' => array('label' => 'Ferry Terminal', 'frequency' => 55),
            'natural:marsh' => array('label' => 'Marsh', 'frequency' => 55),
            'natural:hill' => array('label' => 'Hill', 'frequency' => 54),
            'highway:raceway' => array('label' => 'Raceway', 'frequency' => 53),
            'amenity:taxi' => array('label' => 'Taxi', 'frequency' => 47),
            'amenity:take_away' => array('label' => 'Take Away', 'frequency' => 45),
            'amenity:car_rental' => array('label' => 'Car Rental', 'frequency' => 44),
            'place:islet' => array('label' => 'Islet', 'frequency' => 44),
            'amenity:nursery' => array('label' => 'Nursery', 'frequency' => 44),
            'amenity:nursing_home' => array('label' => 'Nursing Home', 'frequency' => 43),
            'amenity:toilets' => array('label' => 'Toilets', 'frequency' => 38),
            'amenity:hall' => array('label' => 'Hall', 'frequency' => 38),
            'waterway:boatyard' => array('label' => 'Boatyard', 'frequency' => 36),
            'highway:mini_roundabout' => array('label' => 'Mini Roundabout', 'frequency' => 35),
            'historic:manor' => array('label' => 'Manor', 'frequency' => 35),
            'tourism:chalet' => array('label' => 'Chalet', 'frequency' => 34),
            'amenity:bicycle_parking' => array('label' => 'Bicycle Parking', 'frequency' => 34),
            'amenity:hotel' => array('label' => 'Hotel', 'frequency' => 34),
            'waterway:weir' => array('label' => 'Weir', 'frequency' => 33),
            'natural:wetland' => array('label' => 'Wetland', 'frequency' => 33),
            'natural:cave_entrance' => array('label' => 'Cave Entrance', 'frequency' => 32),
            'amenity:crematorium' => array('label' => 'Crematorium', 'frequency' => 31),
            'tourism:picnic_site' => array('label' => 'Picnic Site', 'frequency' => 31),
            'landuse:wood' => array('label' => 'Wood', 'frequency' => 30),
            'landuse:basin' => array('label' => 'Basin', 'frequency' => 30),
            'natural:tree' => array('label' => 'Tree', 'frequency' => 30),
            'leisure:slipway' => array('label' => 'Slipway', 'frequency' => 29),
            'landuse:meadow' => array('label' => 'Meadow', 'frequency' => 29),
            'landuse:piste' => array('label' => 'Piste', 'frequency' => 28),
            'amenity:care_home' => array('label' => 'Care Home', 'frequency' => 28),
            'amenity:club' => array('label' => 'Club', 'frequency' => 28),
            'amenity:medical_centre' => array('label' => 'Medical Centre', 'frequency' => 27),
            'historic:roman_road' => array('label' => 'Roman Road', 'frequency' => 27),
            'historic:fort' => array('label' => 'Fort', 'frequency' => 26),
            'railway:subway_entrance' => array('label' => 'Subway Entrance', 'frequency' => 26),
            'historic:yes' => array('label' => 'Historic', 'frequency' => 25),
            'highway:gate' => array('label' => 'Gate', 'frequency' => 25),
            'leisure:fishing' => array('label' => 'Fishing', 'frequency' => 24),
            'historic:museum' => array('label' => 'Museum', 'frequency' => 24),
            'amenity:car_wash' => array('label' => 'Car Wash', 'frequency' => 24),
            'railway:level_crossing' => array('label' => 'Level Crossing', 'frequency' => 23),
            'leisure:bird_hide' => array('label' => 'Bird Hide', 'frequency' => 23),
            'natural:headland' => array('label' => 'Headland', 'frequency' => 21),
            'tourism:apartments' => array('label' => 'Apartments', 'frequency' => 21),
            'amenity:shopping' => array('label' => 'Shopping', 'frequency' => 21),
            'natural:scrub' => array('label' => 'Scrub', 'frequency' => 20),
            'natural:fen' => array('label' => 'Fen', 'frequency' => 20),
            'building:yes' => array('label' => 'Building', 'frequency' => 200),
            'mountain_pass:yes' => array('label' => 'Mountain Pass', 'frequency' => 200),

            'amenity:parking' => array('label' => 'Parking', 'frequency' => 3157),
            'highway:bus_stop' => array('label' => 'Bus Stop', 'frequency' => 35777, 'icon' => 'transport_bus_stop2'),
            'place:postcode' => array('label' => 'Postcode', 'frequency' => 27267),
            'amenity:post_box' => array('label' => 'Post Box', 'frequency' => 9613),

            'place:houses' => array('label' => 'Houses', 'frequency' => 85),
            'railway:preserved' => array('label' => 'Preserved', 'frequency' => 227),
            'waterway:derelict_canal' => array('label' => 'Derelict Canal', 'frequency' => 21),
            'amenity:dead_pub' => array('label' => 'Dead Pub', 'frequency' => 20),
            'railway:disused_station' => array('label' => 'Disused Station', 'frequency' => 114),
            'railway:abandoned' => array('label' => 'Abandoned', 'frequency' => 641),
            'railway:disused' => array('label' => 'Disused', 'frequency' => 72),
           );
}
