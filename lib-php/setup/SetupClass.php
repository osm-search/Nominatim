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

    public function createSqlFunctions()
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
}
