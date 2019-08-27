#!/bin/bash

psqlcmd() {
     psql wikiprocessingdb
}

mysql2pgsqlcmd() {
     ./mysql2pgsql.perl /dev/stdin /dev/stdout
}


# list the languages to process (refer to List of Wikipedias here: https://en.wikipedia.org/wiki/List_of_Wikipedias)

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
echo "CREATE TABLE geo_earth_wikidata_pages (gt_page_id integer, gt_lat numeric(11,8), gt_lon numeric(11,8), language text, page_title text, instance_of text, ips_site_page text);" | psqlcmd


# get wikidata places from wikidata query API

while read F  ; do
    wget "https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query=SELECT ?item?lat?lon WHERE{?item wdt:P31*/wdt:P279*wd:$F;wdt:P625?pt.?item p:P625?loc.?loc psv:P625?cnode.?cnode wikibase:geoLatitude?lat.?cnode wikibase:geoLongitude?lon.}" -O $F.json
    jq -r '.results | .[] | .[] | [.item.value,.lat.value, .lon.value] | @csv ' $F.json >> $F.txt
    awk -v qid=$F '{print $0 ","qid}' $F.txt | sed -e 's!"http://www.wikidata.org/entity/!!' | sed 's/"//g' >> $F.csv
    cat $F.csv >> wikidata_place_dump.csv
    rm $F.json $F.txt $F.csv
done < wikidata_place_types.txt


# import wikidata places

echo "CREATE TABLE wikidata_place_dump (item text,  lat numeric(11,8), lon numeric(11,8), instance_of text, ont_level integer);"  | psqlcmd
echo "COPY wikidata_place_dump (item, lat, lon, instance_of) FROM  '/srv/nominatim/Nominatim/data-sources/wikipedia-wikidata/wikidata_place_dump.csv' DELIMITER ',' CSV;"  | psqlcmd
echo "CREATE TABLE wikidata_places AS SELECT DISTINCT item, instance_of, lon, lat, ont_level FROM wikidata_place_types;" | psqlcmd
echo "CREATE TABLE wikidata_place_type_levels (place_type text, level integer);" | psqlcmd
echo "COPY wikidata_place_type_levels(place_type, level) FROM '/srv/nominatim/Nominatim/data-sources/wikipedia-wikidata/wikidata_place_type_levels.csv' DELIMITER ',' CSV HEADER;" | psqlcmd
echo "UPDATE wikidata_places SET ont_level = level FROM wikidata_place_type_levels WHERE instance_of = place_type;" | psqlcmd


# create wikidata language pages with wikipedia links

for i in "${language[@]}"
do
   echo "create table geo_earth_wikidata_${i}_pages as select geo_earth_wikidata_places.gt_page_id, geo_earth_wikidata_places.gt_lat, geo_earth_wikidata_places.gt_lon, geo_earth_wikidata_places.page_title, geo_earth_wikidata_places.instance_of, wb_items_per_site.ips_site_page FROM geo_earth_wikidata_places LEFT JOIN wb_items_per_site ON (CAST (( LTRIM(geo_earth_wikidata_places.page_title, 'Q')) AS INTEGER) = wb_items_per_site.ips_item_id) WHERE ips_site_id = '${i}wiki' order by geo_earth_wikidata_places.gt_page_id;" | psqlcmd
   echo "insert into geo_earth_wikidata_pages select gt_page_id, gt_lat, gt_lon, '${i}', page_title, instance_of, ips_site_page from geo_earth_wikidata_${i}_pages;" | psqlcmd
done

echo "ALTER TABLE geo_earth_wikidata_pages ADD COLUMN wp_page_title text;" | psqlcmd
echo "UPDATE geo_earth_wikidata_pages SET wp_page_title = REPLACE(ips_site_page, ' ', '_');" | psqlcmd


# add wikidata to wikipedia_article table

echo "UPDATE wikipedia_article SET lat = geo_earth_wikidata_pages.gt_lat, lon = geo_earth_wikidata_pages.gt_lon, wd_page_title = geo_earth_wikidata_pages.page_title, instance_of = geo_earth_wikidata_pages.instance_of FROM geo_earth_wikidata_pages WHERE wikipedia_article.language = geo_earth_wikidata_pages.language AND wikipedia_article.title  = geo_earth_wikidata_pages.wp_page_title AND geo_earth_wikidata_pages.gt_lat IS NOT NULL;" | psqlcmd






# clean up intermediate tables

echo "DROP TABLE wikidata_place_dump;" | psqlcmd
echo "DROP TABLE wikidata_place_type_levels;" | psqlcmd
echo "DROP TABLE geo_earth_primary;" | psqlcmd
for i in "${language[@]}"
do
    echo "DROP TABLE geo_earth_wikidata_${i}_pages;" | psqlcmd
done
