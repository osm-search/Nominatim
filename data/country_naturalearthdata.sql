--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

CREATE TABLE country_naturalearthdata (
    country_code character varying(2),
    geometry geometry,
    CONSTRAINT enforce_dims_geometry CHECK ((st_ndims(geometry) = 2)),
    CONSTRAINT enforce_srid_geometry CHECK ((st_srid(geometry) = 4326))
);

\COPY country_naturalearthdata (country_code, geometry) FROM pstdin

CREATE INDEX idx_country_naturalearthdata_country_code ON country_naturalearthdata USING btree (country_code);
CREATE INDEX idx_country_naturalearthdata_geometry ON country_naturalearthdata USING gist (geometry);
