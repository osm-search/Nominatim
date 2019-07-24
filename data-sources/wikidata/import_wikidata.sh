#!/bin/bash

psqlcmd() {
     psql wikidata2019
}

mysql2pgsqlcmd() {
     ./mysql2pgsql.perl /dev/stdin /dev/stdout
}

language=( "ar" "bg" "ca" "cs" "da" "de" "en" "es" "eo" "eu" "fa" "fr" "ko" "hi" "hr" "id" "it" "he" "lt" "hu" "ms" "nl" "ja" "no" "pl" "pt" "kk" "ro" "ru" "sk" "sl" "sr" "fi" "sv" "tr" "uk" "vi" "vo" "war" "zh" )

# get wikidata tables

wget https://dumps.wikimedia.org/wikidatawiki/latest/wikidatawiki-latest-geo_tags.sql.gz
wget https://dumps.wikimedia.org/wikidatawiki/latest/wikidatawiki-latest-page.sql.gz
wget https://dumps.wikimedia.org/wikidatawiki/latest/wikidatawiki-latest-wb_items_per_site.sql.gz

# import wikidata tables

gzip -dc wikidatawiki-latest-geo_tags.sql.gz | mysql2pgsqlcmd | psqlcmd
gzip -dc wikidatawiki-latest-page.sql.gz | mysql2pgsqlcmd | psqlcmd
gzip -dc wikidatawiki-latest-wb_items_per_site.sql.gz | mysql2pgsqlcmd | psqlcmd

# create derrived tables

echo "CREATE TABLE geo_earth_primary AS SELECT gt_page_id, gt_lat, gt_lon FROM geo_tags WHERE gt_globe = 'earth' AND gt_primary = 1 AND NOT( gt_lat < -90 OR gt_lat > 90 OR gt_lon < -180 OR gt_lon > 180 OR gt_lat=0 OR gt_lon=0) ;" | psqlcmd
echo "CREATE TABLE geo_earth_wikidata AS SELECT DISTINCT geo_earth_primary.gt_page_id, geo_earth_primary.gt_lat, geo_earth_primary.gt_lon, page.page_title, page.page_namespace FROM geo_earth_primary LEFT OUTER JOIN page ON (geo_earth_primary.gt_page_id = page.page_id) ORDER BY geo_earth_primary.gt_page_id;" | psqlcmd
echo "CREATE TABLE geo_earth_wikidata_pages (gt_page_id integer, gt_lat numeric(11,8), gt_lon numeric(11,8), language text, page_title text, page_namespace text, ips_site_page text);" | psqlcmd

# wikipedia pages and links

for i in "${language[@]}"
do
   echo "create table geo_earth_wikidata_${i}_pages as select geo_earth_wikidata.gt_page_id, geo_earth_wikidata.gt_lat, geo_earth_wikidata.gt_lon, geo_earth_wikidata.page_title, geo_earth_wikidata.page_namespace, wb_items_per_site.ips_site_page FROM geo_earth_wikidata LEFT JOIN wb_items_per_site ON (CAST (( LTRIM(geo_earth_wikidata.page_title, 'Q')) AS INTEGER) = wb_items_per_site.ips_item_id) WHERE ips_site_id = '${i}wiki' order by geo_earth_wikidata.gt_page_id;" | psqlcmd
   echo "insert into geo_earth_wikidata_pages select gt_page_id, gt_lat, gt_lon, '${i}', page_title, page_namespace ips_site_page from geo_earth_wikidata_${i}_pages;" | psqlcmd
done

