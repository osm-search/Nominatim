CREATE TABLE word_frequencies AS
  (SELECT unnest(make_keywords(v)) as id, sum(count) as count
     FROM (select svals(name) as v, count(*)from place group by v) cnt
    WHERE v is not null
 GROUP BY id);

select count(make_keywords(v)) from (select distinct address->'postcode' as v from place where address ? 'postcode') as w where v is not null;
select count(getorcreate_housenumber_id(make_standard_name(v))) from (select distinct address->'housenumber' as v from place where address ? 'housenumber') as w;

-- copy the word frequencies
update word set search_name_count = count from word_frequencies wf where wf.id = word.word_id;

-- and drop the temporary frequency table again
drop table word_frequencies;
