#!/bin/bash

psqlcmd() {
     psql --quiet wikiprocessingdb
}

mysql2pgsqlcmd() {
     ./mysql2pgsql.perl /dev/stdin /dev/stdout
}

download() {
     echo "Downloading $1"
     wget --quiet --no-clobber --tries 3
}


# languages to process (refer to List of Wikipedias here: https://en.wikipedia.org/wiki/List_of_Wikipedias)
# requires Bash 4.0
readarray -t LANGUAGES < languages.txt



echo "====================================================================="
echo "Create wikipedia calculation tables"
echo "====================================================================="

echo "CREATE TABLE linkcounts (
        language text,
        title    text,
        count    integer,
        sumcount integer,
        lat      double precision,
        lon      double precision
     );"  | psqlcmd

echo "CREATE TABLE wikipedia_article (
        language    text NOT NULL,
        title       text NOT NULL,
        langcount   integer,
        othercount  integer,
        totalcount  integer,
        lat double  precision,
        lon double  precision,
        importance  double precision,
        title_en    text,
        osm_type    character(1),
        osm_id      bigint
      );" | psqlcmd

echo "CREATE TABLE wikipedia_redirect (
        language   text,
        from_title text,
        to_title   text
     );" | psqlcmd





echo "====================================================================="
echo "Download individual wikipedia language tables"
echo "====================================================================="


for i in "${LANGUAGES[@]}"
do
    echo "Language: $i"

    # english is the largest
    # 1.7G  enwiki-latest-page.sql.gz
    # 6.2G  enwiki-latest-pagelinks.sql.gz
    # 355M  enwiki-latest-langlinks.sql.gz
    # 128M  enwiki-latest-redirect.sql.gz

    # example of smaller languge turkish
    #  53M  trwiki-latest-page.sql.gz
    # 176M  trwiki-latest-pagelinks.sql.gz
    # 106M  trwiki-latest-langlinks.sql.gz
    # 3.2M  trwiki-latest-redirect.sql.gz

    download https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-page.sql.gz
    download https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-pagelinks.sql.gz
    download https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-langlinks.sql.gz
    download https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-redirect.sql.gz
done





echo "====================================================================="
echo "Import individual wikipedia language tables"
echo "====================================================================="

for i in "${LANGUAGES[@]}"
do
    echo "Language: $i"

    echo "Importing ${i}wiki-latest-pagelinks"
    gzip -dc ${i}wiki-latest-pagelinks.sql.gz | sed "s/\`pagelinks\`/\`${i}pagelinks\`/g" | mysql2pgsqlcmd | psqlcmd

    echo "Importing ${i}wiki-latest-page"
    gzip -dc ${i}wiki-latest-page.sql.gz      | sed "s/\`page\`/\`${i}page\`/g"           | mysql2pgsqlcmd | psqlcmd

    echo "Importing ${i}wiki-latest-langlinks"
    gzip -dc ${i}wiki-latest-langlinks.sql.gz | sed "s/\`langlinks\`/\`${i}langlinks\`/g" | mysql2pgsqlcmd | psqlcmd

    echo "Importing ${i}wiki-latest-redirect"
    gzip -dc ${i}wiki-latest-redirect.sql.gz  | sed "s/\`redirect\`/\`${i}redirect\`/g"   | mysql2pgsqlcmd | psqlcmd
done





echo "====================================================================="
echo "Process language tables and associated pagelink counts"
echo "====================================================================="


for i in "${LANGUAGES[@]}"
do
    echo "Language: $i"

    echo "CREATE TABLE ${i}pagelinkcount
          AS
          SELECT pl_title AS title,
                 COUNT(*) AS count
          FROM ${i}pagelinks
          WHERE pl_namespace = 0
          GROUP BY pl_title
          ;" | psqlcmd

    echo "INSERT INTO linkcounts
          SELECT '${i}',
                 pl_title,
                 COUNT(*)
          FROM ${i}pagelinks
          WHERE pl_namespace = 0
          GROUP BY pl_title
          ;" | psqlcmd

    echo "INSERT INTO wikipedia_redirect
          SELECT '${i}',
                 page_title,
                 rd_title
          FROM ${i}redirect
          JOIN ${i}page ON (rd_from = page_id)
          WHERE page_namespace = 0
            AND rd_namespace = 0
          ;" | psqlcmd

    echo "ALTER TABLE ${i}pagelinkcount
          ADD COLUMN othercount integer
          ;" | psqlcmd

    echo "UPDATE ${i}pagelinkcount
          SET othercount = 0
          ;" | psqlcmd

    for j in "${LANGUAGES[@]}"
    do
        echo "UPDATE ${i}pagelinkcount
              SET othercount = ${i}pagelinkcount.othercount + x.count
              FROM (
                SELECT page_title AS title,
                       count
                FROM ${i}langlinks
                JOIN ${i}page ON (ll_from = page_id)
                JOIN ${j}pagelinkcount ON (ll_lang = '${j}' AND ll_title = title)
              ) AS x
              WHERE x.title = ${i}pagelinkcount.title
              ;" | psqlcmd
    done

    echo "INSERT INTO wikipedia_article
          SELECT '${i}',
                 title,
                 count,
                 othercount,
                 count + othercount
          FROM ${i}pagelinkcount
          ;" | psqlcmd
done





echo "====================================================================="
echo "Calculate importance score for each wikipedia page"
echo "====================================================================="

echo "UPDATE wikipedia_article
      SET importance = LOG(totalcount)/LOG((SELECT MAX(totalcount) FROM wikipedia_article))
      ;" | psqlcmd





echo "====================================================================="
echo "Clean up intermediate tables to conserve space"
echo "====================================================================="

for i in "${LANGUAGES[@]}"
do
    echo "DROP TABLE ${i}pagelinks;"     | psqlcmd
    echo "DROP TABLE ${i}page;"          | psqlcmd
    echo "DROP TABLE ${i}langlinks;"     | psqlcmd
    echo "DROP TABLE ${i}redirect;"      | psqlcmd
    echo "DROP TABLE ${i}pagelinkcount;" | psqlcmd
done
