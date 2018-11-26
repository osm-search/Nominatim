<?php

namespace Nominatim\Setup;

require_once(CONST_BasePath.'/lib/setup/AddressLevelParser.php');

class SetupFunctions
{
    protected $iCacheMemory;
    protected $iInstances;
    protected $sModulePath;
    protected $aDSNInfo;
    protected $bVerbose;
    protected $sIgnoreErrors;
    protected $bEnableDiffUpdates;
    protected $bEnableDebugStatements;
    protected $bNoPartitions;
    protected $oDB = null;

    public function __construct(array $aCMDResult)
    {
        // by default, use all but one processor, but never more than 15.
        $this->iInstances = isset($aCMDResult['threads'])
            ? $aCMDResult['threads']
            : (min(16, getProcessorCount()) - 1);

        if ($this->iInstances < 1) {
            $this->iInstances = 1;
            warn('resetting threads to '.$this->iInstances);
        }

        // Assume we can steal all the cache memory in the box (unless told otherwise)
        if (isset($aCMDResult['osm2pgsql-cache'])) {
            $this->iCacheMemory = $aCMDResult['osm2pgsql-cache'];
        } else {
            $this->iCacheMemory = getCacheMemoryMB();
        }

        $this->sModulePath = CONST_Database_Module_Path;
        info('module path: ' . $this->sModulePath);

        // parse database string
        $this->aDSNInfo = array_filter(\DB::parseDSN(CONST_Database_DSN));
        if (!isset($this->aDSNInfo['port'])) {
            $this->aDSNInfo['port'] = 5432;
        }

        // setting member variables based on command line options stored in $aCMDResult
        $this->bVerbose = $aCMDResult['verbose'];

        //setting default values which are not set by the update.php array
        if (isset($aCMDResult['ignore-errors'])) {
            $this->sIgnoreErrors = $aCMDResult['ignore-errors'];
        } else {
            $this->sIgnoreErrors = false;
        }
        if (isset($aCMDResult['enable-debug-statements'])) {
            $this->bEnableDebugStatements = $aCMDResult['enable-debug-statements'];
        } else {
            $this->bEnableDebugStatements = false;
        }
        if (isset($aCMDResult['no-partitions'])) {
            $this->bNoPartitions = $aCMDResult['no-partitions'];
        } else {
            $this->bNoPartitions = false;
        }
        if (isset($aCMDResult['enable-diff-updates'])) {
            $this->bEnableDiffUpdates = $aCMDResult['enable-diff-updates'];
        } else {
            $this->bEnableDiffUpdates = false;
        }
    }

    public function createDB()
    {
        info('Create DB');
        $sDB = \DB::connect(CONST_Database_DSN, false);
        if (!\PEAR::isError($sDB)) {
            fail('database already exists ('.CONST_Database_DSN.')');
        }

        $sCreateDBCmd = 'createdb -E UTF-8 -p '.$this->aDSNInfo['port'].' '.$this->aDSNInfo['database'];
        if (isset($this->aDSNInfo['username'])) {
            $sCreateDBCmd .= ' -U '.$this->aDSNInfo['username'];
        }

        if (isset($this->aDSNInfo['hostspec'])) {
            $sCreateDBCmd .= ' -h '.$this->aDSNInfo['hostspec'];
        }

        $result = $this->runWithPgEnv($sCreateDBCmd);
        if ($result != 0) fail('Error executing external command: '.$sCreateDBCmd);
    }

    public function connect()
    {
        $this->oDB =& getDB();
    }

    public function setupDB()
    {
        info('Setup DB');

        $fPostgresVersion = getPostgresVersion($this->oDB);
        echo 'Postgres version found: '.$fPostgresVersion."\n";

        if ($fPostgresVersion < 9.01) {
            fail('Minimum supported version of Postgresql is 9.1.');
        }

        $this->pgsqlRunScript('CREATE EXTENSION IF NOT EXISTS hstore');
        $this->pgsqlRunScript('CREATE EXTENSION IF NOT EXISTS postgis');

        // For extratags and namedetails the hstore_to_json converter is
        // needed which is only available from Postgresql 9.3+. For older
        // versions add a dummy function that returns nothing.
        $iNumFunc = chksql($this->oDB->getOne("select count(*) from pg_proc where proname = 'hstore_to_json'"));

        if ($iNumFunc == 0) {
            $this->pgsqlRunScript("create function hstore_to_json(dummy hstore) returns text AS 'select null::text' language sql immutable");
            warn('Postgresql is too old. extratags and namedetails API not available.');
        }


        $fPostgisVersion = getPostgisVersion($this->oDB);
        echo 'Postgis version found: '.$fPostgisVersion."\n";

        if ($fPostgisVersion < 2.1) {
            // Functions were renamed in 2.1 and throw an annoying deprecation warning
            $this->pgsqlRunScript('ALTER FUNCTION st_line_interpolate_point(geometry, double precision) RENAME TO ST_LineInterpolatePoint');
            $this->pgsqlRunScript('ALTER FUNCTION ST_Line_Locate_Point(geometry, geometry) RENAME TO ST_LineLocatePoint');
        }
        if ($fPostgisVersion < 2.2) {
            $this->pgsqlRunScript('ALTER FUNCTION ST_Distance_Spheroid(geometry, geometry, spheroid) RENAME TO ST_DistanceSpheroid');
        }

        $i = chksql($this->oDB->getOne("select count(*) from pg_user where usename = '".CONST_Database_Web_User."'"));
        if ($i == 0) {
            echo "\nERROR: Web user '".CONST_Database_Web_User."' does not exist. Create it with:\n";
            echo "\n          createuser ".CONST_Database_Web_User."\n\n";
            exit(1);
        }

        // Try accessing the C module, so we know early if something is wrong
        if (!checkModulePresence()) {
            fail('error loading nominatim.so module');
        }

        if (!file_exists(CONST_ExtraDataPath.'/country_osm_grid.sql.gz')) {
            echo 'Error: you need to download the country_osm_grid first:';
            echo "\n    wget -O ".CONST_ExtraDataPath."/country_osm_grid.sql.gz https://www.nominatim.org/data/country_grid.sql.gz\n";
            exit(1);
        }
        $this->pgsqlRunScriptFile(CONST_BasePath.'/data/country_name.sql');
        $this->pgsqlRunScriptFile(CONST_BasePath.'/data/country_osm_grid.sql.gz');
        $this->pgsqlRunScriptFile(CONST_BasePath.'/data/gb_postcode_table.sql');

        $sPostcodeFilename = CONST_BasePath.'/data/gb_postcode_data.sql.gz';
        if (file_exists($sPostcodeFilename)) {
            $this->pgsqlRunScriptFile($sPostcodeFilename);
        } else {
            warn('optional external UK postcode table file ('.$sPostcodeFilename.') not found. Skipping.');
        }

        if (CONST_Use_Extra_US_Postcodes) {
            $this->pgsqlRunScriptFile(CONST_BasePath.'/data/us_postcode.sql');
        }

        if ($this->bNoPartitions) {
            $this->pgsqlRunScript('update country_name set partition = 0');
        }

        // the following will be needed by createFunctions later but
        // is only defined in the subsequently called createTables
        // Create dummies here that will be overwritten by the proper
        // versions in create-tables.
        $this->pgsqlRunScript('CREATE TABLE IF NOT EXISTS place_boundingbox ()');
        $this->pgsqlRunScript('CREATE TYPE wikipedia_article_match AS ()', false);
    }

    public function importData($sOSMFile)
    {
        info('Import data');

        $osm2pgsql = CONST_Osm2pgsql_Binary;
        if (!file_exists($osm2pgsql)) {
            echo "Check CONST_Osm2pgsql_Binary in your local settings file.\n";
            echo "Normally you should not need to set this manually.\n";
            fail("osm2pgsql not found in '$osm2pgsql'");
        }

        $osm2pgsql .= ' -S '.CONST_Import_Style;

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
        $osm2pgsql .= ' -C '.$this->iCacheMemory;
        $osm2pgsql .= ' -P '.$this->aDSNInfo['port'];
        if (isset($this->aDSNInfo['username'])) {
            $osm2pgsql .= ' -U '.$this->aDSNInfo['username'];
        }
        if (isset($this->aDSNInfo['hostspec'])) {
            $osm2pgsql .= ' -H '.$this->aDSNInfo['hostspec'];
        }
        $osm2pgsql .= ' -d '.$this->aDSNInfo['database'].' '.$sOSMFile;

        $this->runWithPgEnv($osm2pgsql);

        if (!$this->sIgnoreErrors && !chksql($this->oDB->getRow('select * from place limit 1'))) {
            fail('No Data');
        }
    }

    public function createFunctions()
    {
        info('Create Functions');

        // Try accessing the C module, so we know eif something is wrong
        // update.php calls this function
        if (!checkModulePresence()) {
            fail('error loading nominatim.so module');
        }
        $this->createSqlFunctions();
    }

    public function createTables($bReverseOnly = false)
    {
        info('Create Tables');

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/tables.sql');
        $sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
        $sTemplate = $this->replaceTablespace(
            '{ts:address-data}',
            CONST_Tablespace_Address_Data,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:address-index}',
            CONST_Tablespace_Address_Index,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:search-data}',
            CONST_Tablespace_Search_Data,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:search-index}',
            CONST_Tablespace_Search_Index,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:aux-data}',
            CONST_Tablespace_Aux_Data,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:aux-index}',
            CONST_Tablespace_Aux_Index,
            $sTemplate
        );

        $this->pgsqlRunScript($sTemplate, false);

        if ($bReverseOnly) {
            $this->pgExec('DROP TABLE search_name');
        }

        $oAlParser = new AddressLevelParser(CONST_Address_Level_Config);
        $oAlParser->createTable($this->oDB, 'address_levels');
    }

    public function createPartitionTables()
    {
        info('Create Partition Tables');

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/partition-tables.src.sql');
        $sTemplate = $this->replaceTablespace(
            '{ts:address-data}',
            CONST_Tablespace_Address_Data,
            $sTemplate
        );

        $sTemplate = $this->replaceTablespace(
            '{ts:address-index}',
            CONST_Tablespace_Address_Index,
            $sTemplate
        );

        $sTemplate = $this->replaceTablespace(
            '{ts:search-data}',
            CONST_Tablespace_Search_Data,
            $sTemplate
        );

        $sTemplate = $this->replaceTablespace(
            '{ts:search-index}',
            CONST_Tablespace_Search_Index,
            $sTemplate
        );

        $sTemplate = $this->replaceTablespace(
            '{ts:aux-data}',
            CONST_Tablespace_Aux_Data,
            $sTemplate
        );

        $sTemplate = $this->replaceTablespace(
            '{ts:aux-index}',
            CONST_Tablespace_Aux_Index,
            $sTemplate
        );

        $this->pgsqlRunPartitionScript($sTemplate);
    }

    public function createPartitionFunctions()
    {
        info('Create Partition Functions');

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/partition-functions.src.sql');
        $this->pgsqlRunPartitionScript($sTemplate);
    }

    public function importWikipediaArticles()
    {
        $sWikiArticlesFile = CONST_Wikipedia_Data_Path.'/wikipedia_article.sql.bin';
        $sWikiRedirectsFile = CONST_Wikipedia_Data_Path.'/wikipedia_redirect.sql.bin';
        if (file_exists($sWikiArticlesFile)) {
            info('Importing wikipedia articles');
            $this->pgsqlRunDropAndRestore($sWikiArticlesFile);
        } else {
            warn('wikipedia article dump file not found - places will have default importance');
        }
        if (file_exists($sWikiRedirectsFile)) {
            info('Importing wikipedia redirects');
            $this->pgsqlRunDropAndRestore($sWikiRedirectsFile);
        } else {
            warn('wikipedia redirect dump file not found - some place importance values may be missing');
        }
    }

    public function loadData($bDisableTokenPrecalc)
    {
        info('Drop old Data');

        $this->pgExec('TRUNCATE word');
        echo '.';
        $this->pgExec('TRUNCATE placex');
        echo '.';
        $this->pgExec('TRUNCATE location_property_osmline');
        echo '.';
        $this->pgExec('TRUNCATE place_addressline');
        echo '.';
        $this->pgExec('TRUNCATE place_boundingbox');
        echo '.';
        $this->pgExec('TRUNCATE location_area');
        echo '.';
        if (!$this->dbReverseOnly()) {
            $this->pgExec('TRUNCATE search_name');
            echo '.';
        }
        $this->pgExec('TRUNCATE search_name_blank');
        echo '.';
        $this->pgExec('DROP SEQUENCE seq_place');
        echo '.';
        $this->pgExec('CREATE SEQUENCE seq_place start 100000');
        echo '.';

        $sSQL = 'select distinct partition from country_name';
        $aPartitions = chksql($this->oDB->getCol($sSQL));
        if (!$this->bNoPartitions) $aPartitions[] = 0;
        foreach ($aPartitions as $sPartition) {
            $this->pgExec('TRUNCATE location_road_'.$sPartition);
            echo '.';
        }

        // used by getorcreate_word_id to ignore frequent partial words
        $sSQL = 'CREATE OR REPLACE FUNCTION get_maxwordfreq() RETURNS integer AS ';
        $sSQL .= '$$ SELECT '.CONST_Max_Word_Frequency.' as maxwordfreq; $$ LANGUAGE SQL IMMUTABLE';
        $this->pgExec($sSQL);
        echo ".\n";

        // pre-create the word list
        if (!$bDisableTokenPrecalc) {
            info('Loading word list');
            $this->pgsqlRunScriptFile(CONST_BasePath.'/data/words.sql');
        }

        info('Load Data');
        $sColumns = 'osm_type, osm_id, class, type, name, admin_level, address, extratags, geometry';
        $aDBInstances = array();
        $iLoadThreads = max(1, $this->iInstances - 1);
        for ($i = 0; $i < $iLoadThreads; $i++) {
            $aDBInstances[$i] =& getDB(true);
            $sSQL = "INSERT INTO placex ($sColumns) SELECT $sColumns FROM place WHERE osm_id % $iLoadThreads = $i";
            $sSQL .= " and not (class='place' and type='houses' and osm_type='W'";
            $sSQL .= "          and ST_GeometryType(geometry) = 'ST_LineString')";
            $sSQL .= ' and ST_IsValid(geometry)';
            if ($this->bVerbose) echo "$sSQL\n";
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
        if ($this->bVerbose) echo "$sSQL\n";
        if (!pg_send_query($aDBInstances[$iLoadThreads]->connection, $sSQL)) {
            fail(pg_last_error($aDBInstances[$iLoadThreads]->connection));
        }

        $bFailed = false;
        for ($i = 0; $i <= $iLoadThreads; $i++) {
            while (($hPGresult = pg_get_result($aDBInstances[$i]->connection)) !== false) {
                $resultStatus = pg_result_status($hPGresult);
                // PGSQL_EMPTY_QUERY, PGSQL_COMMAND_OK, PGSQL_TUPLES_OK,
                // PGSQL_COPY_OUT, PGSQL_COPY_IN, PGSQL_BAD_RESPONSE,
                // PGSQL_NONFATAL_ERROR and PGSQL_FATAL_ERROR
                // echo 'Query result ' . $i . ' is: ' . $resultStatus . "\n";
                if ($resultStatus != PGSQL_COMMAND_OK && $resultStatus != PGSQL_TUPLES_OK) {
                    $resultError = pg_result_error($hPGresult);
                    echo '-- error text ' . $i . ': ' . $resultError . "\n";
                    $bFailed = true;
                }
            }
        }
        if ($bFailed) {
            fail('SQL errors loading placex and/or location_property_osmline tables');
        }
        echo "\n";
        info('Reanalysing database');
        $this->pgsqlRunScript('ANALYSE');

        $sDatabaseDate = getDatabaseDate($this->oDB);
        pg_query($this->oDB->connection, 'TRUNCATE import_status');
        if ($sDatabaseDate === false) {
            warn('could not determine database date.');
        } else {
            $sSQL = "INSERT INTO import_status (lastimportdate) VALUES('".$sDatabaseDate."')";
            pg_query($this->oDB->connection, $sSQL);
            echo "Latest data imported from $sDatabaseDate.\n";
        }
    }

    public function importTigerData()
    {
        info('Import Tiger data');

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/tiger_import_start.sql');
        $sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
        $sTemplate = $this->replaceTablespace(
            '{ts:aux-data}',
            CONST_Tablespace_Aux_Data,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:aux-index}',
            CONST_Tablespace_Aux_Index,
            $sTemplate
        );
        $this->pgsqlRunScript($sTemplate, false);

        $aDBInstances = array();
        for ($i = 0; $i < $this->iInstances; $i++) {
            $aDBInstances[$i] =& getDB(true);
        }

        foreach (glob(CONST_Tiger_Data_Path.'/*.sql') as $sFile) {
            echo $sFile.': ';
            $hFile = fopen($sFile, 'r');
            $sSQL = fgets($hFile, 100000);
            $iLines = 0;
            while (true) {
                for ($i = 0; $i < $this->iInstances; $i++) {
                    if (!pg_connection_busy($aDBInstances[$i]->connection)) {
                        while (pg_get_result($aDBInstances[$i]->connection));
                        $sSQL = fgets($hFile, 100000);
                        if (!$sSQL) break 2;
                        if (!pg_send_query($aDBInstances[$i]->connection, $sSQL)) fail(pg_last_error($this->oDB->connection));
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
                for ($i = 0; $i < $this->iInstances; $i++) {
                    if (pg_connection_busy($aDBInstances[$i]->connection)) $bAnyBusy = true;
                }
                usleep(10);
            }
            echo "\n";
        }

        info('Creating indexes on Tiger data');
        $sTemplate = file_get_contents(CONST_BasePath.'/sql/tiger_import_finish.sql');
        $sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
        $sTemplate = $this->replaceTablespace(
            '{ts:aux-data}',
            CONST_Tablespace_Aux_Data,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:aux-index}',
            CONST_Tablespace_Aux_Index,
            $sTemplate
        );
        $this->pgsqlRunScript($sTemplate, false);
    }

    public function calculatePostcodes($bCMDResultAll)
    {
        info('Calculate Postcodes');
        $this->pgExec('TRUNCATE location_postcode');

        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, country_code,";
        $sSQL .= "       upper(trim (both ' ' from address->'postcode')) as pc,";
        $sSQL .= '       ST_Centroid(ST_Collect(ST_Centroid(geometry)))';
        $sSQL .= '  FROM placex';
        $sSQL .= " WHERE address ? 'postcode' AND address->'postcode' NOT SIMILAR TO '%(,|;)%'";
        $sSQL .= '       AND geometry IS NOT null';
        $sSQL .= ' GROUP BY country_code, pc';
        $this->pgExec($sSQL);

        if (CONST_Use_Extra_US_Postcodes) {
            // only add postcodes that are not yet available in OSM
            $sSQL  = 'INSERT INTO location_postcode';
            $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
            $sSQL .= "SELECT nextval('seq_place'), 1, 'us', postcode,";
            $sSQL .= '       ST_SetSRID(ST_Point(x,y),4326)';
            $sSQL .= '  FROM us_postcode WHERE postcode NOT IN';
            $sSQL .= '        (SELECT postcode FROM location_postcode';
            $sSQL .= "          WHERE country_code = 'us')";
            $this->pgExec($sSQL);
        }

        // add missing postcodes for GB (if available)
        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, 'gb', postcode, geometry";
        $sSQL .= '  FROM gb_postcode WHERE postcode NOT IN';
        $sSQL .= '           (SELECT postcode FROM location_postcode';
        $sSQL .= "             WHERE country_code = 'gb')";
        $this->pgExec($sSQL);

        if (!$bCMDResultAll) {
            $sSQL = "DELETE FROM word WHERE class='place' and type='postcode'";
            $sSQL .= 'and word NOT IN (SELECT postcode FROM location_postcode)';
            $this->pgExec($sSQL);
        }

        $sSQL = 'SELECT count(getorcreate_postcode_id(v)) FROM ';
        $sSQL .= '(SELECT distinct(postcode) as v FROM location_postcode) p';
        $this->pgExec($sSQL);
    }

    public function index($bIndexNoanalyse)
    {
        $sOutputFile = '';
        $sBaseCmd = CONST_InstallPath.'/nominatim/nominatim -i -d '.$this->aDSNInfo['database'].' -P '
            .$this->aDSNInfo['port'].' -t '.$this->iInstances.$sOutputFile;
        if (isset($this->aDSNInfo['hostspec'])) {
            $sBaseCmd .= ' -H '.$this->aDSNInfo['hostspec'];
        }
        if (isset($this->aDSNInfo['username'])) {
            $sBaseCmd .= ' -U '.$this->aDSNInfo['username'];
        }

        info('Index ranks 0 - 4');
        $iStatus = $this->runWithPgEnv($sBaseCmd.' -R 4');
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }
        if (!$bIndexNoanalyse) $this->pgsqlRunScript('ANALYSE');

        info('Index ranks 5 - 25');
        $iStatus = $this->runWithPgEnv($sBaseCmd.' -r 5 -R 25');
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }
        if (!$bIndexNoanalyse) $this->pgsqlRunScript('ANALYSE');

        info('Index ranks 26 - 30');
        $iStatus = $this->runWithPgEnv($sBaseCmd.' -r 26');
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }

        info('Index postcodes');
        $sSQL = 'UPDATE location_postcode SET indexed_status = 0';
        $this->pgExec($sSQL);
    }

    public function createSearchIndices()
    {
        info('Create Search indices');

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/indices.src.sql');
        if (!$this->dbReverseOnly()) {
            $sTemplate .= file_get_contents(CONST_BasePath.'/sql/indices_search.src.sql');
        }
        $sTemplate = str_replace('{www-user}', CONST_Database_Web_User, $sTemplate);
        $sTemplate = $this->replaceTablespace(
            '{ts:address-index}',
            CONST_Tablespace_Address_Index,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:search-index}',
            CONST_Tablespace_Search_Index,
            $sTemplate
        );
        $sTemplate = $this->replaceTablespace(
            '{ts:aux-index}',
            CONST_Tablespace_Aux_Index,
            $sTemplate
        );
        $this->pgsqlRunScript($sTemplate);
    }

    public function createCountryNames()
    {
        info('Create search index for default country names');

        $this->pgsqlRunScript("select getorcreate_country(make_standard_name('uk'), 'gb')");
        $this->pgsqlRunScript("select getorcreate_country(make_standard_name('united states'), 'us')");
        $this->pgsqlRunScript('select count(*) from (select getorcreate_country(make_standard_name(country_code), country_code) from country_name where country_code is not null) as x');
        $this->pgsqlRunScript("select count(*) from (select getorcreate_country(make_standard_name(name->'name'), country_code) from country_name where name ? 'name') as x");
        $sSQL = 'select count(*) from (select getorcreate_country(make_standard_name(v),'
            .'country_code) from (select country_code, skeys(name) as k, svals(name) as v from country_name) x where k ';
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
        $this->pgsqlRunScript($sSQL);
    }

    public function drop()
    {
        info('Drop tables only required for updates');

        // The implementation is potentially a bit dangerous because it uses
        // a positive selection of tables to keep, and deletes everything else.
        // Including any tables that the unsuspecting user might have manually
        // created. USE AT YOUR OWN PERIL.
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
                        'place_classtype_*',
                        'country_osm_grid'
                       );

        $aDropTables = array();
        $aHaveTables = chksql($this->oDB->getCol("SELECT tablename FROM pg_tables WHERE schemaname='public'"));

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
            if ($this->bVerbose) echo "Dropping table $sDrop\n";
            @pg_query($this->oDB->connection, "DROP TABLE $sDrop CASCADE");
            // ignore warnings/errors as they might be caused by a table having
            // been deleted already by CASCADE
        }

        if (!is_null(CONST_Osm2pgsql_Flatnode_File) && CONST_Osm2pgsql_Flatnode_File) {
            if (file_exists(CONST_Osm2pgsql_Flatnode_File)) {
                if ($this->bVerbose) echo 'Deleting '.CONST_Osm2pgsql_Flatnode_File."\n";
                unlink(CONST_Osm2pgsql_Flatnode_File);
            }
        }
    }

    private function pgsqlRunDropAndRestore($sDumpFile)
    {
        $sCMD = 'pg_restore -p '.$this->aDSNInfo['port'].' -d '.$this->aDSNInfo['database'].' -Fc --clean '.$sDumpFile;
        if (isset($this->aDSNInfo['hostspec'])) {
            $sCMD .= ' -h '.$this->aDSNInfo['hostspec'];
        }
        if (isset($this->aDSNInfo['username'])) {
            $sCMD .= ' -U '.$this->aDSNInfo['username'];
        }

        $this->runWithPgEnv($sCMD);
    }

    private function pgsqlRunScript($sScript, $bfatal = true)
    {
        runSQLScript(
            $sScript,
            $bfatal,
            $this->bVerbose,
            $this->sIgnoreErrors
        );
    }

    private function createSqlFunctions()
    {
        $sTemplate = file_get_contents(CONST_BasePath.'/sql/functions.sql');
        $sTemplate = str_replace('{modulepath}', $this->sModulePath, $sTemplate);
        if ($this->bEnableDiffUpdates) {
            $sTemplate = str_replace('RETURN NEW; -- %DIFFUPDATES%', '--', $sTemplate);
        }
        if ($this->bEnableDebugStatements) {
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

        $sReverseOnly = $this->dbReverseOnly() ? 'true' : 'false';
        $sTemplate = str_replace('%REVERSE-ONLY%', $sReverseOnly, $sTemplate);

        $this->pgsqlRunScript($sTemplate);
    }

    private function pgsqlRunPartitionScript($sTemplate)
    {
        $sSQL = 'select distinct partition from country_name';
        $aPartitions = chksql($this->oDB->getCol($sSQL));
        if (!$this->bNoPartitions) $aPartitions[] = 0;

        preg_match_all('#^-- start(.*?)^-- end#ms', $sTemplate, $aMatches, PREG_SET_ORDER);
        foreach ($aMatches as $aMatch) {
            $sResult = '';
            foreach ($aPartitions as $sPartitionName) {
                $sResult .= str_replace('-partition-', $sPartitionName, $aMatch[1]);
            }
            $sTemplate = str_replace($aMatch[0], $sResult, $sTemplate);
        }

        $this->pgsqlRunScript($sTemplate);
    }

    private function pgsqlRunScriptFile($sFilename)
    {
        if (!file_exists($sFilename)) fail('unable to find '.$sFilename);

        $sCMD = 'psql -p '.$this->aDSNInfo['port'].' -d '.$this->aDSNInfo['database'];
        if (!$this->bVerbose) {
            $sCMD .= ' -q';
        }
        if (isset($this->aDSNInfo['hostspec'])) {
            $sCMD .= ' -h '.$this->aDSNInfo['hostspec'];
        }
        if (isset($this->aDSNInfo['username'])) {
            $sCMD .= ' -U '.$this->aDSNInfo['username'];
        }
        $aProcEnv = null;
        if (isset($this->aDSNInfo['password'])) {
            $aProcEnv = array_merge(array('PGPASSWORD' => $this->aDSNInfo['password']), $_ENV);
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
        $hProcess = proc_open($sCMD, $aDescriptors, $ahPipes, null, $aProcEnv);
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

    private function replaceTablespace($sTemplate, $sTablespace, $sSql)
    {
        if ($sTablespace) {
            $sSql = str_replace($sTemplate, 'TABLESPACE "'.$sTablespace.'"', $sSql);
        } else {
            $sSql = str_replace($sTemplate, '', $sSql);
        }
        return $sSql;
    }

    private function runWithPgEnv($sCmd)
    {
        if ($this->bVerbose) {
            echo "Execute: $sCmd\n";
        }

        $aProcEnv = null;

        if (isset($this->aDSNInfo['password'])) {
            $aProcEnv = array_merge(array('PGPASSWORD' => $this->aDSNInfo['password']), $_ENV);
        }

        return runWithEnv($sCmd, $aProcEnv);
    }

    /**
     * Execute the SQL command on the open database.
     *
     * @param string $sSQL SQL command to execute.
     *
     * @return null
     *
     * @pre connect() must have been called.
     */
    private function pgExec($sSQL)
    {
        if (!pg_query($this->oDB->connection, $sSQL)) {
            fail(pg_last_error($this->oDB->connection));
        }
    }

    /**
     * Check if the database is in reverse-only mode.
     *
     * @return True if there is no search_name table and infrastructure.
     */
    private function dbReverseOnly()
    {
        $sSQL = "SELECT count(*) FROM pg_tables WHERE tablename = 'search_name'";
        return !(chksql($this->oDB->getOne($sSQL)));
    }
}
