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
