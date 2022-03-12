--
-- PostgreSQL database dump
--

CREATE TABLE public.country_name (
    country_code character varying(2),
    name public.hstore,
    derived_name public.hstore,
    country_default_language_code text,
    partition integer
);
