\a
\t
\o /tmp/bigintupdate.sql
select 'alter table "'||relname||'" alter '||attname||' type bigint;' from pg_attribute join pg_class on 
(attrelid = oid) where attname like '%place_id%' and attnum > 0 and relkind = 'r'::"char" and atttypid = 23 
and not relname::text ~ '^.*_[0-9]+$' order by 'alter table "'||relname||'" alter '||attname||' type 
bigint;';
\o
\i /tmp/bigintupdate.sql
