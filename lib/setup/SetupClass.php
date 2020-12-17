<?php

namespace Nominatim\Setup;

require_once(CONST_LibDir.'/setup/AddressLevelParser.php');
require_once(CONST_LibDir.'/Shell.php');

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
        } elseif (getSetting('FLATNODE_FILE')) {
            // When flatnode files are enabled then disable cache per default.
            $this->iCacheMemory = 0;
        } else {
            // Otherwise: Assume we can steal all the cache memory in the box.
            $this->iCacheMemory = getCacheMemoryMB();
        }

        $this->sModulePath = getSetting('DATABASE_MODULE_PATH', CONST_InstallDir.'/module');
        info('module path: ' . $this->sModulePath);

        // parse database string
        $this->aDSNInfo = \Nominatim\DB::parseDSN(getSetting('DATABASE_DSN'));
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

        if ($oDB->checkConnection()) {
            fail('database already exists ('.getSetting('DATABASE_DSN').')');
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

    public function setupDB()
    {
        info('Setup DB');

        $fPostgresVersion = $this->db()->getPostgresVersion();
        echo 'Postgres version found: '.$fPostgresVersion."\n";

        if ($fPostgresVersion < 9.03) {
            fail('Minimum supported version of Postgresql is 9.3.');
        }

        $this->pgsqlRunScript('CREATE EXTENSION IF NOT EXISTS hstore');
        $this->pgsqlRunScript('CREATE EXTENSION IF NOT EXISTS postgis');

        $fPostgisVersion = $this->db()->getPostgisVersion();
        echo 'Postgis version found: '.$fPostgisVersion."\n";

        if ($fPostgisVersion < 2.2) {
            echo "Minimum required Postgis version 2.2\n";
            exit(1);
        }

        $sPgUser = getSetting('DATABASE_WEBUSER');
        $i = $this->db()->getOne("select count(*) from pg_user where usename = '$sPgUser'");
        if ($i == 0) {
            echo "\nERROR: Web user '".$sPgUser."' does not exist. Create it with:\n";
            echo "\n          createuser ".$sPgUser."\n\n";
            exit(1);
        }

        // Try accessing the C module, so we know early if something is wrong
        $this->checkModulePresence(); // raises exception on failure

        if (!file_exists(CONST_DataDir.'/data/country_osm_grid.sql.gz')) {
            echo 'Error: you need to download the country_osm_grid first:';
            echo "\n    wget -O ".CONST_DataDir."/data/country_osm_grid.sql.gz https://www.nominatim.org/data/country_grid.sql.gz\n";
            exit(1);
        }
        $this->pgsqlRunScriptFile(CONST_DataDir.'/data/country_name.sql');
        $this->pgsqlRunScriptFile(CONST_DataDir.'/data/country_osm_grid.sql.gz');
        $this->pgsqlRunScriptFile(CONST_DataDir.'/data/gb_postcode_table.sql');
        $this->pgsqlRunScriptFile(CONST_DataDir.'/data/us_postcode_table.sql');

        $sPostcodeFilename = CONST_DataDir.'/data/gb_postcode_data.sql.gz';
        if (file_exists($sPostcodeFilename)) {
            $this->pgsqlRunScriptFile($sPostcodeFilename);
        } else {
            warn('optional external GB postcode table file ('.$sPostcodeFilename.') not found. Skipping.');
        }

        $sPostcodeFilename = CONST_DataDir.'/data/us_postcode_data.sql.gz';
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

        if (!file_exists(getOsm2pgsqlBinary())) {
            echo "Check NOMINATIM_OSM2PGSQL_BINARY in your local .env file.\n";
            echo "Normally you should not need to set this manually.\n";
            fail("osm2pgsql not found in '".getOsm2pgsqlBinary()."'");
        }

        $oCmd = new \Nominatim\Shell(getOsm2pgsqlBinary());
        $oCmd->addParams('--style', getImportStyle());

        if (getSetting('FLATNODE_FILE')) {
            $oCmd->addParams('--flat-nodes', getSetting('FLATNODE_FILE'));
        }
        if (getSetting('TABLESPACE_OSM_DATA')) {
            $oCmd->addParams('--tablespace-slim-data', getSetting('TABLESPACE_OSM_DATA'));
        }
        if (getSetting('TABLESPACE_OSM_INDEX')) {
            $oCmd->addParams('--tablespace-slim-index', getSetting('TABLESPACE_OSM_INDEX'));
        }
        if (getSetting('TABLESPACE_PLACE_DATA')) {
            $oCmd->addParams('--tablespace-main-data', getSetting('TABLESPACE_PLACE_DATA'));
        }
        if (getSetting('TABLESPACE_PLACE_INDEX')) {
            $oCmd->addParams('--tablespace-main-index', getSetting('TABLESPACE_PLACE_INDEX'));
        }
        $oCmd->addParams('--latlong', '--slim', '--create');
        $oCmd->addParams('--output', 'gazetteer');
        $oCmd->addParams('--hstore');
        $oCmd->addParams('--number-processes', 1);
        $oCmd->addParams('--with-forward-dependencies', 'false');
        $oCmd->addParams('--log-progress', 'true');
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

        if (!$this->sIgnoreErrors && !$this->db()->getRow('select * from place limit 1')) {
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
        $this->checkModulePresence(); // raises exception on failure

        $this->createSqlFunctions();
    }

    public function createTables($bReverseOnly = false)
    {
        info('Create Tables');

        $sTemplate = file_get_contents(CONST_DataDir.'/sql/tables.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);

        if ($bReverseOnly) {
            $this->dropTable('search_name');
        }

        $oAlParser = new AddressLevelParser(getSettingConfig('ADDRESS_LEVEL_CONFIG', 'address-levels.json'));
        $oAlParser->createTable($this->db(), 'address_levels');
    }

    public function createTableTriggers()
    {
        info('Create Tables');

        $sTemplate = file_get_contents(CONST_DataDir.'/sql/table-triggers.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);
    }

    public function createPartitionTables()
    {
        info('Create Partition Tables');

        $sTemplate = file_get_contents(CONST_DataDir.'/sql/partition-tables.src.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunPartitionScript($sTemplate);
    }

    public function createPartitionFunctions()
    {
        info('Create Partition Functions');

        $sTemplate = file_get_contents(CONST_DataDir.'/sql/partition-functions.src.sql');
        $this->pgsqlRunPartitionScript($sTemplate);
    }

    public function importWikipediaArticles()
    {
        $sWikiArticlePath = getSetting('WIKIPEDIA_DATA_PATH', CONST_DataDir.'/data');
        $sWikiArticlesFile = $sWikiArticlePath.'/wikimedia-importance.sql.gz';
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

        $oDB = $this->db();

        $oDB->exec('TRUNCATE word');
        echo '.';
        $oDB->exec('TRUNCATE placex');
        echo '.';
        $oDB->exec('TRUNCATE location_property_osmline');
        echo '.';
        $oDB->exec('TRUNCATE place_addressline');
        echo '.';
        $oDB->exec('TRUNCATE location_area');
        echo '.';
        if (!$this->dbReverseOnly()) {
            $oDB->exec('TRUNCATE search_name');
            echo '.';
        }
        $oDB->exec('TRUNCATE search_name_blank');
        echo '.';
        $oDB->exec('DROP SEQUENCE seq_place');
        echo '.';
        $oDB->exec('CREATE SEQUENCE seq_place start 100000');
        echo '.';

        $sSQL = 'select distinct partition from country_name';
        $aPartitions = $oDB->getCol($sSQL);

        if (!$this->bNoPartitions) $aPartitions[] = 0;
        foreach ($aPartitions as $sPartition) {
            $oDB->exec('TRUNCATE location_road_'.$sPartition);
            echo '.';
        }

        // used by getorcreate_word_id to ignore frequent partial words
        $sSQL = 'CREATE OR REPLACE FUNCTION get_maxwordfreq() RETURNS integer AS ';
        $sSQL .= '$$ SELECT '.getSetting('MAX_WORD_FREQUENCY').' as maxwordfreq; $$ LANGUAGE SQL IMMUTABLE';
        $oDB->exec($sSQL);
        echo ".\n";

        // pre-create the word list
        if (!$bDisableTokenPrecalc) {
            info('Loading word list');
            $this->pgsqlRunScriptFile(CONST_DataDir.'/data/words.sql');
        }

        info('Load Data');
        $sColumns = 'osm_type, osm_id, class, type, name, admin_level, address, extratags, geometry';

        $aDBInstances = array();
        $iLoadThreads = max(1, $this->iInstances - 1);
        for ($i = 0; $i < $iLoadThreads; $i++) {
            // https://secure.php.net/manual/en/function.pg-connect.php
            $DSN = getSetting('DATABASE_DSN');
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
        $DSN = getSetting('DATABASE_DSN');
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

        $sDatabaseDate = getDatabaseDate($oDB);
        $oDB->exec('TRUNCATE import_status');
        if (!$sDatabaseDate) {
            warn('could not determine database date.');
        } else {
            $sSQL = "INSERT INTO import_status (lastimportdate) VALUES('".$sDatabaseDate."')";
            $oDB->exec($sSQL);
            echo "Latest data imported from $sDatabaseDate.\n";
        }
    }

    public function importTigerData($sTigerPath)
    {
        info('Import Tiger data');

        $aFilenames = glob($sTigerPath.'/*.sql');
        info('Found '.count($aFilenames).' SQL files in path '.$sTigerPath);
        if (empty($aFilenames)) {
            warn('Tiger data import selected but no files found in path '.$sTigerPath);
            return;
        }
        $sTemplate = file_get_contents(CONST_DataDir.'/sql/tiger_import_start.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);

        $aDBInstances = array();
        for ($i = 0; $i < $this->iInstances; $i++) {
            // https://secure.php.net/manual/en/function.pg-connect.php
            $DSN = getSetting('DATABASE_DSN');
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
        $sTemplate = file_get_contents(CONST_DataDir.'/sql/tiger_import_finish.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);
    }

    public function calculatePostcodes($bCMDResultAll)
    {
        info('Calculate Postcodes');
        $this->db()->exec('TRUNCATE location_postcode');

        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, country_code,";
        $sSQL .= "       upper(trim (both ' ' from address->'postcode')) as pc,";
        $sSQL .= '       ST_Centroid(ST_Collect(ST_Centroid(geometry)))';
        $sSQL .= '  FROM placex';
        $sSQL .= " WHERE address ? 'postcode' AND address->'postcode' NOT SIMILAR TO '%(,|;)%'";
        $sSQL .= '       AND geometry IS NOT null';
        $sSQL .= ' GROUP BY country_code, pc';
        $this->db()->exec($sSQL);

        // only add postcodes that are not yet available in OSM
        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, 'us', postcode,";
        $sSQL .= '       ST_SetSRID(ST_Point(x,y),4326)';
        $sSQL .= '  FROM us_postcode WHERE postcode NOT IN';
        $sSQL .= '        (SELECT postcode FROM location_postcode';
        $sSQL .= "          WHERE country_code = 'us')";
        $this->db()->exec($sSQL);

        // add missing postcodes for GB (if available)
        $sSQL  = 'INSERT INTO location_postcode';
        $sSQL .= ' (place_id, indexed_status, country_code, postcode, geometry) ';
        $sSQL .= "SELECT nextval('seq_place'), 1, 'gb', postcode, geometry";
        $sSQL .= '  FROM gb_postcode WHERE postcode NOT IN';
        $sSQL .= '           (SELECT postcode FROM location_postcode';
        $sSQL .= "             WHERE country_code = 'gb')";
        $this->db()->exec($sSQL);

        if (!$bCMDResultAll) {
            $sSQL = "DELETE FROM word WHERE class='place' and type='postcode'";
            $sSQL .= 'and word NOT IN (SELECT postcode FROM location_postcode)';
            $this->db()->exec($sSQL);
        }

        $sSQL = 'SELECT count(getorcreate_postcode_id(v)) FROM ';
        $sSQL .= '(SELECT distinct(postcode) as v FROM location_postcode) p';
        $this->db()->exec($sSQL);
    }

    public function index($bIndexNoanalyse)
    {
        $this->checkModulePresence(); // raises exception on failure

        $oBaseCmd = (new \Nominatim\Shell(CONST_DataDir.'/nominatim/nominatim.py'))
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

        info('Index administrative boundaries');
        $oCmd = (clone $oBaseCmd)->addParams('-b');
        $iStatus = $oCmd->run();
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }

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
        $this->db()->exec($sSQL);
    }

    public function createSearchIndices()
    {
        info('Create Search indices');

        $sSQL = 'SELECT relname FROM pg_class, pg_index ';
        $sSQL .= 'WHERE pg_index.indisvalid = false AND pg_index.indexrelid = pg_class.oid';
        $aInvalidIndices = $this->db()->getCol($sSQL);

        foreach ($aInvalidIndices as $sIndexName) {
            info("Cleaning up invalid index $sIndexName");
            $this->db()->exec("DROP INDEX $sIndexName;");
        }

        $sTemplate = file_get_contents(CONST_DataDir.'/sql/indices.src.sql');
        if (!$this->bDrop) {
            $sTemplate .= file_get_contents(CONST_DataDir.'/sql/indices_updates.src.sql');
        }
        if (!$this->dbReverseOnly()) {
            $sTemplate .= file_get_contents(CONST_DataDir.'/sql/indices_search.src.sql');
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
        $sLanguages = getSetting('LANGUAGES');
        if ($sLanguages) {
            $sSQL .= 'in ';
            $sDelim = '(';
            foreach (explode(',', $sLanguages) as $sLang) {
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
        $aHaveTables = $this->db()->getListOfTables();

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

    /**
     * Setup the directory for the API scripts.
     *
     * @return null
     */
    public function setupWebsite()
    {
        if (!is_dir(CONST_InstallDir.'/website')) {
            info('Creating directory for website scripts at: '.CONST_InstallDir.'/website');
            mkdir(CONST_InstallDir.'/website');
        }

        $aScripts = array(
          'deletable.php',
          'details.php',
          'lookup.php',
          'polygons.php',
          'reverse.php',
          'search.php',
          'status.php'
        );

        foreach ($aScripts as $sScript) {
            $rFile = fopen(CONST_InstallDir.'/website/'.$sScript, 'w');

            fwrite($rFile, "<?php\n\n");
            fwrite($rFile, '@define(\'CONST_Debug\', $_GET[\'debug\'] ?? false);'."\n\n");

            fwriteConstDef($rFile, 'LibDir', CONST_LibDir);
            fwriteConstDef($rFile, 'DataDir', CONST_DataDir);
            fwriteConstDef($rFile, 'InstallDir', CONST_InstallDir);

            fwrite($rFile, "if (file_exists(getenv('NOMINATIM_SETTINGS'))) require_once(getenv('NOMINATIM_SETTINGS'));\n\n");

            fwriteConstDef($rFile, 'Database_DSN', getSetting('DATABASE_DSN'));
            fwriteConstDef($rFile, 'Default_Language', getSetting('DEFAULT_LANGUAGE'));
            fwriteConstDef($rFile, 'Log_DB', getSettingBool('LOG_DB'));
            fwriteConstDef($rFile, 'Log_File', getSetting('LOG_FILE'));
            fwriteConstDef($rFile, 'Max_Word_Frequency', (int)getSetting('MAX_WORD_FREQUENCY'));
            fwriteConstDef($rFile, 'NoAccessControl', getSettingBool('CORS_NOACCESSCONTROL'));
            fwriteConstDef($rFile, 'Places_Max_ID_count', (int)getSetting('LOOKUP_MAX_COUNT'));
            fwriteConstDef($rFile, 'PolygonOutput_MaximumTypes', getSetting('POLYGON_OUTPUT_MAX_TYPES'));
            fwriteConstDef($rFile, 'Search_BatchMode', getSettingBool('SEARCH_BATCH_MODE'));
            fwriteConstDef($rFile, 'Search_NameOnlySearchFrequencyThreshold', getSetting('SEARCH_NAME_ONLY_THRESHOLD'));
            fwriteConstDef($rFile, 'Term_Normalization_Rules', getSetting('TERM_NORMALIZATION'));
            fwriteConstDef($rFile, 'Use_Aux_Location_data', getSettingBool('USE_AUX_LOCATION_DATA'));
            fwriteConstDef($rFile, 'Use_US_Tiger_Data', getSettingBool('USE_US_TIGER_DATA'));
            fwriteConstDef($rFile, 'MapIcon_URL', getSetting('MAPICON_URL'));

            // XXX scripts should go into the library.
            fwrite($rFile, 'require_once(\''.CONST_DataDir.'/website/'.$sScript."');\n");
            fclose($rFile);

            chmod(CONST_InstallDir.'/website/'.$sScript, 0755);
        }
    }

    /**
     * Return the connection to the database.
     *
     * @return Database object.
     *
     * Creates a new connection if none exists yet. Otherwise reuses the
     * already established connection.
     */
    private function db()
    {
        if (is_null($this->oDB)) {
            $this->oDB = new \Nominatim\DB();
            $this->oDB->connect();
        }

        return $this->oDB;
    }

    private function removeFlatnodeFile()
    {
        $sFName = getSetting('FLATNODE_FILE');
        if ($sFName && file_exists($sFName)) {
            if ($this->bVerbose) echo 'Deleting '.$sFName."\n";
            unlink($sFName);
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
        $sBasePath = CONST_DataDir.'/sql/functions/';
        $sTemplate = file_get_contents($sBasePath.'utils.sql');
        $sTemplate .= file_get_contents($sBasePath.'normalization.sql');
        $sTemplate .= file_get_contents($sBasePath.'ranking.sql');
        $sTemplate .= file_get_contents($sBasePath.'importance.sql');
        $sTemplate .= file_get_contents($sBasePath.'address_lookup.sql');
        $sTemplate .= file_get_contents($sBasePath.'interpolation.sql');
        if ($this->db()->tableExists('place')) {
            $sTemplate .= file_get_contents($sBasePath.'place_triggers.sql');
        }
        if ($this->db()->tableExists('placex')) {
            $sTemplate .= file_get_contents($sBasePath.'placex_triggers.sql');
        }
        if ($this->db()->tableExists('location_postcode')) {
            $sTemplate .= file_get_contents($sBasePath.'postcode_triggers.sql');
        }
        $sTemplate = str_replace('{modulepath}', $this->sModulePath, $sTemplate);
        if ($this->bEnableDiffUpdates) {
            $sTemplate = str_replace('RETURN NEW; -- %DIFFUPDATES%', '--', $sTemplate);
        }
        if ($this->bEnableDebugStatements) {
            $sTemplate = str_replace('--DEBUG:', '', $sTemplate);
        }
        if (getSettingBool('LIMIT_REINDEXING')) {
            $sTemplate = str_replace('--LIMIT INDEXING:', '', $sTemplate);
        }
        if (!getSettingBool('USE_US_TIGER_DATA')) {
            $sTemplate = str_replace('-- %NOTIGERDATA% ', '', $sTemplate);
        }
        if (!getSettingBool('USE_AUX_LOCATION_DATA')) {
            $sTemplate = str_replace('-- %NOAUXDATA% ', '', $sTemplate);
        }

        $sReverseOnly = $this->dbReverseOnly() ? 'true' : 'false';
        $sTemplate = str_replace('%REVERSE-ONLY%', $sReverseOnly, $sTemplate);

        $this->pgsqlRunScript($sTemplate);
    }

    private function pgsqlRunPartitionScript($sTemplate)
    {
        $sSQL = 'select distinct partition from country_name';
        $aPartitions = $this->db()->getCol($sSQL);
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
        $sSql = str_replace('{www-user}', getSetting('DATABASE_WEBUSER'), $sSql);

        $aPatterns = array(
                      '{ts:address-data}' => getSetting('TABLESPACE_ADDRESS_DATA'),
                      '{ts:address-index}' => getSetting('TABLESPACE_ADDRESS_INDEX'),
                      '{ts:search-data}' => getSetting('TABLESPACE_SEARCH_DATA'),
                      '{ts:search-index}' =>  getSetting('TABLESPACE_SEARCH_INDEX'),
                      '{ts:aux-data}' =>  getSetting('TABLESPACE_AUX_DATA'),
                      '{ts:aux-index}' =>  getSetting('TABLESPACE_AUX_INDEX')
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
     */
    private function dropTable($sName)
    {
        if ($this->bVerbose) echo "Dropping table $sName\n";
        $this->db()->deleteTable($sName);
    }

    /**
     * Check if the database is in reverse-only mode.
     *
     * @return True if there is no search_name table and infrastructure.
     */
    private function dbReverseOnly()
    {
        return !($this->db()->tableExists('search_name'));
    }

    /**
     * Try accessing the C module, so we know early if something is wrong.
     *
     * Raises Nominatim\DatabaseError on failure
     */
    private function checkModulePresence()
    {
        $sSQL = "CREATE FUNCTION nominatim_test_import_func(text) RETURNS text AS '";
        $sSQL .= $this->sModulePath . "/nominatim.so', 'transliteration' LANGUAGE c IMMUTABLE STRICT";
        $sSQL .= ';DROP FUNCTION nominatim_test_import_func(text);';

        $oDB = new \Nominatim\DB();
        $oDB->connect();
        $oDB->exec($sSQL, null, 'Database server failed to load '.$this->sModulePath.'/nominatim.so module');
    }
}
