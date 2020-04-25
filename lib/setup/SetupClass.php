<?php

namespace Nominatim\Setup;

require_once(CONST_BasePath.'/lib/setup/AddressLevelParser.php');
require_once(CONST_BasePath.'/lib/Shell.php');

class SetupFunctions
{
    protected $iCacheMemory;
    protected $iInstances;
    protected $sModulePath;
    protected $aDSNInfo;
    protected $bQuiet;
    protected $bVerbose;
    protected $sIgnoreErrors;
    protected $bEnableDiffUpdates;
    protected $bEnableDebugStatements;
    protected $bNoPartitions;
    protected $bDrop;
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

        if (isset($aCMDResult['osm2pgsql-cache'])) {
            $this->iCacheMemory = $aCMDResult['osm2pgsql-cache'];
        } elseif (!is_null(CONST_Osm2pgsql_Flatnode_File)) {
            // When flatnode files are enabled then disable cache per default.
            $this->iCacheMemory = 0;
        } else {
            // Otherwise: Assume we can steal all the cache memory in the box.
            $this->iCacheMemory = getCacheMemoryMB();
        }

        $this->sModulePath = CONST_Database_Module_Path;
        info('module path: ' . $this->sModulePath);

        // parse database string
        $this->aDSNInfo = \Nominatim\DB::parseDSN(CONST_Database_DSN);
        if (!isset($this->aDSNInfo['port'])) {
            $this->aDSNInfo['port'] = 5432;
        }

        // setting member variables based on command line options stored in $aCMDResult
        $this->bQuiet = isset($aCMDResult['quiet']) && $aCMDResult['quiet'];
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

        $this->bDrop = isset($aCMDResult['drop']) && $aCMDResult['drop'];
    }

    public function createDB()
    {
        info('Create DB');
        $oDB = new \Nominatim\DB;

        if ($oDB->databaseExists()) {
            fail('database already exists ('.CONST_Database_DSN.')');
        }

        $oCmd = (new \Nominatim\Shell('createdb'))
                ->addParams('-E', 'UTF-8')
                ->addParams('-p', $this->aDSNInfo['port']);

        if (isset($this->aDSNInfo['username'])) {
            $oCmd->addParams('-U', $this->aDSNInfo['username']);
        }
        if (isset($this->aDSNInfo['password'])) {
            $oCmd->addEnvPair('PGPASSWORD', $this->aDSNInfo['password']);
        }
        if (isset($this->aDSNInfo['hostspec'])) {
            $oCmd->addParams('-h', $this->aDSNInfo['hostspec']);
        }
        $oCmd->addParams($this->aDSNInfo['database']);

        $result = $oCmd->run();
        if ($result != 0) fail('Error executing external command: '.$oCmd->escapedCmd());
    }

    public function connect()
    {
        $this->oDB = new \Nominatim\DB();
        $this->oDB->connect();
    }

    public function setupDB()
    {
        info('Setup DB');

        $fPostgresVersion = $this->oDB->getPostgresVersion();
        echo 'Postgres version found: '.$fPostgresVersion."\n";

        if ($fPostgresVersion < 9.03) {
            fail('Minimum supported version of Postgresql is 9.3.');
        }

        $this->pgsqlRunScript('CREATE EXTENSION IF NOT EXISTS hstore');
        $this->pgsqlRunScript('CREATE EXTENSION IF NOT EXISTS postgis');

        $fPostgisVersion = $this->oDB->getPostgisVersion();
        echo 'Postgis version found: '.$fPostgisVersion."\n";

        if ($fPostgisVersion < 2.2) {
            echo "Minimum required Postgis version 2.2\n";
            exit(1);
        }

        $i = $this->oDB->getOne("select count(*) from pg_user where usename = '".CONST_Database_Web_User."'");
        if ($i == 0) {
            echo "\nERROR: Web user '".CONST_Database_Web_User."' does not exist. Create it with:\n";
            echo "\n          createuser ".CONST_Database_Web_User."\n\n";
            exit(1);
        }

        // Try accessing the C module, so we know early if something is wrong
        checkModulePresence(); // raises exception on failure

        if (!file_exists(CONST_ExtraDataPath.'/country_osm_grid.sql.gz')) {
            echo 'Error: you need to download the country_osm_grid first:';
            echo "\n    wget -O ".CONST_ExtraDataPath."/country_osm_grid.sql.gz https://www.nominatim.org/data/country_grid.sql.gz\n";
            exit(1);
        }
        $this->pgsqlRunScriptFile(CONST_BasePath.'/data/country_name.sql');
        $this->pgsqlRunScriptFile(CONST_ExtraDataPath.'/country_osm_grid.sql.gz');
        $this->pgsqlRunScriptFile(CONST_BasePath.'/data/gb_postcode_table.sql');
        $this->pgsqlRunScriptFile(CONST_BasePath.'/data/us_postcode_table.sql');

        $sPostcodeFilename = CONST_BasePath.'/data/gb_postcode_data.sql.gz';
        if (file_exists($sPostcodeFilename)) {
            $this->pgsqlRunScriptFile($sPostcodeFilename);
        } else {
            warn('optional external GB postcode table file ('.$sPostcodeFilename.') not found. Skipping.');
        }

        $sPostcodeFilename = CONST_BasePath.'/data/us_postcode_data.sql.gz';
        if (file_exists($sPostcodeFilename)) {
            $this->pgsqlRunScriptFile($sPostcodeFilename);
        } else {
            warn('optional external US postcode table file ('.$sPostcodeFilename.') not found. Skipping.');
        }

        if ($this->bNoPartitions) {
            $this->pgsqlRunScript('update country_name set partition = 0');
        }
    }

    public function importData($sOSMFile)
    {
        info('Import data');

        if (!file_exists(CONST_Osm2pgsql_Binary)) {
            echo "Check CONST_Osm2pgsql_Binary in your local settings file.\n";
            echo "Normally you should not need to set this manually.\n";
            fail("osm2pgsql not found in '".CONST_Osm2pgsql_Binary."'");
        }

        $oCmd = new \Nominatim\Shell(CONST_Osm2pgsql_Binary);
        $oCmd->addParams('--style', CONST_Import_Style);

        if (!is_null(CONST_Osm2pgsql_Flatnode_File) && CONST_Osm2pgsql_Flatnode_File) {
            $oCmd->addParams('--flat-nodes', CONST_Osm2pgsql_Flatnode_File);
        }
        if (CONST_Tablespace_Osm2pgsql_Data) {
            $oCmd->addParams('--tablespace-slim-data', CONST_Tablespace_Osm2pgsql_Data);
        }
        if (CONST_Tablespace_Osm2pgsql_Index) {
            $oCmd->addParams('--tablespace-slim-index', CONST_Tablespace_Osm2pgsql_Index);
        }
        if (CONST_Tablespace_Place_Data) {
            $oCmd->addParams('--tablespace-main-data', CONST_Tablespace_Place_Data);
        }
        if (CONST_Tablespace_Place_Index) {
            $oCmd->addParams('--tablespace-main-index', CONST_Tablespace_Place_Index);
        }
        $oCmd->addParams('--latlong', '--slim', '--create');
        $oCmd->addParams('--output', 'gazetteer');
        $oCmd->addParams('--hstore');
        $oCmd->addParams('--number-processes', 1);
        $oCmd->addParams('--cache', $this->iCacheMemory);
        $oCmd->addParams('--port', $this->aDSNInfo['port']);

        if (isset($this->aDSNInfo['username'])) {
            $oCmd->addParams('--username', $this->aDSNInfo['username']);
        }
        if (isset($this->aDSNInfo['password'])) {
            $oCmd->addEnvPair('PGPASSWORD', $this->aDSNInfo['password']);
        }
        if (isset($this->aDSNInfo['hostspec'])) {
            $oCmd->addParams('--host', $this->aDSNInfo['hostspec']);
        }
        $oCmd->addParams('--database', $this->aDSNInfo['database']);
        $oCmd->addParams($sOSMFile);
        $oCmd->run();

        if (!$this->sIgnoreErrors && !$this->oDB->getRow('select * from place limit 1')) {
            fail('No Data');
        }

        if ($this->bDrop) {
            $this->dropTable('planet_osm_nodes');
            $this->removeFlatnodeFile();
        }
    }

    public function createFunctions()
    {
        info('Create Functions');

        // Try accessing the C module, so we know early if something is wrong
        checkModulePresence(); // raises exception on failure

        $this->createSqlFunctions();
    }

    public function createTables($bReverseOnly = false)
    {
        info('Create Tables');

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/tables.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);

        if ($bReverseOnly) {
            $this->dropTable('search_name');
        }

        $oAlParser = new AddressLevelParser(CONST_Address_Level_Config);
        $oAlParser->createTable($this->oDB, 'address_levels');
    }

    public function createTableTriggers()
    {
        info('Create Tables');

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/table-triggers.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);
    }

    public function createPartitionTables()
    {
        info('Create Partition Tables');

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/partition-tables.src.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

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
        $sWikiArticlesFile = CONST_Wikipedia_Data_Path.'/wikimedia-importance.sql.gz';
        if (file_exists($sWikiArticlesFile)) {
            info('Importing wikipedia articles and redirects');
            $this->dropTable('wikipedia_article');
            $this->dropTable('wikipedia_redirect');
            $this->pgsqlRunScriptFile($sWikiArticlesFile);
        } else {
            warn('wikipedia importance dump file not found - places will have default importance');
        }
    }

    public function loadData($bDisableTokenPrecalc)
    {
        info('Drop old Data');

        $this->oDB->exec('TRUNCATE word');
        echo '.';
        $this->oDB->exec('TRUNCATE placex');
        echo '.';
        $this->oDB->exec('TRUNCATE location_property_osmline');
        echo '.';
        $this->oDB->exec('TRUNCATE place_addressline');
        echo '.';
        $this->oDB->exec('TRUNCATE location_area');
        echo '.';
        if (!$this->dbReverseOnly()) {
            $this->oDB->exec('TRUNCATE search_name');
            echo '.';
        }
        $this->oDB->exec('TRUNCATE search_name_blank');
        echo '.';
        $this->oDB->exec('DROP SEQUENCE seq_place');
        echo '.';
        $this->oDB->exec('CREATE SEQUENCE seq_place start 100000');
        echo '.';

        $sSQL = 'select distinct partition from country_name';
        $aPartitions = $this->oDB->getCol($sSQL);

        if (!$this->bNoPartitions) $aPartitions[] = 0;
        foreach ($aPartitions as $sPartition) {
            $this->oDB->exec('TRUNCATE location_road_'.$sPartition);
            echo '.';
        }

        // used by getorcreate_word_id to ignore frequent partial words
        $sSQL = 'CREATE OR REPLACE FUNCTION get_maxwordfreq() RETURNS integer AS ';
        $sSQL .= '$$ SELECT '.CONST_Max_Word_Frequency.' as maxwordfreq; $$ LANGUAGE SQL IMMUTABLE';
        $this->oDB->exec($sSQL);
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
            // https://secure.php.net/manual/en/function.pg-connect.php
            $DSN = CONST_Database_DSN;
            $DSN = preg_replace('/^pgsql:/', '', $DSN);
            $DSN = preg_replace('/;/', ' ', $DSN);
            $aDBInstances[$i] = pg_connect($DSN, PGSQL_CONNECT_FORCE_NEW);
            pg_ping($aDBInstances[$i]);
        }

        for ($i = 0; $i < $iLoadThreads; $i++) {
            $sSQL = "INSERT INTO placex ($sColumns) SELECT $sColumns FROM place WHERE osm_id % $iLoadThreads = $i";
            $sSQL .= " and not (class='place' and type='houses' and osm_type='W'";
            $sSQL .= "          and ST_GeometryType(geometry) = 'ST_LineString')";
            $sSQL .= ' and ST_IsValid(geometry)';
            if ($this->bVerbose) echo "$sSQL\n";
            if (!pg_send_query($aDBInstances[$i], $sSQL)) {
                fail(pg_last_error($aDBInstances[$i]));
            }
        }

        // last thread for interpolation lines
        // https://secure.php.net/manual/en/function.pg-connect.php
        $DSN = CONST_Database_DSN;
        $DSN = preg_replace('/^pgsql:/', '', $DSN);
        $DSN = preg_replace('/;/', ' ', $DSN);
        $aDBInstances[$iLoadThreads] = pg_connect($DSN, PGSQL_CONNECT_FORCE_NEW);
        pg_ping($aDBInstances[$iLoadThreads]);
        $sSQL = 'insert into location_property_osmline';
        $sSQL .= ' (osm_id, address, linegeo)';
        $sSQL .= ' SELECT osm_id, address, geometry from place where ';
        $sSQL .= "class='place' and type='houses' and osm_type='W' and ST_GeometryType(geometry) = 'ST_LineString'";
        if ($this->bVerbose) echo "$sSQL\n";
        if (!pg_send_query($aDBInstances[$iLoadThreads], $sSQL)) {
            fail(pg_last_error($aDBInstances[$iLoadThreads]));
        }

        $bFailed = false;
        for ($i = 0; $i <= $iLoadThreads; $i++) {
            while (($hPGresult = pg_get_result($aDBInstances[$i])) !== false) {
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

        for ($i = 0; $i < $this->iInstances; $i++) {
            pg_close($aDBInstances[$i]);
        }

        echo "\n";
        info('Reanalysing database');
        $this->pgsqlRunScript('ANALYSE');

        $sDatabaseDate = getDatabaseDate($this->oDB);
        $this->oDB->exec('TRUNCATE import_status');
        if (!$sDatabaseDate) {
            warn('could not determine database date.');
        } else {
            $sSQL = "INSERT INTO import_status (lastimportdate) VALUES('".$sDatabaseDate."')";
            $this->oDB->exec($sSQL);
            echo "Latest data imported from $sDatabaseDate.\n";
        }
    }

    public function importTigerData()
    {
        info('Import Tiger data');

        $aFilenames = glob(CONST_Tiger_Data_Path.'/*.sql');
        info('Found '.count($aFilenames).' SQL files in path '.CONST_Tiger_Data_Path);
        if (empty($aFilenames)) {
            warn('Tiger data import selected but no files found in path '.CONST_Tiger_Data_Path);
            return;
        }
        $sTemplate = file_get_contents(CONST_BasePath.'/sql/tiger_import_start.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);

        $aDBInstances = array();
        for ($i = 0; $i < $this->iInstances; $i++) {
            // https://secure.php.net/manual/en/function.pg-connect.php
            $DSN = CONST_Database_DSN;
            $DSN = preg_replace('/^pgsql:/', '', $DSN);
            $DSN = preg_replace('/;/', ' ', $DSN);
            $aDBInstances[$i] = pg_connect($DSN, PGSQL_CONNECT_FORCE_NEW | PGSQL_CONNECT_ASYNC);
            pg_ping($aDBInstances[$i]);
        }

        foreach ($aFilenames as $sFile) {
            echo $sFile.': ';
            $hFile = fopen($sFile, 'r');
            $sSQL = fgets($hFile, 100000);
            $iLines = 0;
            while (true) {
                for ($i = 0; $i < $this->iInstances; $i++) {
                    if (!pg_connection_busy($aDBInstances[$i])) {
                        while (pg_get_result($aDBInstances[$i]));
                        $sSQL = fgets($hFile, 100000);
                        if (!$sSQL) break 2;
                        if (!pg_send_query($aDBInstances[$i], $sSQL)) fail(pg_last_error($aDBInstances[$i]));
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
                    if (pg_connection_busy($aDBInstances[$i])) $bAnyBusy = true;
                }
                usleep(10);
            }
            echo "\n";
        }

        for ($i = 0; $i < $this->iInstances; $i++) {
            pg_close($aDBInstances[$i]);
        }

        info('Creating indexes on Tiger data');
        $sTemplate = file_get_contents(CONST_BasePath.'/sql/tiger_import_finish.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);
    }

    public function calculatePostcodes($bCMDResultAll)
    {
        info('Calculate Postcodes');
        $this->oDB->exec('TRUNCATE location_postcode');

        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, country_code,";
        $sSQL .= "       upper(trim (both ' ' from address->'postcode')) as pc,";
        $sSQL .= '       ST_Centroid(ST_Collect(ST_Centroid(geometry)))';
        $sSQL .= '  FROM placex';
        $sSQL .= " WHERE address ? 'postcode' AND address->'postcode' NOT SIMILAR TO '%(,|;)%'";
        $sSQL .= '       AND geometry IS NOT null';
        $sSQL .= ' GROUP BY country_code, pc';
        $this->oDB->exec($sSQL);

        // only add postcodes that are not yet available in OSM
        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, 'us', postcode,";
        $sSQL .= '       ST_SetSRID(ST_Point(x,y),4326)';
        $sSQL .= '  FROM us_postcode WHERE postcode NOT IN';
        $sSQL .= '        (SELECT postcode FROM location_postcode';
        $sSQL .= "          WHERE country_code = 'us')";
        $this->oDB->exec($sSQL);

        // add missing postcodes for GB (if available)
        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, 'gb', postcode, geometry";
        $sSQL .= '  FROM gb_postcode WHERE postcode NOT IN';
        $sSQL .= '           (SELECT postcode FROM location_postcode';
        $sSQL .= "             WHERE country_code = 'gb')";
        $this->oDB->exec($sSQL);

        if (!$bCMDResultAll) {
            $sSQL = "DELETE FROM word WHERE class='place' and type='postcode'";
            $sSQL .= 'and word NOT IN (SELECT postcode FROM location_postcode)';
            $this->oDB->exec($sSQL);
        }

        $sSQL = 'SELECT count(getorcreate_postcode_id(v)) FROM ';
        $sSQL .= '(SELECT distinct(postcode) as v FROM location_postcode) p';
        $this->oDB->exec($sSQL);
    }

    public function index($bIndexNoanalyse)
    {
        $oBaseCmd = (new \Nominatim\Shell(CONST_BasePath.'/nominatim/nominatim.py'))
                    ->addParams('--database', $this->aDSNInfo['database'])
                    ->addParams('--port', $this->aDSNInfo['port'])
                    ->addParams('--threads', $this->iInstances);

        if (!$this->bQuiet) {
            $oBaseCmd->addParams('-v');
        }
        if ($this->bVerbose) {
            $oBaseCmd->addParams('-v');
        }
        if (isset($this->aDSNInfo['hostspec'])) {
            $oBaseCmd->addParams('--host', $this->aDSNInfo['hostspec']);
        }
        if (isset($this->aDSNInfo['username'])) {
            $oBaseCmd->addParams('--user', $this->aDSNInfo['username']);
        }
        if (isset($this->aDSNInfo['password'])) {
            $oBaseCmd->addEnvPair('PGPASSWORD', $this->aDSNInfo['password']);
        }

        info('Index ranks 0 - 4');
        $oCmd = (clone $oBaseCmd)->addParams('--maxrank', 4);
        echo $oCmd->escapedCmd();
        
        $iStatus = $oCmd->run();
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }
        if (!$bIndexNoanalyse) $this->pgsqlRunScript('ANALYSE');

        info('Index ranks 5 - 25');
        $oCmd = (clone $oBaseCmd)->addParams('--minrank', 5, '--maxrank', 25);
        $iStatus = $oCmd->run();
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }
        if (!$bIndexNoanalyse) $this->pgsqlRunScript('ANALYSE');

        info('Index ranks 26 - 30');
        $oCmd = (clone $oBaseCmd)->addParams('--minrank', 26);
        $iStatus = $oCmd->run();
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }

        info('Index postcodes');
        $sSQL = 'UPDATE location_postcode SET indexed_status = 0';
        $this->oDB->exec($sSQL);
    }

    public function createSearchIndices()
    {
        info('Create Search indices');

        $sSQL = 'SELECT relname FROM pg_class, pg_index ';
        $sSQL .= 'WHERE pg_index.indisvalid = false AND pg_index.indexrelid = pg_class.oid';
        $aInvalidIndices = $this->oDB->getCol($sSQL);

        foreach ($aInvalidIndices as $sIndexName) {
            info("Cleaning up invalid index $sIndexName");
            $this->oDB->exec("DROP INDEX $sIndexName;");
        }

        $sTemplate = file_get_contents(CONST_BasePath.'/sql/indices.src.sql');
        if (!$this->bDrop) {
            $sTemplate .= file_get_contents(CONST_BasePath.'/sql/indices_updates.src.sql');
        }
        if (!$this->dbReverseOnly()) {
            $sTemplate .= file_get_contents(CONST_BasePath.'/sql/indices_search.src.sql');
        }
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

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
        $aHaveTables = $this->oDB->getCol("SELECT tablename FROM pg_tables WHERE schemaname='public'");

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
            $this->dropTable($sDrop);
        }

        $this->removeFlatnodeFile();
    }

    private function removeFlatnodeFile()
    {
        if (!is_null(CONST_Osm2pgsql_Flatnode_File) && CONST_Osm2pgsql_Flatnode_File) {
            if (file_exists(CONST_Osm2pgsql_Flatnode_File)) {
                if ($this->bVerbose) echo 'Deleting '.CONST_Osm2pgsql_Flatnode_File."\n";
                unlink(CONST_Osm2pgsql_Flatnode_File);
            }
        }
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
        $sBasePath = CONST_BasePath.'/sql/functions/';
        $sTemplate = file_get_contents($sBasePath.'utils.sql');
        $sTemplate .= file_get_contents($sBasePath.'normalization.sql');
        $sTemplate .= file_get_contents($sBasePath.'ranking.sql');
        $sTemplate .= file_get_contents($sBasePath.'importance.sql');
        $sTemplate .= file_get_contents($sBasePath.'address_lookup.sql');
        $sTemplate .= file_get_contents($sBasePath.'interpolation.sql');
        if ($this->oDB->tableExists('place')) {
            $sTemplate .= file_get_contents($sBasePath.'place_triggers.sql');
        }
        if ($this->oDB->tableExists('placex')) {
            $sTemplate .= file_get_contents($sBasePath.'placex_triggers.sql');
        }
        if ($this->oDB->tableExists('location_postcode')) {
            $sTemplate .= file_get_contents($sBasePath.'postcode_triggers.sql');
        }
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
        $aPartitions = $this->oDB->getCol($sSQL);
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

        $oCmd = (new \Nominatim\Shell('psql'))
                ->addParams('--port', $this->aDSNInfo['port'])
                ->addParams('--dbname', $this->aDSNInfo['database']);

        if (!$this->bVerbose) {
            $oCmd->addParams('--quiet');
        }
        if (isset($this->aDSNInfo['hostspec'])) {
            $oCmd->addParams('--host', $this->aDSNInfo['hostspec']);
        }
        if (isset($this->aDSNInfo['username'])) {
            $oCmd->addParams('--username', $this->aDSNInfo['username']);
        }
        if (isset($this->aDSNInfo['password'])) {
            $oCmd->addEnvPair('PGPASSWORD', $this->aDSNInfo['password']);
        }
        $ahGzipPipes = null;
        if (preg_match('/\\.gz$/', $sFilename)) {
            $aDescriptors = array(
                             0 => array('pipe', 'r'),
                             1 => array('pipe', 'w'),
                             2 => array('file', '/dev/null', 'a')
                            );
            $oZcatCmd = new \Nominatim\Shell('zcat', $sFilename);

            $hGzipProcess = proc_open($oZcatCmd->escapedCmd(), $aDescriptors, $ahGzipPipes);
            if (!is_resource($hGzipProcess)) fail('unable to start zcat');
            $aReadPipe = $ahGzipPipes[1];
            fclose($ahGzipPipes[0]);
        } else {
            $oCmd->addParams('--file', $sFilename);
            $aReadPipe = array('pipe', 'r');
        }
        $aDescriptors = array(
                         0 => $aReadPipe,
                         1 => array('pipe', 'w'),
                         2 => array('file', '/dev/null', 'a')
                        );
        $ahPipes = null;

        $hProcess = proc_open($oCmd->escapedCmd(), $aDescriptors, $ahPipes, null, $oCmd->aEnv);
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

    private function replaceSqlPatterns($sSql)
    {
        $sSql = str_replace('{www-user}', CONST_Database_Web_User, $sSql);

        $aPatterns = array(
                      '{ts:address-data}' => CONST_Tablespace_Address_Data,
                      '{ts:address-index}' => CONST_Tablespace_Address_Index,
                      '{ts:search-data}' => CONST_Tablespace_Search_Data,
                      '{ts:search-index}' =>  CONST_Tablespace_Search_Index,
                      '{ts:aux-data}' =>  CONST_Tablespace_Aux_Data,
                      '{ts:aux-index}' =>  CONST_Tablespace_Aux_Index,
        );

        foreach ($aPatterns as $sPattern => $sTablespace) {
            if ($sTablespace) {
                $sSql = str_replace($sPattern, 'TABLESPACE "'.$sTablespace.'"', $sSql);
            } else {
                $sSql = str_replace($sPattern, '', $sSql);
            }
        }

        return $sSql;
    }

    /**
     * Drop table with the given name if it exists.
     *
     * @param string $sName Name of table to remove.
     *
     * @return null
     *
     * @pre connect() must have been called.
     */
    private function dropTable($sName)
    {
        if ($this->bVerbose) echo "Dropping table $sName\n";
        $this->oDB->exec('DROP TABLE IF EXISTS '.$sName.' CASCADE');
    }

    /**
     * Check if the database is in reverse-only mode.
     *
     * @return True if there is no search_name table and infrastructure.
     */
    private function dbReverseOnly()
    {
        return !($this->oDB->tableExists('search_name'));
    }
}
