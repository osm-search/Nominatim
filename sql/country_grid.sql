drop table country_osm_grid2;
create table country_osm_grid2 as select country_name.country_code,st_union(placex.geometry) as geometry from country_name,
  placex
  where (lower(placex.country_code) = country_name.country_code)
    and placex.rank_search < 16 and st_area(placex.geometry)>0 
  group by country_name.country_code;
alter table country_osm_grid2 add column area double precision;
update country_osm_grid2 set area = st_area(geometry::geography);
drop table country_osm_grid3;
create table country_osm_grid3 as select country_code,area,quad_split_geometry(geometry,0.5,20) as geometry from country_osm_grid2;
drop table country_osm_grid;
alter table country_osm_grid3 rename to country_osm_grid;
CREATE INDEX idx_country_osm_grid_geometry ON country_osm_grid USING GIST (geometry);
update country_osm_grid set area = sum from (select country_code,sum(case when st_area(geometry::geography) = 'NaN' THEN 0 ELSE st_area(geometry::geography) END) 
 from country_osm_grid group by country_code) as x where x.country_code = country_osm_grid.country_code;
