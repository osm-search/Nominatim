#!/bin/bash

psqlcmd() {
     psql wikipedia2019
}

mysql2pgsqlcmd() {
     ./mysql2pgsql.perl /dev/stdin /dev/stdout
}

language=( "ar" "bg" "ca" "cs" "da" "de" "en" "es" "eo" "eu" "fa" "fr" "ko" "hi" "hr" "id" "it" "he" "lt" "hu" "ms" "nl" "ja" "no" "pl" "pt" "kk" "ro" "ru" "sk" "sl" "sr" "fi" "sv" "tr" "uk" "vi" "vo" "war" "zh" )

# wikipedia pages and links
echo "CREATE TABLE linkcounts (language text, title text, count integer, sumcount integer, lat double precision, lon double precision);"  | psqlcmd
echo "CREATE TABLE wikipedia_redirect (language text, from_title text, to_title text );"  | psqlcmd

for i in "${language[@]}"
do
    wget https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-page.sql.gz
    wget https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-pagelinks.sql.gz
    wget https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-langlinks.sql.gz
    wget https://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-redirect.sql.gz
done

for i in "${language[@]}"
do
    gzip -dc ${i}wiki-latest-pagelinks.sql.gz | sed "s/\`pagelinks\`/\`${i}pagelinks\`/g" | mysql2pgsqlcmd | psqlcmd
    gzip -dc ${i}wiki-latest-page.sql.gz | sed "s/\`page\`/\`${i}page\`/g" | mysql2pgsqlcmd | psqlcmd
    gzip -dc ${i}wiki-latest-langlinks.sql.gz | sed "s/\`langlinks\`/\`${i}langlinks\`/g" | mysql2pgsqlcmd | psqlcmd
    gzip -dc ${i}wiki-latest-redirect.sql.gz | sed "s/\`redirect\`/\`${i}redirect\`/g" | mysql2pgsqlcmd | psqlcmd
done

for i in "${language[@]}"
do
    echo "create table ${i}pagelinkcount as select pl_title as title,count(*) as count from ${i}pagelinks where pl_namespace = 0 group by pl_title;" | psqlcmd
    echo "insert into linkcounts select '${i}',pl_title,count(*) from ${i}pagelinks where pl_namespace = 0 group by pl_title;" | psqlcmd
    echo "insert into wikipedia_redirect select '${i}',page_title,rd_title from ${i}redirect join ${i}page on (rd_from = page_id) where page_namespace = 0 and rd_namespace = 0;" | psqlcmd
    echo "alter table ${i}pagelinkcount add column othercount integer;" | psqlcmd
    echo "update ${i}pagelinkcount set othercount = 0;" | psqlcmd
    for j in "${language[@]}"
    do
        echo "update ${i}pagelinkcount set othercount = ${i}pagelinkcount.othercount + x.count from (select page_title as title,count from ${i}langlinks join ${i}page on (ll_from = page_id) join ${j}pagelinkcount on (ll_lang = '${j}' and ll_title = title)) as x where x.title = ${i}pagelinkcount.title;" | psqlcmd
    done
    echo "insert into wikipedia_article select '${i}', title, count, othercount, count+othercount from ${i}pagelinkcount;" | psqlcmd
done

echo "update wikipedia_article set importance = log(totalcount)/log((select max(totalcount) from wikipedia_article))" | psqlcmd
