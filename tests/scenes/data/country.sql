select country_code, st_astext(st_pointonsurface(st_collect(geometry))) from country_osm_grid group by country_code order by country_code
