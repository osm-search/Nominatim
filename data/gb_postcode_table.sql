-- This data contains Ordnance Survey data © Crown copyright and database right 2010. 
-- Code-Point Open contains Royal Mail data © Royal Mail copyright and database right 2010.
-- OS data may be used under the terms of the OS OpenData licence:
-- http://www.ordnancesurvey.co.uk/oswebsite/opendata/licence/docs/licence.pdf

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET default_tablespace = '';

SET default_with_oids = false;

CREATE TABLE gb_postcode (
    id integer,
    postcode character varying(9),
    geometry geometry,
    CONSTRAINT enforce_dims_geometry CHECK ((st_ndims(geometry) = 2)),
    CONSTRAINT enforce_srid_geometry CHECK ((st_srid(geometry) = 4326))
);

