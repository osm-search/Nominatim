PSQL=/usr/lib/postgresql/9.2/bin/psql -d wikidata

cat create.sql | $PSQL

cat entity.csv | $PSQL -c "COPY entity from STDIN WITH CSV"
cat entity_label.csv | $PSQL -c "COPY entity_label from STDIN WITH CSV"
cat entity_description.csv | $PSQL -c "COPY entity_description from STDIN WITH CSV"
cat entity_alias.csv | $PSQL -c "COPY entity_alias from STDIN WITH CSV"
cat entity_link.csv | $PSQL -c "COPY entity_link from STDIN WITH CSV"
cat entity_property.csv | $PSQL -c "COPY entity_property from STDIN WITH CSV"

$PSQL -c "create index idx_entity_link_target on entity_link using btree (target,value)"
$PSQL -c "create index idx_entity_qid on entity using btree (qid)"
$PSQL -c "create table property_label_en as select pid,null::text as label from entity where pid is not null"
$PSQL -c "update property_label_en set label = x.label from (select pid,label,language from entity join entity_label using (entity_id) where pid is not null and language = 'en') as x where x.pid = property_label_en.pid"
$PSQL -c "create unique index idx_property_label_en on property_label_en using btree (pid)"
$PSQL -c "alter table entity add column label_en text"
$PSQL -c "update entity set label_en = label from entity_label where entity.entity_id = entity_label.entity_id and language = 'en'"
$PSQL -c "alter table entity add column description_en text"
$PSQL -c "update entity set description_en = description from entity_description where entity.entity_id = entity_description.entity_id and language = 'en'"

cat totals.txt | $PSQL -c "COPY import_link_hit from STDIN WITH CSV DELIMITER ' '"
$PSQL -c "truncate link_hit"
$PSQL -c "insert into link_hit select target||'wiki', replace(catch_decode_url_part(value), '_', ' '), sum(hits) from import_link_hit where replace(catch_decode_url_part(value), '_', ' ') is not null group by target||'wiki', replace(dcatch_decode_url_part(value), '_', ' ')"
$PSQL -c "truncate entity_link_hit"
$PSQL -c "insert into entity_link_hit select entity_id, target, value, coalesce(hits,0) from entity_link left outer join link_hit using (target, value)"
$PSQL -c "create table entity_hit as select entity_id,sum(hits) as hits from entity_link_hit group by entity_id"
$PSQL -c "create unique index idx_entity_hit on entity_hit using btree (entity_id)"
