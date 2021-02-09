<?php

namespace Nominatim;

class Shell
{
    public function __construct($sBaseCmd, ...$aParams)
    {
        if (!$sBaseCmd) {
            throw new \Exception('Command missing in new() call');
        }
        $this->baseCmd = $sBaseCmd;
        $this->aParams = array();
        $this->aEnv = null; // null = use the same environment as the current PHP process

        $this->stdoutString = null;

        foreach ($aParams as $sParam) {
            $this->addParams($sParam);
        }
    }

    public function addParams(...$aParams)
    {
        foreach ($aParams as $sParam) {
            if (isset($sParam) && $sParam !== null && $sParam !== '') {
                array_push($this->aParams, $sParam);
            }
        }
        return $this;
    }

    public function addEnvPair($sKey, $sVal)
    {
        if (isset($sKey) && $sKey && isset($sVal)) {
            if (!isset($this->aEnv)) $this->aEnv = $_ENV;
            $this->aEnv = array_merge($this->aEnv, array($sKey => $sVal), $_ENV);
        }
        return $this;
    }

    public function escapedCmd()
    {
        $aEscaped = array_map(function ($sParam) {
            return $this->escapeParam($sParam);
        }, array_merge(array($this->baseCmd), $this->aParams));

        return join(' ', $aEscaped);
    }

    public function run()
    {
        $sCmd = $this->escapedCmd();
        // $aEnv does not need escaping, proc_open seems to handle it fine

        $aFDs = array(
                 0 => array('pipe', 'r'),
                 1 => STDOUT,
                 2 => STDERR
                );
        $aPipes = null;
        $hProc = @proc_open($sCmd, $aFDs, $aPipes, null, $this->aEnv);
        if (!is_resource($hProc)) {
            throw new \Exception('Unable to run command: ' . $sCmd);
        }

        fclose($aPipes[0]); // no stdin

        $iStat = proc_close($hProc);
        return $iStat;
    }



    private function escapeParam($sParam)
    {
        if (preg_match('/^-*\w+$/', $sParam)) return $sParam;
        return escapeshellarg($sParam);
    }
}
