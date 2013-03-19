#!/bin/bash

psqlcmd=psql wikipedia2013
mysql2pgsqlcmd=./mysql2pgsql.perl /dev/stdin /dev/stdout

language=( "ar" "bg" "ca" "cs" "da" "de" "en" "es" "eo" "eu" "fa" "fr" "ko" "hi" "hr" "id" "it" "he" "lt" "hu" "ms" "nl" "ja" "no" "pl" "pt" "kk" "ro" "ru" "sk" "sl" "sr" "fi" "sv" "tr" "uk" "vi" "vo" "war" "zh" )

# wikipedia pages and links
echo "CREATE TABLE linkcounts (language text, title text, count integer, sumcount integer, lat double, lon double );"  | $psqlcmd
echo "CREATE TABLE wikipedia_redirect (language text, from_title text, to_title text );"  | $psqlcmd

for i in "${language[@]}"
do
	wget http://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-page.sql.gz
	wget http://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-pagelinks.sql.gz
	wget http://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-langlinks.sql.gz
	wget http://dumps.wikimedia.org/${i}wiki/latest/${i}wiki-latest-redirect.sql.gz
done

for i in "${language[@]}"
do
  gzip -dc ${i}wiki-latest-pagelinks.sql.gz | sed "s/\`pagelinks\`/\`${i}pagelinks\`/g" | $mysql2pgsqlcmd | $psqlcmd
  gzip -dc ${i}wiki-latest-page.sql.gz | sed "s/\`page\`/\`${i}page\`/g" | $mysql2pgsqlcmd | $psqlcmd
  gzip -dc ${i}wiki-latest-langlinks.sql.gz | sed "s/\`langlinks\`/\`${i}langlinks\`/g" | $mysql2pgsqlcmd | $psqlcmd
  gzip -dc ${i}wiki-latest-redirect.sql.gz | sed "s/\`redirect\`/\`${i}redirect\`/g" | $mysql2pgsqlcmd | $psqlcmd
done

for i in "${language[@]}"
do
  echo "create table ${i}pagelinkcount as select pl_title as title,count(*) as count from ${i}pagelinks where pl_namespace = 0 group by pl_title;" | $psqlcmd
  echo "insert into linkcounts select '${i}',pl_title,count(*) from ${i}pagelinks where pl_namespace = 0 group by pl_title;" | $psqlcmd
  echo "insert into wikipedia_redirect select '${i}',page_title,rd_title from ${i}redirect join ${i}page on (rd_from = page_id) where page_namespace = 0 and rd_namespace = 0;" | $psqlcmd
  echo "alter table ${i}pagelinkcount add column othercount integer;" | $psqlcmd
  echo "update ${i}pagelinkcount set othercount = 0;" | $psqlcmd
  for j in "${language[@]}"
  do
    echo "update ${i}pagelinkcount set othercount = ${i}pagelinkcount.othercount + x.count from (select page_title as title,count from ${i}langlinks join ${i}page on (ll_from = page_id) join ${j}pagelinkcount on (ll_lang = '${j}' and ll_title = title)) as x where x.title = ${i}pagelinkcount.title;" | $psqlcmd
  done
  echo "insert into wikipedia_article select '${i}', title, count, othercount, count+othercount from ${i}pagelinkcount;" | $psqlcmd
done

echo "update wikipedia_article set importance = log(totalcount)/log((select max(totalcount) from wikipedia_article))" | $psqlcmd

# precalculated lat,lon from dbpedia
wget http://downloads.dbpedia.org/current/en/geo_coordinates_en.nq.bz2
bzip2 -dc geo_coordinates_en.nq.bz2 | grep http://www.georss.org/georss/point | sed 's|<http://dbpedia.org/resource/[^>]*> *<http://www.georss.org/georss/point> "\(-\?[-0-9.E]\+\) \(-\?[-0-9.E]\+\)"@en <http://\([a-z][a-z]\).wikipedia.org/wiki/\([^#]\+\)#> .|update pagelinks set lat=\1, lon=\2 where language = '"'"'\3'"'"' and title = decode_url_part('"'"'\4'"'"');|g' | $psqlcmd

# media wiki dumper
wget https://github.com/bcollier/mwdumper/blob/master/build/mwdumper.jar

# latest english wikipedia articles
wget http://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2
java -jar mwdumper.jar --format=sql:1.5 enwiki-latest-pages-articles.xml.bz2 | ./mysql2pgsql.perl /dev/stdin /dev/stdout | sed 's/"text (/text ("/g' | sed 's/"old_flags)"/"old_flags")/g' | sed 's/"revision (/revision ("/g' | sed 's/"rev_deleted)"/"rev_deleted")/g' | sed 's/"page (/page ("/g' | sed 's/"page_len)"/"page_len")/g' | sed "s/DATE_ADD(E'1970-01-01', INTERVAL UNIX_TIMESTAMP() SECOND)[+]//g" | sed 's/RAND()/0/g' | $psqlcmd
