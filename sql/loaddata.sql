TRUNCATE placex;
TRUNCATE search_name;
TRUNCATE place_addressline;
TRUNCATE location_area;

DROP SEQUENCE seq_place;
CREATE SEQUENCE seq_place start 100000;

insert into placex (osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, extratags, geometry)
             select osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, extratags, geometry from place where osm_type = 'N';
insert into placex (osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, extratags, geometry)
             select osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, extratags, geometry from place where osm_type = 'W';
insert into placex (osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, extratags, geometry)
             select osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, country_code, extratags, geometry from place where osm_type = 'R';

--select count(*) from (select create_interpolation(osm_id, housenumber) from placex where indexed=false and class='place' and type='houses') as x;
