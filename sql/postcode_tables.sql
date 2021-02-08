DROP TABLE IF EXISTS gb_postcode;
CREATE TABLE gb_postcode (
    id integer,
    postcode character varying(9),
    geometry geometry,
    CONSTRAINT enforce_dims_geometry CHECK ((st_ndims(geometry) = 2)),
    CONSTRAINT enforce_srid_geometry CHECK ((st_srid(geometry) = 4326))
);

DROP TABLE IF EXISTS us_postcode;
CREATE TABLE us_postcode (
    postcode text,
    x double precision,
    y double precision
);
