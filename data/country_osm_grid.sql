--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: country_osm_grid; Type: TABLE; Schema: public; Owner: brian; Tablespace: 
--

CREATE TABLE country_osm_grid (
    country_code character varying(2),
    area double precision,
    geometry geometry
);

--
-- Data for Name: country_osm_grid; Type: TABLE DATA; Schema: public; Owner: brian
--

\COPY country_osm_grid (country_code, area, geometry) FROM pstdin;

--
-- Name: idx_country_osm_grid_geometry; Type: INDEX; Schema: public; Owner: brian; Tablespace: 
--

CREATE INDEX idx_country_osm_grid_geometry ON country_osm_grid USING gist (geometry);

GRANT SELECT ON TABLE country_osm_grid TO "www-data";

--
-- PostgreSQL database dump complete
--

