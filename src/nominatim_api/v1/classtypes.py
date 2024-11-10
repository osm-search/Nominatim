# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Hard-coded information about tag categories.

These tables have been copied verbatim from the old PHP code. For future
version a more flexible formatting is required.
"""
from typing import Tuple, Optional, Mapping, Union

from ..results import ReverseResult, SearchResult
from ..types import Bbox


def get_label_tag(category: Tuple[str, str], extratags: Optional[Mapping[str, str]],
                  rank: int, country: Optional[str]) -> str:
    """ Create a label tag for the given place that can be used as an XML name.
    """
    if rank < 26 and extratags and 'place' in extratags:
        label = extratags['place']
    elif rank < 26 and extratags and 'linked_place' in extratags:
        label = extratags['linked_place']
    elif category == ('boundary', 'administrative'):
        label = ADMIN_LABELS.get((country or '', int(rank/2)))\
                or ADMIN_LABELS.get(('', int(rank/2)))\
                or 'Administrative'
    elif category[1] == 'postal_code':
        label = 'postcode'
    elif rank < 26:
        label = category[1] if category[1] != 'yes' else category[0]
    elif rank < 28:
        label = 'road'
    elif (category[0] == 'place'
          and category[1] in ('house_number', 'house_name', 'country_code')):
        label = category[1]
    else:
        label = category[0]

    return label.lower().replace(' ', '_')


def bbox_from_result(result: Union[ReverseResult, SearchResult]) -> Bbox:
    """ Compute a bounding box for the result. For ways and relations
        a given boundingbox is used. For all other object, a box is computed
        around the centroid according to dimensions derived from the
        search rank.
    """
    if result.category == ('place', 'postcode') and result.bbox is None:
        return Bbox.from_point(result.centroid,
                               0.05 - 0.012 * (result.rank_search - 21))

    if (result.osm_object and result.osm_object[0] == 'N') or result.bbox is None:

        extent = NODE_EXTENT.get(result.category, 0.00005)
        return Bbox.from_point(result.centroid, extent)

    return result.bbox


# pylint: disable=line-too-long
OSM_ATTRIBUTION = 'Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright'


OSM_TYPE_NAME = {
    'N': 'node',
    'W': 'way',
    'R': 'relation'
}


ADMIN_LABELS = {
  ('', 1): 'Continent',
  ('', 2): 'Country',
  ('', 3): 'Region',
  ('', 4): 'State',
  ('', 5): 'State District',
  ('', 6): 'County',
  ('', 7): 'Municipality',
  ('', 8): 'City',
  ('', 9): 'City District',
  ('', 10): 'Suburb',
  ('', 11): 'Neighbourhood',
  ('', 12): 'City Block',
  ('no', 3): 'State',
  ('no', 4): 'County',
  ('se', 3): 'State',
  ('se', 4): 'County'
}


ICONS = {
    ('boundary', 'administrative'): 'poi_boundary_administrative',
    ('place', 'city'): 'poi_place_city',
    ('place', 'town'): 'poi_place_town',
    ('place', 'village'): 'poi_place_village',
    ('place', 'hamlet'): 'poi_place_village',
    ('place', 'suburb'): 'poi_place_village',
    ('place', 'locality'): 'poi_place_village',
    ('place', 'airport'): 'transport_airport2',
    ('aeroway', 'aerodrome'): 'transport_airport2',
    ('railway', 'station'): 'transport_train_station2',
    ('amenity', 'place_of_worship'): 'place_of_worship_unknown3',
    ('amenity', 'pub'): 'food_pub',
    ('amenity', 'bar'): 'food_bar',
    ('amenity', 'university'): 'education_university',
    ('tourism', 'museum'): 'tourist_museum',
    ('amenity', 'arts_centre'): 'tourist_art_gallery2',
    ('tourism', 'zoo'): 'tourist_zoo',
    ('tourism', 'theme_park'): 'poi_point_of_interest',
    ('tourism', 'attraction'): 'poi_point_of_interest',
    ('leisure', 'golf_course'): 'sport_golf',
    ('historic', 'castle'): 'tourist_castle',
    ('amenity', 'hospital'): 'health_hospital',
    ('amenity', 'school'): 'education_school',
    ('amenity', 'theatre'): 'tourist_theatre',
    ('amenity', 'library'): 'amenity_library',
    ('amenity', 'fire_station'): 'amenity_firestation3',
    ('amenity', 'police'): 'amenity_police2',
    ('amenity', 'bank'): 'money_bank2',
    ('amenity', 'post_office'): 'amenity_post_office',
    ('tourism', 'hotel'): 'accommodation_hotel2',
    ('amenity', 'cinema'): 'tourist_cinema',
    ('tourism', 'artwork'): 'tourist_art_gallery2',
    ('historic', 'archaeological_site'): 'tourist_archaeological2',
    ('amenity', 'doctors'): 'health_doctors',
    ('leisure', 'sports_centre'): 'sport_leisure_centre',
    ('leisure', 'swimming_pool'): 'sport_swimming_outdoor',
    ('shop', 'supermarket'): 'shopping_supermarket',
    ('shop', 'convenience'): 'shopping_convenience',
    ('amenity', 'restaurant'): 'food_restaurant',
    ('amenity', 'fast_food'): 'food_fastfood',
    ('amenity', 'cafe'): 'food_cafe',
    ('tourism', 'guest_house'): 'accommodation_bed_and_breakfast',
    ('amenity', 'pharmacy'): 'health_pharmacy_dispensing',
    ('amenity', 'fuel'): 'transport_fuel',
    ('natural', 'peak'): 'poi_peak',
    ('natural', 'wood'): 'landuse_coniferous_and_deciduous',
    ('shop', 'bicycle'): 'shopping_bicycle',
    ('shop', 'clothes'): 'shopping_clothes',
    ('shop', 'hairdresser'): 'shopping_hairdresser',
    ('shop', 'doityourself'): 'shopping_diy',
    ('shop', 'estate_agent'): 'shopping_estateagent2',
    ('shop', 'car'): 'shopping_car',
    ('shop', 'garden_centre'): 'shopping_garden_centre',
    ('shop', 'car_repair'): 'shopping_car_repair',
    ('shop', 'bakery'): 'shopping_bakery',
    ('shop', 'butcher'): 'shopping_butcher',
    ('shop', 'apparel'): 'shopping_clothes',
    ('shop', 'laundry'): 'shopping_laundrette',
    ('shop', 'beverages'): 'shopping_alcohol',
    ('shop', 'alcohol'): 'shopping_alcohol',
    ('shop', 'optician'): 'health_opticians',
    ('shop', 'chemist'): 'health_pharmacy',
    ('shop', 'gallery'): 'tourist_art_gallery2',
    ('shop', 'jewelry'): 'shopping_jewelry',
    ('tourism', 'information'): 'amenity_information',
    ('historic', 'ruins'): 'tourist_ruin',
    ('amenity', 'college'): 'education_school',
    ('historic', 'monument'): 'tourist_monument',
    ('historic', 'memorial'): 'tourist_monument',
    ('historic', 'mine'): 'poi_mine',
    ('tourism', 'caravan_site'): 'accommodation_caravan_park',
    ('amenity', 'bus_station'): 'transport_bus_station',
    ('amenity', 'atm'): 'money_atm2',
    ('tourism', 'viewpoint'): 'tourist_view_point',
    ('tourism', 'guesthouse'): 'accommodation_bed_and_breakfast',
    ('railway', 'tram'): 'transport_tram_stop',
    ('amenity', 'courthouse'): 'amenity_court',
    ('amenity', 'recycling'): 'amenity_recycling',
    ('amenity', 'dentist'): 'health_dentist',
    ('natural', 'beach'): 'tourist_beach',
    ('railway', 'tram_stop'): 'transport_tram_stop',
    ('amenity', 'prison'): 'amenity_prison',
    ('highway', 'bus_stop'): 'transport_bus_stop2'
}

NODE_EXTENT = {
    ('place', 'continent'): 25,
    ('place', 'country'): 7,
    ('place', 'state'): 2.6,
    ('place', 'province'): 2.6,
    ('place', 'region'): 1.0,
    ('place', 'county'): 0.7,
    ('place', 'city'): 0.16,
    ('place', 'municipality'): 0.16,
    ('place', 'island'): 0.32,
    ('place', 'postcode'): 0.16,
    ('place', 'town'): 0.04,
    ('place', 'village'): 0.02,
    ('place', 'hamlet'): 0.02,
    ('place', 'district'): 0.02,
    ('place', 'borough'): 0.02,
    ('place', 'suburb'): 0.02,
    ('place', 'locality'): 0.01,
    ('place', 'neighbourhood'): 0.01,
    ('place', 'quarter'): 0.01,
    ('place', 'city_block'): 0.01,
    ('landuse', 'farm'): 0.01,
    ('place', 'farm'): 0.01,
    ('place', 'airport'): 0.015,
    ('aeroway', 'aerodrome'): 0.015,
    ('railway', 'station'): 0.005
}
