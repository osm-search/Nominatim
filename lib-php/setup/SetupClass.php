<?php

namespace Nominatim\Setup;

require_once(CONST_LibDir.'/Shell.php');

class SetupFunctions
{
    protected $iInstances;
    protected $aDSNInfo;
    protected $bQuiet;
    protected $bVerbose;
    protected $sIgnoreErrors;
    protected $bEnableDiffUpdates;
    protected $bEnableDebugStatements;
    protected $bNoPartitions;
    protected $bDrop;
    protected $oDB = null;
    protected $oNominatimCmd;

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

        $this->oNominatimCmd = new \Nominatim\Shell(getSetting('NOMINATIM_TOOL'));
        if ($this->bQuiet) {
            $this->oNominatimCmd->addParams('--quiet');
        }
        if ($this->bVerbose) {
            $this->oNominatimCmd->addParams('--verbose');
        }
        $this->oNominatimCmd->addParams('--threads', $this->iInstances);
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

        $sTemplate = file_get_contents(CONST_SqlDir.'/tables.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);

        if ($bReverseOnly) {
            $this->dropTable('search_name');
        }

        (clone($this->oNominatimCmd))->addParams('refresh', '--address-levels')->run();
    }

    public function createTableTriggers()
    {
        info('Create Tables');

        $sTemplate = file_get_contents(CONST_SqlDir.'/table-triggers.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);
    }

    public function createPartitionTables()
    {
        info('Create Partition Tables');

        $sTemplate = file_get_contents(CONST_SqlDir.'/partition-tables.src.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunPartitionScript($sTemplate);
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
            $this->pgsqlRunScriptFile(CONST_DataDir.'/words.sql');
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
        $sTemplate = file_get_contents(CONST_SqlDir.'/tiger_import_start.sql');
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
        $sTemplate = file_get_contents(CONST_SqlDir.'/tiger_import_finish.sql');
        $sTemplate = $this->replaceSqlPatterns($sTemplate);

        $this->pgsqlRunScript($sTemplate, false);
    }

    public function calculatePostcodes($bCMDResultAll)
    {
        info('Calculate Postcodes');
        $this->pgsqlRunScriptFile(CONST_SqlDir.'/postcode_tables.sql');

        $sPostcodeFilename = CONST_InstallDir.'/gb_postcode_data.sql.gz';
        if (file_exists($sPostcodeFilename)) {
            $this->pgsqlRunScriptFile($sPostcodeFilename);
        } else {
            warn('optional external GB postcode table file ('.$sPostcodeFilename.') not found. Skipping.');
        }

        $sPostcodeFilename = CONST_InstallDir.'/us_postcode_data.sql.gz';
        if (file_exists($sPostcodeFilename)) {
            $this->pgsqlRunScriptFile($sPostcodeFilename);
        } else {
            warn('optional external US postcode table file ('.$sPostcodeFilename.') not found. Skipping.');
        }


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

        $oBaseCmd = (clone $this->oNominatimCmd)->addParams('index');

        info('Index ranks 0 - 4');
        $oCmd = (clone $oBaseCmd)->addParams('--maxrank', 4);

        $iStatus = $oCmd->run();
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }
        if (!$bIndexNoanalyse) $this->pgsqlRunScript('ANALYSE');

        info('Index administrative boundaries');
        $oCmd = (clone $oBaseCmd)->addParams('--boundaries-only');
        $iStatus = $oCmd->run();
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }

        info('Index ranks 5 - 25');
        $oCmd = (clone $oBaseCmd)->addParams('--no-boundaries', '--minrank', 5, '--maxrank', 25);
        $iStatus = $oCmd->run();
        if ($iStatus != 0) {
            fail('error status ' . $iStatus . ' running nominatim!');
        }

        if (!$bIndexNoanalyse) $this->pgsqlRunScript('ANALYSE');

        info('Index ranks 26 - 30');
        $oCmd = (clone $oBaseCmd)->addParams('--no-boundaries', '--minrank', 26);
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

        $sTemplate = file_get_contents(CONST_SqlDir.'/indices.src.sql');
        if (!$this->bDrop) {
            $sTemplate .= file_get_contents(CONST_SqlDir.'/indices_updates.src.sql');
        }
        if (!$this->dbReverseOnly()) {
            $sTemplate .= file_get_contents(CONST_SqlDir.'/indices_search.src.sql');
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
        $oCmd = (clone($this->oNominatimCmd))
                ->addParams('refresh', '--functions');

        if (!$this->bEnableDiffUpdates) {
            $oCmd->addParams('--no-diff-updates');
        }

        if ($this->bEnableDebugStatements) {
            $oCmd->addParams('--enable-debug-statements');
        }

        $oCmd->run(!$this->sIgnoreErrors);
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
        $sModulePath = getSetting('DATABASE_MODULE_PATH', CONST_InstallDir.'/module');
        $sSQL = "CREATE FUNCTION nominatim_test_import_func(text) RETURNS text AS '";
        $sSQL .= $sModulePath . "/nominatim.so', 'transliteration' LANGUAGE c IMMUTABLE STRICT";
        $sSQL .= ';DROP FUNCTION nominatim_test_import_func(text);';

        $oDB = new \Nominatim\DB();
        $oDB->connect();
        $oDB->exec($sSQL, null, 'Database server failed to load '.$sModulePath.'/nominatim.so module');
    }
}
