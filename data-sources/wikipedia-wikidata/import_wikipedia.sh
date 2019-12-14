#!/bin/bash

psqlcmd() {
     psql wikiprocessingdb
}

mysql2pgsqlcmd() {
     ./mysql2pgsql.perl /dev/stdin /dev/stdout
}


# list the languages to process (refer to List of Wikipedias here: https://en.wikipedia.org/wiki/List_of_Wikipedias)

language=( "ar" "bg" "ca" "cs" "da" "de" "en" "es" "eo" "eu" "fa" "fr" "ko" "hi" "hr" "id" "it" "he" "lt" "hu" "ms" "nl" "ja" "no" "pl" "pt" "kk" "ro" "ru" "sk" "sl" "sr" "fi" "sv" "tr" "uk" "vi" "vo" "war" "zh" )


# create wikipedia calculation tables

echo "CREATE TABLE linkcounts (language text, title text, count integer, sumcount integer, lat double precision, lon double precision);"  | psqlcmd
echo "CREATE TABLE wikipedia_article (language text NOT NULL, title text NOT NULL, langcount integer, othercount integer, totalcount integer, lat double precision, lon double precision, importance double precision, title_en text, osm_type character(1), osm_id bigint );" | psqlcmd
echo "CREATE TABLE wikipedia_redirect (language text, from_title text, to_title text );"  | psqlcmd


# download individual wikipedia language tables

for i in "${language[@]}"
do
    wget https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-page.sql.gz
    wget https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-pagelinks.sql.gz
    wget https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-langlinks.sql.gz
    wget https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-redirect.sql.gz
done


# import individual wikipedia language tables

for i in "${language[@]}"
do
    gzip -dc ${i}wiki-latest-pagelinks.sql.gz | sed "s/\`pagelinks\`/\`${i}pagelinks\`/g" | mysql2pgsqlcmd | psqlcmd
    gzip -dc ${i}wiki-latest-page.sql.gz | sed "s/\`page\`/\`${i}page\`/g" | mysql2pgsqlcmd | psqlcmd
    gzip -dc ${i}wiki-latest-langlinks.sql.gz | sed "s/\`langlinks\`/\`${i}langlinks\`/g" | mysql2pgsqlcmd | psqlcmd
    gzip -dc ${i}wiki-latest-redirect.sql.gz | sed "s/\`redirect\`/\`${i}redirect\`/g" | mysql2pgsqlcmd | psqlcmd
done


# process language tables and associated pagelink counts

for i in "${language[@]}"
do
    echo "create table ${i}pagelinkcount as select pl_title as title,count(*) as count from ${i}pagelinks where pl_namespace = 0 group by pl_title;" | psqlcmd
    echo "insert into linkcounts select '${i}',pl_title,count(*) from ${i}pagelinks where pl_namespace = 0 group by pl_title;" | psqlcmd
    echo "insert into wikipedia_redirect select '${i}',page_title,rd_title from ${i}redirect join ${i}page on (rd_from = page_id) where page_namespace = 0 and rd_namespace = 0;" | psqlcmd
    echo "alter table ${i}pagelinkcount add column othercount integer;" | psqlcmd
    echo "update ${i}pagelinkcount set othercount = 0;" | psqlcmd
done

for i in "${language[@]}"
do
    for j in "${language[@]}"
    do
        echo "update ${i}pagelinkcount set othercount = ${i}pagelinkcount.othercount + x.count from (select page_title as title,count from ${i}langlinks join ${i}page on (ll_from = page_id) join ${j}pagelinkcount on (ll_lang = '${j}' and ll_title = title)) as x where x.title = ${i}pagelinkcount.title;" | psqlcmd
    done
    echo "insert into wikipedia_article select '${i}', title, count, othercount, count+othercount from ${i}pagelinkcount;" | psqlcmd
done


# calculate importance score for each wikipedia page

echo "update wikipedia_article set importance = log(totalcount)/log((select max(totalcount) from wikipedia_article))" | psqlcmd


# clean up intermediate tables to conserve space

for i in "${language[@]}"
do
    echo "DROP TABLE ${i}pagelinks;" | psqlcmd
    echo "DROP TABLE ${i}page;" | psqlcmd
    echo "DROP TABLE ${i}langlinks;" | psqlcmd
    echo "DROP TABLE ${i}redirect;" | psqlcmd
    echo "DROP TABLE ${i}pagelinkcount;" | psqlcmd
done
