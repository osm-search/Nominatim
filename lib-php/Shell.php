<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

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
            if (!isset($this->aEnv)) {
                $this->aEnv = $_ENV;
            }
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

    public function run($bExitOnFail = false)
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

        if ($iStat != 0 && $bExitOnFail) {
            exit($iStat);
        }

        return $iStat;
    }

    private function escapeParam($sParam)
    {
        return (preg_match('/^-*\w+$/', $sParam)) ? $sParam : escapeshellarg($sParam);
    }
}
