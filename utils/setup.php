#!/usr/bin/php -Cq
<?php

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-cmd.php');
ini_set('memory_limit', '800M');

$aCMDOptions
= array(
   'Create and setup nominatim search system',
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

   array('osm-file', '', 0, 1, 1, 1, 'realpath', 'File to import'),
   array('threads', '', 0, 1, 1, 1, 'int', 'Number of threads (where possible)'),

   array('all', '', 0, 1, 0, 0, 'bool', 'Do the complete process'),

   array('create-db', '', 0, 1, 0, 0, 'bool', 'Create nominatim db'),
   array('setup-db', '', 0, 1, 0, 0, 'bool', 'Build a blank nominatim db'),
   array('import-data', '', 0, 1, 0, 0, 'bool', 'Import a osm file'),
   array('osm2pgsql-cache', '', 0, 1, 1, 1, 'int', 'Cache size used by osm2pgsql'),
   array('create-functions', '', 0, 1, 0, 0, 'bool', 'Create functions'),
   array('enable-diff-updates', '', 0, 1, 0, 0, 'bool', 'Turn on the code required to make diff updates work'),
   array('enable-debug-statements', '', 0, 1, 0, 0, 'bool', 'Include debug warning statements in pgsql commands'),
   array('ignore-errors', '', 0, 1, 0, 0, 'bool', 'Continue import even when errors in SQL are present (EXPERT)'),
   array('create-tables', '', 0, 1, 0, 0, 'bool', 'Create main tables'),
   array('create-partition-tables', '', 0, 1, 0, 0, 'bool', 'Create required partition tables'),
   array('create-partition-functions', '', 0, 1, 0, 0, 'bool', 'Create required partition triggers'),
   array('no-partitions', '', 0, 1, 0, 0, 'bool', 'Do not partition search indices (speeds up import of single country extracts)'),
   array('import-wikipedia-articles', '', 0, 1, 0, 0, 'bool', 'Import wikipedia article dump'),
   array('load-data', '', 0, 1, 0, 0, 'bool', 'Copy data to live tables from import table'),
   array('disable-token-precalc', '', 0, 1, 0, 0, 'bool', 'Disable name precalculation (EXPERT)'),
   array('import-tiger-data', '', 0, 1, 0, 0, 'bool', 'Import tiger data (not included in \'all\')'),
   array('calculate-postcodes', '', 0, 1, 0, 0, 'bool', 'Calculate postcode centroids'),
   array('osmosis-init', '', 0, 1, 0, 0, 'bool', 'Generate default osmosis configuration'),
   array('index', '', 0, 1, 0, 0, 'bool', 'Index the data'),
   array('index-noanalyse', '', 0, 1, 0, 0, 'bool', 'Do not perform analyse operations during index (EXPERT)'),
   array('create-search-indices', '', 0, 1, 0, 0, 'bool', 'Create additional indices required for search and update'),
   array('create-country-names', '', 0, 1, 0, 0, 'bool', 'Create default list of searchable country names'),
   array('drop', '', 0, 1, 0, 0, 'bool', 'Drop tables needed for updates, making the database readonly (EXPERIMENTAL)'),
  );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

$bDidSomething = false;

// Check if osm-file is set and points to a valid file if --all or --import-data is given
if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    if (!isset($aCMDResult['osm-file'])) {
        fail('missing --osm-file for data import');
    }

    if (!file_exists($aCMDResult['osm-file'])) {
        fail('the path supplied to --osm-file does not exist');
    }

    if (!is_readable($aCMDResult['osm-file'])) {
        fail('osm-file "'.$aCMDResult['osm-file'].'" not readable');
    }
}


// by default, use all but one processor, but never more than 15.
$iInstances = isset($aCMDResult['threads'])?$aCMDResult['threads']:(min(16,getProcessorCount())-1);
if ($iInstances < 1) {
    $iInstances = 1;
    warn("resetting threads to $iInstances");
}
if ($iInstances > getProcessorCount()) {
    $iInstances = getProcessorCount();
    warn("resetting threads to $iInstances");
}

// Assume we can steal all the cache memory in the box (unless told otherwise)
if (isset($aCMDResult['osm2pgsql-cache'])) {
    $iCacheMemory = $aCMDResult['osm2pgsql-cache'];
} else {
    $iCacheMemory = getCacheMemoryMB();
}

$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;

if ($aCMDResult['create-db'] || $aCMDResult['all']) {
    info('Create DB');
    $bDidSomething = true;
    $oDB = DB::connect(CONST_Database_DSN, false);
    if (!PEAR::isError($oDB)) {
        fail('database already exists ('.CONST_Database_DSN.')');
    }
    passthruCheckReturn('createdb -E UTF-8 -p '.$aDSNInfo['port'].' '.$aDSNInfo['database']);
}

if ($aCMDResult['setup-db'] || $aCMDResult['all']) {
    info('Setup DB');
    $bDidSomething = true;

    $oDB =& getDB();

    $fPostgresVersion = getPostgresVersion($oDB);
    echo 'Postgres version found: '.$fPostgresVersion."\n";

    if ($fPostgresVersion < 9.1) {
        fail('Minimum supported version of Postgresql is 9.1.');
    }

    pgsqlRunScript('CREATE EXTENSION IF NOT EXISTS hstore');
    pgsqlRunScript('CREATE EXTENSION IF NOT EXISTS postgis');

    // For extratags and namedetails the hstore_to_json converter is
    // needed which is only available from Postgresql 9.3+. For older
    // versions add a dummy function that returns nothing.
    $iNumFunc = chksql($oDB->getOne("select count(*) from pg_proc where proname = 'hstore_to_json'"));

    if ($iNumFunc == 0) {
        pgsqlRunScript("create function hstore_to_json(dummy hstore) returns text AS 'select null::text' language sql immutable");
        warn('Postgresql is too old. extratags and namedetails API not available.');
    }

    $fPostgisVersion = getPostgisVersion($oDB);
    echo 'Postgis version found: '.$fPostgisVersion."\n";

    if ($fPostgisVersion < 2.1) {
        // Functions were renamed in 2.1 and throw an annoying deprecation warning
        pgsqlRunScript('ALTER FUNCTION st_line_interpolate_point(geometry, double precision) RENAME TO ST_LineInterpolatePoint');
        pgsqlRunScript('ALTER FUNCTION ST_Line_Locate_Point(geometry, geometry) RENAME TO ST_LineLocatePoint');
    }
    if ($fPostgisVersion < 2.2) {
        pgsqlRunScript('ALTER FUNCTION ST_Distance_Spheroid(geometry, geometry, spheroid) RENAME TO ST_DistanceSpheroid');
    }

    $i = chksql($oDB->getOne("select count(*) from pg_user where usename = '".CONST_Database_Web_User."'"));
    if ($i == 0) {
        echo "\nERROR: Web user '".CONST_Database_Web_User."' does not exist. Create it with:\n";
        echo "\n          createuser ".CONST_Database_Web_User."\n\n";
        exit(1);
    }

    // Try accessing the C module, so we know early if something is wrong
    // and can simply error out.
    $sSQL = "CREATE FUNCTION nominatim_test_import_func(text) RETURNS text AS '";
    $sSQL .= CONST_InstallPath."/module/nominatim.so', 'transliteration' LANGUAGE c IMMUTABLE STRICT";
    $sSQL .= ';DROP FUNCTION nominatim_test_import_func(text);';
    $oResult = $oDB->query($sSQL);

    if (PEAR::isError($oResult)) {
        echo "\nERROR: Failed to load nominatim module. Reason:\n";
        echo $oResult->userinfo."\n\n";
        exit(1);
    }

    if (!file_exists(CONST_ExtraDataPath.'/country_osm_grid.sql.gz')) {
        echo 'Error: you need to download the country_osm_grid first:';
        echo "\n    wget -O ".CONST_ExtraDataPath."/country_osm_grid.sql.gz https://www.nominatim.org/data/country_grid.sql.gz\n";
        exit(1);
    }

    pgsqlRunScriptFile(CONST_BasePath.'/data/country_name.sql');
    pgsqlRunScriptFile(CONST_BasePath.'/data/country_naturalearthdata.sql');
    pgsqlRunScriptFile(CONST_BasePath.'/data/country_osm_grid.sql.gz');
    pgsqlRunScriptFile(CONST_BasePath.'/data/gb_postcode_table.sql');
    if (file_exists(CONST_BasePath.'/data/gb_postcode_data.sql.gz')) {
        pgsqlRunScriptFile(CONST_BasePath.'/data/gb_postcode_data.sql.gz');
    } else {
        warn('external UK postcode table not found.');
    }
    if (CONST_Use_Extra_US_Postcodes) {
        pgsqlRunScriptFile(CONST_BasePath.'/data/us_postcode.sql');
    }

    if ($aCMDResult['no-partitions']) {
        pgsqlRunScript('update country_name set partition = 0');
    }

    // the following will be needed by create_functions later but
    // is only defined in the subsequently called create_tables.
    // Create dummies here that will be overwritten by the proper
    // versions in create-tables.
    pgsqlRunScript('CREATE TABLE place_boundingbox ()');
    pgsqlRunScript('create type wikipedia_article_match as ()');
}

if ($aCMDResult['import-data'] || $aCMDResult['all']) {
    info('Import data');
    $bDidSomething = true;

    $osm2pgsql = CONST_Osm2pgsql_Binary;
    if (!file_exists($osm2pgsql)) {
        echo "Check CONST_Osm2pgsql_Binary in your local settings file.\n";
        echo "Normally you should not need to set this manually.\n";
        fail("osm2pgsql not found in '$osm2pgsql'");
    }

    if (!is_null(CONST_Osm2pgsql_Flatnode_File) && CONST_Osm2pgsql_Flatnode_File) {
        $osm2pgsql .= ' --flat-nodes '.CONST_Osm2pgsql_Flatnode_File;
    }
    if (CONST_Tablespace_Osm2pgsql_Data)
        $osm2pgsql .= ' --tablespace-slim-data '.CONST_Tablespace_Osm2pgsql_Data;
    if (CONST_Tablespace_Osm2pgsql_Index)
        $osm2pgsql .= ' --tablespace-slim-index '.CONST_Tablespace_Osm2pgsql_Index;
    if (CONST_Tablespace_Place_Data)
        $osm2pgsql .= ' --tablespace-main-data '.CONST_Tablespace_Place_Data;
    if (CONST_Tablespace_Place_Index)
        $osm2pgsql .= ' --tablespace-main-index '.CONST_Tablespace_Place_Index;
    $osm2pgsql .= ' -lsc -O gazetteer --hstore --number-processes 1';
    $osm2pgsql .= ' -C '.$iCacheMemory;
    $osm2pgsql .= ' -P '.$aDSNInfo['port'];
    $osm2pgsql .= ' -d '.$aDSNInfo['database'].' '.$aCMDResult['osm-file'];
    passthruCheckReturn($osm2pgsql);

    $oDB =& getDB();
    if (!$aCMDResult['ignore-errors'] && !chksql($oDB->getRow('select * from place limit 1'))) {
        fail('No Data');
    }
}

if ($aCMDResult['create-functions'] || $aCMDResult['all']) {
    info('Create Functions');
    $bDidSomething = true;
    if (!file_exists(CONST_InstallPath.'/module/nominatim.so')) {
        fail('nominatim module not built');
    }
    create_sql_functions($aCMDResult);
}

if ($aCMDResult['create-tables'] || $aCMDResult['all']) {
    info('Create Tables');
    $bDidSomething = true;

    $sTemplate = file_get_contents(CONST_BasePath.'/sql/tables.sql');
    $sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
    $sTemplate = replace_tablespace(
        '{ts:address-data}',
        CONST_Tablespace_Address_Data,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:address-index}',
        CONST_Tablespace_Address_Index,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:search-data}',
        CONST_Tablespace_Search_Data,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:search-index}',
        CONST_Tablespace_Search_Index,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:aux-data}',
        CONST_Tablespace_Aux_Data,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:aux-index}',
        CONST_Tablespace_Aux_Index,
        $sTemplate
    );
    pgsqlRunScript($sTemplate, false);

    // re-run the functions
    info('Recreate Functions');
    create_sql_functions($aCMDResult);
}

if ($aCMDResult['create-partition-tables'] || $aCMDResult['all']) {
    info('Create Partition Tables');
    $bDidSomething = true;

    $sTemplate = file_get_contents(CONST_BasePath.'/sql/partition-tables.src.sql');
    $sTemplate = replace_tablespace(
        '{ts:address-data}',
        CONST_Tablespace_Address_Data,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:address-index}',
        CONST_Tablespace_Address_Index,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:search-data}',
        CONST_Tablespace_Search_Data,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:search-index}',
        CONST_Tablespace_Search_Index,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:aux-data}',
        CONST_Tablespace_Aux_Data,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:aux-index}',
        CONST_Tablespace_Aux_Index,
        $sTemplate
    );

    pgsqlRunPartitionScript($sTemplate);
}


if ($aCMDResult['create-partition-functions'] || $aCMDResult['all']) {
    info('Create Partition Functions');
    $bDidSomething = true;

    $sTemplate = file_get_contents(CONST_BasePath.'/sql/partition-functions.src.sql');

    pgsqlRunPartitionScript($sTemplate);
}

if ($aCMDResult['import-wikipedia-articles'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $sWikiArticlesFile = CONST_Wikipedia_Data_Path.'/wikipedia_article.sql.bin';
    $sWikiRedirectsFile = CONST_Wikipedia_Data_Path.'/wikipedia_redirect.sql.bin';
    if (file_exists($sWikiArticlesFile)) {
        info('Importing wikipedia articles');
        pgsqlRunDropAndRestore($sWikiArticlesFile);
    } else {
        warn('wikipedia article dump file not found - places will have default importance');
    }
    if (file_exists($sWikiRedirectsFile)) {
        info('Importing wikipedia redirects');
        pgsqlRunDropAndRestore($sWikiRedirectsFile);
    } else {
        warn('wikipedia redirect dump file not found - some place importance values may be missing');
    }
}


if ($aCMDResult['load-data'] || $aCMDResult['all']) {
    info('Drop old Data');
    $bDidSomething = true;

    $oDB =& getDB();
    if (!pg_query($oDB->connection, 'TRUNCATE word')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'TRUNCATE placex')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'TRUNCATE location_property_osmline')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'TRUNCATE place_addressline')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'TRUNCATE place_boundingbox')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'TRUNCATE location_area')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'TRUNCATE search_name')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'TRUNCATE search_name_blank')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'DROP SEQUENCE seq_place')) fail(pg_last_error($oDB->connection));
    echo '.';
    if (!pg_query($oDB->connection, 'CREATE SEQUENCE seq_place start 100000')) fail(pg_last_error($oDB->connection));
    echo '.';

    $sSQL = 'select distinct partition from country_name';
    $aPartitions = chksql($oDB->getCol($sSQL));
    if (!$aCMDResult['no-partitions']) $aPartitions[] = 0;
    foreach ($aPartitions as $sPartition) {
        if (!pg_query($oDB->connection, 'TRUNCATE location_road_'.$sPartition)) fail(pg_last_error($oDB->connection));
        echo '.';
    }

    // used by getorcreate_word_id to ignore frequent partial words
    $sSQL = 'CREATE OR REPLACE FUNCTION get_maxwordfreq() RETURNS integer AS ';
    $sSQL .= '$$ SELECT '.CONST_Max_Word_Frequency.' as maxwordfreq; $$ LANGUAGE SQL IMMUTABLE';
    if (!pg_query($oDB->connection, $sSQL)) {
        fail(pg_last_error($oDB->connection));
    }
    echo ".\n";

    // pre-create the word list
    if (!$aCMDResult['disable-token-precalc']) {
        info('Loading word list');
        pgsqlRunScriptFile(CONST_BasePath.'/data/words.sql');
    }

    info('Load Data');
    $sColumns = 'osm_type, osm_id, class, type, name, admin_level, address, extratags, geometry';

    $aDBInstances = array();
    $iLoadThreads = max(1, $iInstances - 1);
    for ($i = 0; $i < $iLoadThreads; $i++) {
        $aDBInstances[$i] =& getDB(true);
        $sSQL = "INSERT INTO placex ($sColumns) SELECT $sColumns FROM place WHERE osm_id % $iLoadThreads = $i";
        $sSQL .= " and not (class='place' and type='houses' and osm_type='W'";
        $sSQL .= "          and ST_GeometryType(geometry) = 'ST_LineString')";
        $sSQL .= ' and ST_IsValid(geometry)';
        if ($aCMDResult['verbose']) echo "$sSQL\n";
        if (!pg_send_query($aDBInstances[$i]->connection, $sSQL)) {
            fail(pg_last_error($aDBInstances[$i]->connection));
        }
    }
    // last thread for interpolation lines
    $aDBInstances[$iLoadThreads] =& getDB(true);
    $sSQL = 'insert into location_property_osmline';
    $sSQL .= ' (osm_id, address, linegeo)';
    $sSQL .= ' SELECT osm_id, address, geometry from place where ';
    $sSQL .= "class='place' and type='houses' and osm_type='W' and ST_GeometryType(geometry) = 'ST_LineString'";
    if ($aCMDResult['verbose']) echo "$sSQL\n";
    if (!pg_send_query($aDBInstances[$iLoadThreads]->connection, $sSQL)) {
        fail(pg_last_error($aDBInstances[$iLoadThreads]->connection));
    }

    $bAnyBusy = true;
    while ($bAnyBusy) {
        $bAnyBusy = false;
        for ($i = 0; $i <= $iLoadThreads; $i++) {
            if (pg_connection_busy($aDBInstances[$i]->connection)) $bAnyBusy = true;
        }
        sleep(1);
        echo '.';
    }
    echo "\n";
    info('Reanalysing database');
    pgsqlRunScript('ANALYSE');

    $sDatabaseDate = getDatabaseDate($oDB);
    pg_query($oDB->connection, 'TRUNCATE import_status');
    if ($sDatabaseDate === false) {
        warn('could not determine database date.');
    } else {
        $sSQL = "INSERT INTO import_status (lastimportdate) VALUES('".$sDatabaseDate."')";
        pg_query($oDB->connection, $sSQL);
        echo "Latest data imported from $sDatabaseDate.\n";
    }
}

if ($aCMDResult['import-tiger-data']) {
    info('Import Tiger data');
    $bDidSomething = true;

    $sTemplate = file_get_contents(CONST_BasePath.'/sql/tiger_import_start.sql');
    $sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
    $sTemplate = replace_tablespace(
        '{ts:aux-data}',
        CONST_Tablespace_Aux_Data,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:aux-index}',
        CONST_Tablespace_Aux_Index,
        $sTemplate
    );
    pgsqlRunScript($sTemplate, false);

    $aDBInstances = array();
    for ($i = 0; $i < $iInstances; $i++) {
        $aDBInstances[$i] =& getDB(true);
    }

    foreach (glob(CONST_Tiger_Data_Path.'/*.sql') as $sFile) {
        echo $sFile.': ';
        $hFile = fopen($sFile, 'r');
        $sSQL = fgets($hFile, 100000);
        $iLines = 0;

        while (true) {
            for ($i = 0; $i < $iInstances; $i++) {
                if (!pg_connection_busy($aDBInstances[$i]->connection)) {
                    while (pg_get_result($aDBInstances[$i]->connection));
                    $sSQL = fgets($hFile, 100000);
                    if (!$sSQL) break 2;
                    if (!pg_send_query($aDBInstances[$i]->connection, $sSQL)) fail(pg_last_error($oDB->connection));
                    $iLines++;
                    if ($iLines == 1000) {
                        echo '.';
                        $iLines = 0;
                    }
                }
            }
            usleep(10);
        }

        fclose($hFile);

        $bAnyBusy = true;
        while ($bAnyBusy) {
            $bAnyBusy = false;
            for ($i = 0; $i < $iInstances; $i++) {
                if (pg_connection_busy($aDBInstances[$i]->connection)) $bAnyBusy = true;
            }
            usleep(10);
        }
        echo "\n";
    }

    info('Creating indexes on Tiger data');
    $sTemplate = file_get_contents(CONST_BasePath.'/sql/tiger_import_finish.sql');
    $sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
    $sTemplate = replace_tablespace(
        '{ts:aux-data}',
        CONST_Tablespace_Aux_Data,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:aux-index}',
        CONST_Tablespace_Aux_Index,
        $sTemplate
    );
    pgsqlRunScript($sTemplate, false);
}

if ($aCMDResult['calculate-postcodes'] || $aCMDResult['all']) {
    info('Calculate Postcodes');
    $bDidSomething = true;
    $oDB =& getDB();
    if (!pg_query($oDB->connection, 'TRUNCATE location_postcode')) {
        fail(pg_last_error($oDB->connection));
    }

    $sSQL  = 'INSERT INTO location_postcode';
    $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
    $sSQL .= "SELECT nextval('seq_place'), 1, country_code,";
    $sSQL .= "       upper(trim (both ' ' from address->'postcode')) as pc,";
    $sSQL .= '       ST_Centroid(ST_Collect(ST_Centroid(geometry)))';
    $sSQL .= '  FROM placex';
    $sSQL .= " WHERE address ? 'postcode' AND address->'postcode' NOT SIMILAR TO '%(,|;)%'";
    $sSQL .= '       AND geometry IS NOT null';
    $sSQL .= ' GROUP BY country_code, pc';

    if (!pg_query($oDB->connection, $sSQL)) {
        fail(pg_last_error($oDB->connection));
    }

    if (CONST_Use_Extra_US_Postcodes) {
        // only add postcodes that are not yet available in OSM
        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, 'us', postcode,";
        $sSQL .= '       ST_SetSRID(ST_Point(x,y),4326)';
        $sSQL .= '  FROM us_postcode WHERE postcode NOT IN';
        $sSQL .= '        (SELECT postcode FROM location_postcode';
        $sSQL .= "          WHERE country_code = 'us')";
        if (!pg_query($oDB->connection, $sSQL)) fail(pg_last_error($oDB->connection));
    }

    // add missing postcodes for GB (if available)
    $sSQL  = 'INSERT INTO location_postcode';
    $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
    $sSQL .= "SELECT nextval('seq_place'), 1, 'gb', postcode, geometry";
    $sSQL .= '  FROM gb_postcode WHERE postcode NOT IN';
    $sSQL .= '           (SELECT postcode FROM location_postcode';
    $sSQL .= "             WHERE country_code = 'gb')";
    if (!pg_query($oDB->connection, $sSQL)) fail(pg_last_error($oDB->connection));

    if (!$aCMDResult['all']) {
        $sSQL = "DELETE FROM word WHERE class='place' and type='postcode'";
        $sSQL .= 'and word NOT IN (SELECT postcode FROM location_postcode)';
        if (!pg_query($oDB->connection, $sSQL)) {
            fail(pg_last_error($oDB->connection));
        }
    }
    $sSQL = 'SELECT count(getorcreate_postcode_id(v)) FROM ';
    $sSQL .= '(SELECT distinct(postcode) as v FROM location_postcode) p';

    if (!pg_query($oDB->connection, $sSQL)) {
        fail(pg_last_error($oDB->connection));
    }
}

if ($aCMDResult['osmosis-init']) {
    $bDidSomething = true;
    echo "Command 'osmosis-init' no longer available, please use utils/update.php --init-updates.\n";
}

if ($aCMDResult['index'] || $aCMDResult['all']) {
    $bDidSomething = true;
    $sOutputFile = '';
    $sBaseCmd = CONST_InstallPath.'/nominatim/nominatim -i -d '.$aDSNInfo['database'].' -P '.$aDSNInfo['port'].' -t '.$iInstances.$sOutputFile;
    info('Index ranks 0 - 4');
    passthruCheckReturn($sBaseCmd.' -R 4');
    if (!$aCMDResult['index-noanalyse']) pgsqlRunScript('ANALYSE');
    info('Index ranks 5 - 25');
    passthruCheckReturn($sBaseCmd.' -r 5 -R 25');
    if (!$aCMDResult['index-noanalyse']) pgsqlRunScript('ANALYSE');
    info('Index ranks 26 - 30');
    passthruCheckReturn($sBaseCmd.' -r 26');

    info('Index postcodes');
    $oDB =& getDB();
    $sSQL = 'UPDATE location_postcode SET indexed_status = 0';
    if (!pg_query($oDB->connection, $sSQL)) fail(pg_last_error($oDB->connection));
}

if ($aCMDResult['create-search-indices'] || $aCMDResult['all']) {
    info('Create Search indices');
    $bDidSomething = true;

    $sTemplate = file_get_contents(CONST_BasePath.'/sql/indices.src.sql');
    $sTemplate = replace_tablespace(
        '{ts:address-index}',
        CONST_Tablespace_Address_Index,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:search-index}',
        CONST_Tablespace_Search_Index,
        $sTemplate
    );
    $sTemplate = replace_tablespace(
        '{ts:aux-index}',
        CONST_Tablespace_Aux_Index,
        $sTemplate
    );

    pgsqlRunScript($sTemplate);
}

if ($aCMDResult['create-country-names'] || $aCMDResult['all']) {
    info('Create search index for default country names');
    $bDidSomething = true;

    pgsqlRunScript("select getorcreate_country(make_standard_name('uk'), 'gb')");
    pgsqlRunScript("select getorcreate_country(make_standard_name('united states'), 'us')");
    pgsqlRunScript('select count(*) from (select getorcreate_country(make_standard_name(country_code), country_code) from country_name where country_code is not null) as x');
    pgsqlRunScript("select count(*) from (select getorcreate_country(make_standard_name(name->'name'), country_code) from country_name where name ? 'name') as x");

    $sSQL = 'select count(*) from (select getorcreate_country(make_standard_name(v), country_code) from (select country_code, skeys(name) as k, svals(name) as v from country_name) x where k ';
    if (CONST_Languages) {
        $sSQL .= 'in ';
        $sDelim = '(';
        foreach (explode(',', CONST_Languages) as $sLang) {
            $sSQL .= $sDelim."'name:$sLang'";
            $sDelim = ',';
        }
        $sSQL .= ')';
    } else {
        // all include all simple name tags
        $sSQL .= "like 'name:%'";
    }
    $sSQL .= ') v';
    pgsqlRunScript($sSQL);
}

if ($aCMDResult['drop']) {
    info('Drop tables only required for updates');
    // The implementation is potentially a bit dangerous because it uses
    // a positive selection of tables to keep, and deletes everything else.
    // Including any tables that the unsuspecting user might have manually
    // created. USE AT YOUR OWN PERIL.
    $bDidSomething = true;

    // tables we want to keep. everything else goes.
    $aKeepTables = array(
                    '*columns',
                    'import_polygon_*',
                    'import_status',
                    'place_addressline',
                    'location_postcode',
                    'location_property*',
                    'placex',
                    'search_name',
                    'seq_*',
                    'word',
                    'query_log',
                    'new_query_log',
                    'spatial_ref_sys',
                    'country_name',
                    'place_classtype_*'
                   );

    $oDB =& getDB();
    $aDropTables = array();
    $aHaveTables = chksql($oDB->getCol("SELECT tablename FROM pg_tables WHERE schemaname='public'"));

    foreach ($aHaveTables as $sTable) {
        $bFound = false;
        foreach ($aKeepTables as $sKeep) {
            if (fnmatch($sKeep, $sTable)) {
                $bFound = true;
                break;
            }
        }
        if (!$bFound) array_push($aDropTables, $sTable);
    }

    foreach ($aDropTables as $sDrop) {
        if ($aCMDResult['verbose']) echo "dropping table $sDrop\n";
        @pg_query($oDB->connection, "DROP TABLE $sDrop CASCADE");
        // ignore warnings/errors as they might be caused by a table having
        // been deleted already by CASCADE
    }

    if (!is_null(CONST_Osm2pgsql_Flatnode_File) && CONST_Osm2pgsql_Flatnode_File) {
        if ($aCMDResult['verbose']) echo 'deleting '.CONST_Osm2pgsql_Flatnode_File."\n";
        unlink(CONST_Osm2pgsql_Flatnode_File);
    }
}

if (!$bDidSomething) {
    showUsage($aCMDOptions, true);
} else {
    echo "Summary of warnings:\n\n";
    repeatWarnings();
    echo "\n";
    info('Setup finished.');
}


function pgsqlRunScriptFile($sFilename)
{
    global $aCMDResult;
    if (!file_exists($sFilename)) fail('unable to find '.$sFilename);

    // Convert database DSN to psql parameters
    $aDSNInfo = DB::parseDSN(CONST_Database_DSN);
    if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
    $sCMD = 'psql -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'];
    if (!$aCMDResult['verbose']) {
        $sCMD .= ' -q';
    }

    $ahGzipPipes = null;
    if (preg_match('/\\.gz$/', $sFilename)) {
        $aDescriptors = array(
                         0 => array('pipe', 'r'),
                         1 => array('pipe', 'w'),
                         2 => array('file', '/dev/null', 'a')
                        );
        $hGzipProcess = proc_open('zcat '.$sFilename, $aDescriptors, $ahGzipPipes);
        if (!is_resource($hGzipProcess)) fail('unable to start zcat');
        $aReadPipe = $ahGzipPipes[1];
        fclose($ahGzipPipes[0]);
    } else {
        $sCMD .= ' -f '.$sFilename;
        $aReadPipe = array('pipe', 'r');
    }

    $aDescriptors = array(
                     0 => $aReadPipe,
                     1 => array('pipe', 'w'),
                     2 => array('file', '/dev/null', 'a')
                    );
    $ahPipes = null;
    $hProcess = proc_open($sCMD, $aDescriptors, $ahPipes);
    if (!is_resource($hProcess)) fail('unable to start pgsql');


    // TODO: error checking
    while (!feof($ahPipes[1])) {
        echo fread($ahPipes[1], 4096);
    }
    fclose($ahPipes[1]);

    $iReturn = proc_close($hProcess);
    if ($iReturn > 0) {
        fail("pgsql returned with error code ($iReturn)");
    }
    if ($ahGzipPipes) {
        fclose($ahGzipPipes[1]);
        proc_close($hGzipProcess);
    }
}

function pgsqlRunScript($sScript, $bfatal = true)
{
    global $aCMDResult;
    runSQLScript(
        $sScript,
        $bfatal,
        $aCMDResult['verbose'],
        $aCMDResult['ignore-errors']
    );
}

function pgsqlRunPartitionScript($sTemplate)
{
    global $aCMDResult;
    $oDB =& getDB();

    $sSQL = 'select distinct partition from country_name';
    $aPartitions = chksql($oDB->getCol($sSQL));
    if (!$aCMDResult['no-partitions']) $aPartitions[] = 0;

    preg_match_all('#^-- start(.*?)^-- end#ms', $sTemplate, $aMatches, PREG_SET_ORDER);
    foreach ($aMatches as $aMatch) {
        $sResult = '';
        foreach ($aPartitions as $sPartitionName) {
            $sResult .= str_replace('-partition-', $sPartitionName, $aMatch[1]);
        }
        $sTemplate = str_replace($aMatch[0], $sResult, $sTemplate);
    }

    pgsqlRunScript($sTemplate);
}

function pgsqlRunRestoreData($sDumpFile)
{
    // Convert database DSN to psql parameters
    $aDSNInfo = DB::parseDSN(CONST_Database_DSN);
    if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
    $sCMD = 'pg_restore -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'].' -Fc -a '.$sDumpFile;

    $aDescriptors = array(
                     0 => array('pipe', 'r'),
                     1 => array('pipe', 'w'),
                     2 => array('file', '/dev/null', 'a')
                    );
    $ahPipes = null;
    $hProcess = proc_open($sCMD, $aDescriptors, $ahPipes);
    if (!is_resource($hProcess)) fail('unable to start pg_restore');

    fclose($ahPipes[0]);

    // TODO: error checking
    while (!feof($ahPipes[1])) {
        echo fread($ahPipes[1], 4096);
    }
    fclose($ahPipes[1]);

    $iReturn = proc_close($hProcess);
}

function pgsqlRunDropAndRestore($sDumpFile)
{
    // Convert database DSN to psql parameters
    $aDSNInfo = DB::parseDSN(CONST_Database_DSN);
    if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;
    $sCMD = 'pg_restore -p '.$aDSNInfo['port'].' -d '.$aDSNInfo['database'].' -Fc --clean '.$sDumpFile;

    $aDescriptors = array(
                     0 => array('pipe', 'r'),
                     1 => array('pipe', 'w'),
                     2 => array('file', '/dev/null', 'a')
                    );
    $ahPipes = null;
    $hProcess = proc_open($sCMD, $aDescriptors, $ahPipes);
    if (!is_resource($hProcess)) fail('unable to start pg_restore');

    fclose($ahPipes[0]);

    // TODO: error checking
    while (!feof($ahPipes[1])) {
        echo fread($ahPipes[1], 4096);
    }
    fclose($ahPipes[1]);

    $iReturn = proc_close($hProcess);
}

function passthruCheckReturn($cmd)
{
    $result = -1;
    passthru($cmd, $result);
    if ($result != 0) fail('Error executing external command: '.$cmd);
}

function replace_tablespace($sTemplate, $sTablespace, $sSql)
{
    if ($sTablespace) {
        $sSql = str_replace($sTemplate, 'TABLESPACE "'.$sTablespace.'"', $sSql);
    } else {
        $sSql = str_replace($sTemplate, '', $sSql);
    }

    return $sSql;
}

function create_sql_functions($aCMDResult)
{
    $sTemplate = file_get_contents(CONST_BasePath.'/sql/functions.sql');
    $sTemplate = str_replace('{modulepath}', CONST_InstallPath.'/module', $sTemplate);
    if ($aCMDResult['enable-diff-updates']) {
        $sTemplate = str_replace('RETURN NEW; -- %DIFFUPDATES%', '--', $sTemplate);
    }
    if ($aCMDResult['enable-debug-statements']) {
        $sTemplate = str_replace('--DEBUG:', '', $sTemplate);
    }
    if (CONST_Limit_Reindexing) {
        $sTemplate = str_replace('--LIMIT INDEXING:', '', $sTemplate);
    }
    if (!CONST_Use_US_Tiger_Data) {
        $sTemplate = str_replace('-- %NOTIGERDATA% ', '', $sTemplate);
    }
    if (!CONST_Use_Aux_Location_data) {
        $sTemplate = str_replace('-- %NOAUXDATA% ', '', $sTemplate);
    }
    pgsqlRunScript($sTemplate);
}
