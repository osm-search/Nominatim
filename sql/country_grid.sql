-- Script to build a calculated country grid from existing tables
DROP TABLE IF EXISTS tmp_country_osm_grid;
CREATE TABLE tmp_country_osm_grid as select country_name.country_code,st_union(placex.geometry) as geometry from country_name,
  placex
  where (lower(placex.country_code) = country_name.country_code)
    and placex.rank_search < 16 and st_area(placex.geometry) > 0 
  group by country_name.country_code;
ALTER TABLE tmp_country_osm_grid add column area double precision;
UPDATE tmp_country_osm_grid set area = st_area(geometry::geography);

-- compare old and new
select country_code, round, round(log(area)) from (select distinct country_code,round(log(area)) from country_osm_grid order by country_code) as x 
  left outer join tmp_country_osm_grid using (country_code) where area is null or round(log(area)) != round;

DROP TABLE IF EXISTS new_country_osm_grid;
CREATE TABLE new_country_osm_grid as select country_code,area,quad_split_geometry(geometry,0.5,20) as geometry from tmp_country_osm_grid;
CREATE INDEX new_idx_country_osm_grid_geometry ON new_country_osm_grid USING GIST (geometry);

-- Sometimes there are problems calculating area due to invalid data - optionally recalc
UPDATE new_country_osm_grid set area = sum from (select country_code,sum(case when st_area(geometry::geography) = 'NaN' THEN 0 ELSE st_area(geometry::geography) END) 
 from new_country_osm_grid group by country_code) as x where x.country_code = new_country_osm_grid.country_code;

-- compare old and new
select country_code, x.round, y.round from (select distinct country_code,round(log(area)) from country_osm_grid order by country_code) as x
  left outer join (select distinct country_code,round(log(area)) from new_country_osm_grid order by country_code) as y
    using (country_code) where x.round != y.round;

-- Flip the new table in
BEGIN;
DROP TABLE IF EXISTS country_osm_grid;
ALTER TABLE new_country_osm_grid rename to country_osm_grid;
ALTER INDEX new_idx_country_osm_grid_geometry RENAME TO idx_country_osm_grid_geometry;
COMMIT;
