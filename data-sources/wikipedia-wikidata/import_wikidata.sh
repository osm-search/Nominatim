#!/bin/bash

psqlcmd() {
     psql --quiet wikiprocessingdb
}

mysql2pgsqlcmd() {
     ./mysql2pgsql.perl /dev/stdin /dev/stdout
}

download() {
     echo "Downloading $1"
     wget --quiet --no-clobber --tries 3 "$1"
}

# languages to process (refer to List of Wikipedias here: https://en.wikipedia.org/wiki/List_of_Wikipedias)
# requires Bash 4.0
readarray -t LANGUAGES < languages.txt



echo "====================================================================="
echo "Download wikidata dump tables"
echo "====================================================================="

# 114M  wikidatawiki-latest-geo_tags.sql.gz
# 1.7G  wikidatawiki-latest-page.sql.gz
# 1.2G  wikidatawiki-latest-wb_items_per_site.sql.gz
download https://dumps.wikimedia.org/wikidatawiki/latest/wikidatawiki-latest-geo_tags.sql.gz
download https://dumps.wikimedia.org/wikidatawiki/latest/wikidatawiki-latest-page.sql.gz
download https://dumps.wikimedia.org/wikidatawiki/latest/wikidatawiki-latest-wb_items_per_site.sql.gz




echo "====================================================================="
echo "Import wikidata dump tables"
echo "====================================================================="

echo "Importing wikidatawiki-latest-geo_tags"
gzip -dc wikidatawiki-latest-geo_tags.sql.gz          | mysql2pgsqlcmd | psqlcmd

echo "Importing wikidatawiki-latest-page"
gzip -dc wikidatawiki-latest-page.sql.gz              | mysql2pgsqlcmd | psqlcmd

echo "Importing wikidatawiki-latest-wb_items_per_site"
gzip -dc wikidatawiki-latest-wb_items_per_site.sql.gz | mysql2pgsqlcmd | psqlcmd






echo "====================================================================="
echo "Get wikidata places from wikidata query API"
echo "====================================================================="

echo "Number of place types:"
wc -l wikidata_place_types.txt

while read F  ; do
    echo "Querying for place type $F..."
    wget --quiet "https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query=SELECT ?item WHERE{?item wdt:P31*/wdt:P279*wd:$F;}" -O $F.json
    jq -r '.results | .[] | .[] | [.item.value] | @csv' $F.json >> $F.txt
    awk -v qid=$F '{print $0 ","qid}' $F.txt | sed -e 's!"http://www.wikidata.org/entity/!!' | sed 's/"//g' >> $F.csv
    cat $F.csv >> wikidata_place_dump.csv
    rm $F.json $F.txt $F.csv
done < wikidata_place_types.txt




echo "====================================================================="
echo "Import wikidata places"
echo "====================================================================="

echo "CREATE TABLE wikidata_place_dump (
        item        text,
        instance_of text
      );"  | psqlcmd

echo "COPY wikidata_place_dump (item, instance_of)
      FROM '/srv/nominatim/Nominatim/data-sources/wikipedia-wikidata/wikidata_place_dump.csv'
      DELIMITER ','
      CSV
      ;"  | psqlcmd

echo "CREATE TABLE wikidata_place_type_levels (
        place_type text,
        level      integer
      );" | psqlcmd

echo "COPY wikidata_place_type_levels (place_type, level)
      FROM '/srv/nominatim/Nominatim/data-sources/wikipedia-wikidata/wikidata_place_type_levels.csv'
      DELIMITER ','
      CSV
      HEADER
      ;" | psqlcmd




echo "====================================================================="
echo "Create derived tables"
echo "====================================================================="

echo "CREATE TABLE geo_earth_primary AS
      SELECT gt_page_id,
             gt_lat,
             gt_lon
      FROM geo_tags
      WHERE gt_globe = 'earth'
        AND gt_primary = 1
        AND NOT(    gt_lat < -90
                 OR gt_lat > 90
                 OR gt_lon < -180
                 OR gt_lon > 180
                 OR gt_lat=0
                 OR gt_lon=0)
      ;" | psqlcmd

echo "CREATE TABLE geo_earth_wikidata AS
      SELECT DISTINCT geo_earth_primary.gt_page_id,
                      geo_earth_primary.gt_lat,
                      geo_earth_primary.gt_lon,
                      page.page_title,
                      page.page_namespace
      FROM geo_earth_primary
      LEFT OUTER JOIN page
                   ON (geo_earth_primary.gt_page_id = page.page_id)
      ORDER BY geo_earth_primary.gt_page_id
      ;" | psqlcmd

echo "ALTER TABLE wikidata_place_dump
      ADD COLUMN ont_level integer,
      ADD COLUMN lat numeric(11,8),
      ADD COLUMN lon numeric(11,8)
      ;" | psqlcmd

echo "UPDATE wikidata_place_dump
      SET ont_level = wikidata_place_type_levels.level
      FROM wikidata_place_type_levels
      WHERE wikidata_place_dump.instance_of = wikidata_place_type_levels.place_type
      ;" | psqlcmd

echo "CREATE TABLE wikidata_places
      AS
      SELECT DISTINCT ON (item) item,
                                instance_of,
                                MAX(ont_level) AS ont_level,
                                lat,
                                lon
      FROM wikidata_place_dump
      GROUP BY item,
               instance_of,
               ont_level,
               lat,
               lon
      ORDER BY item
      ;" | psqlcmd

echo "UPDATE wikidata_places
      SET lat = geo_earth_wikidata.gt_lat,
          lon = geo_earth_wikidata.gt_lon
      FROM geo_earth_wikidata
      WHERE wikidata_places.item = geo_earth_wikidata.page_title
      ;" | psqlcmd




echo "====================================================================="
echo "Process language pages"
echo "====================================================================="


echo "CREATE TABLE wikidata_pages (
        item          text,
        instance_of   text,
        lat           numeric(11,8),
        lon           numeric(11,8),
        ips_site_page text,
        language      text
      );" | psqlcmd

for i in "${LANGUAGES[@]}"
do
   echo "CREATE TABLE wikidata_${i}_pages AS
         SELECT wikidata_places.item,
                wikidata_places.instance_of,
                wikidata_places.lat,
                wikidata_places.lon,
                wb_items_per_site.ips_site_page
         FROM wikidata_places
         LEFT JOIN wb_items_per_site
                ON (CAST (( LTRIM(wikidata_places.item, 'Q')) AS INTEGER) = wb_items_per_site.ips_item_id)
         WHERE ips_site_id = '${i}wiki'
           AND LEFT(wikidata_places.item,1) = 'Q'
         ORDER BY wikidata_places.item
         ;" | psqlcmd

   echo "ALTER TABLE wikidata_${i}_pages
         ADD COLUMN language text
         ;" | psqlcmd

   echo "UPDATE wikidata_${i}_pages
         SET language = '${i}'
         ;" | psqlcmd

   echo "INSERT INTO wikidata_pages
         SELECT item,
                instance_of,
                lat,
                lon,
                ips_site_page,
                language
         FROM wikidata_${i}_pages
         ;" | psqlcmd
done

echo "ALTER TABLE wikidata_pages
      ADD COLUMN wp_page_title text
      ;" | psqlcmd
echo "UPDATE wikidata_pages
      SET wp_page_title = REPLACE(ips_site_page, ' ', '_')
      ;" | psqlcmd
echo "ALTER TABLE wikidata_pages
      DROP COLUMN ips_site_page
      ;" | psqlcmd




echo "====================================================================="
echo "Add wikidata to wikipedia_article table"
echo "====================================================================="

echo "UPDATE wikipedia_article
      SET lat = wikidata_pages.lat,
          lon = wikidata_pages.lon,
          wd_page_title = wikidata_pages.item,
          instance_of = wikidata_pages.instance_of
      FROM wikidata_pages
      WHERE wikipedia_article.language = wikidata_pages.language
        AND wikipedia_article.title  = wikidata_pages.wp_page_title
      ;" | psqlcmd

echo "CREATE TABLE wikipedia_article_slim
      AS
      SELECT * FROM wikipedia_article
      WHERE wikidata_id IS NOT NULL
      ;" | psqlcmd

echo "ALTER TABLE wikipedia_article
      RENAME TO wikipedia_article_full
      ;" | psqlcmd

echo "ALTER TABLE wikipedia_article_slim
      RENAME TO wikipedia_article
      ;" | psqlcmd




echo "====================================================================="
echo "Dropping intermediate tables"
echo "====================================================================="

echo "DROP TABLE wikidata_place_dump;" | psqlcmd
echo "DROP TABLE geo_earth_primary;" | psqlcmd
for i in "${LANGUAGES[@]}"
do
    echo "DROP TABLE wikidata_${i}_pages;" | psqlcmd
done
