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
-- Name: country_name; Type: TABLE; Schema: public; Owner: brian; Tablespace: 
--

CREATE TABLE country_name (
    country_code character varying(2),
    name hstore,
    country_default_language_code character varying(2),
    partition integer
);

--
-- Data for Name: country_name; Type: TABLE DATA; Schema: public; Owner: brian
--

\COPY country_name (country_code, name, country_default_language_code, partition) FROM pstdin


--
-- Name: idx_country_name_country_code; Type: INDEX; Schema: public; Owner: brian; Tablespace: 
--

CREATE INDEX idx_country_name_country_code ON country_name USING btree (country_code);


--
-- Name: country_name; Type: ACL; Schema: public; Owner: brian
--

REVOKE ALL ON TABLE country_name FROM PUBLIC;
GRANT SELECT ON TABLE country_name TO "www-data";


--
-- PostgreSQL database dump complete
--

