<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

require_once(CONST_LibDir.'/Shell.php');

function getCmdOpt($aArg, $aSpec, &$aResult, $bExitOnError = false, $bExitOnUnknown = false)
{
    $aQuick = array();
    $aCounts = array();

    foreach ($aSpec as $aLine) {
        if (is_array($aLine)) {
            if ($aLine[0]) {
                $aQuick['--'.$aLine[0]] = $aLine;
            }
            if ($aLine[1]) {
                $aQuick['-'.$aLine[1]] = $aLine;
            }
            $aCounts[$aLine[0]] = 0;
        }
    }

    $aResult = array();
    $bUnknown = false;
    $iSize = count($aArg);
    for ($i = 1; $i < $iSize; $i++) {
        if (isset($aQuick[$aArg[$i]])) {
            $aLine = $aQuick[$aArg[$i]];
            $aCounts[$aLine[0]]++;
            $xVal = null;
            if ($aLine[4] == $aLine[5]) {
                if ($aLine[4]) {
                    $xVal = array();
                    for ($n = $aLine[4]; $i < $iSize && $n; $n--) {
                        $i++;
                        if ($i >= $iSize || $aArg[$i][0] == '-') {
                            showUsage($aSpec, $bExitOnError, 'Parameter of  \''.$aLine[0].'\' is missing');
                        }

                        switch ($aLine[6]) {
                            case 'realpath':
                                $xVal[] = realpath($aArg[$i]);
                                break;
                            case 'realdir':
                                $sPath = realpath(dirname($aArg[$i]));
                                if ($sPath) {
                                    $xVal[] = $sPath . '/' . basename($aArg[$i]);
                                } else {
                                    $xVal[] = $sPath;
                                }
                                break;
                            case 'bool':
                                $xVal[] = (bool)$aArg[$i];
                                break;
                            case 'int':
                                $xVal[] = (int)$aArg[$i];
                                break;
                            case 'float':
                                $xVal[] = (float)$aArg[$i];
                                break;
                            default:
                                $xVal[] = $aArg[$i];
                                break;
                        }
                    }
                    if ($aLine[4] == 1) {
                        $xVal = $xVal[0];
                    }
                } else {
                    $xVal = true;
                }
            } else {
                fail('Variable numbers of params not yet supported');
            }

            if ($aLine[3] > 1) {
                if (!array_key_exists($aLine[0], $aResult)) {
                    $aResult[$aLine[0]] = array();
                }
                $aResult[$aLine[0]][] = $xVal;
            } else {
                $aResult[$aLine[0]] = $xVal;
            }
        } else {
            $bUnknown = $aArg[$i];
        }
    }

    if (array_key_exists('help', $aResult)) {
        showUsage($aSpec);
    }
    if ($bUnknown && $bExitOnUnknown) {
        showUsage($aSpec, $bExitOnError, 'Unknown option \''.$bUnknown.'\'');
    }

    foreach ($aSpec as $aLine) {
        if (is_array($aLine)) {
            if ($aCounts[$aLine[0]] < $aLine[2]) {
                showUsage($aSpec, $bExitOnError, 'Option \''.$aLine[0].'\' is missing');
            }
            if ($aCounts[$aLine[0]] > $aLine[3]) {
                showUsage($aSpec, $bExitOnError, 'Option \''.$aLine[0].'\' is present too many times');
            }
            if ($aLine[6] == 'bool' && !array_key_exists($aLine[0], $aResult)) {
                $aResult[$aLine[0]] = false;
            }
        }
    }
    return $bUnknown;
}

function showUsage($aSpec, $bExit = false, $sError = false)
{
    if ($sError) {
        echo basename($_SERVER['argv'][0]).': '.$sError."\n";
        echo 'Try `'.basename($_SERVER['argv'][0]).' --help` for more information.'."\n";
        exit;
    }
    echo 'Usage: '.basename($_SERVER['argv'][0])."\n";
    $bFirst = true;
    foreach ($aSpec as $aLine) {
        if (is_array($aLine)) {
            if ($bFirst) {
                $bFirst = false;
                echo "\n";
            }
            $aNames = array();
            if ($aLine[1]) {
                $aNames[] = '-'.$aLine[1];
            }
            if ($aLine[0]) {
                $aNames[] = '--'.$aLine[0];
            }
            $sName = join(', ', $aNames);
            echo '  '.$sName.str_repeat(' ', 30-strlen($sName)).$aLine[7]."\n";
        } else {
            echo $aLine."\n";
        }
    }
    echo "\n";
    exit;
}

function info($sMsg)
{
    echo date('Y-m-d H:i:s == ').$sMsg."\n";
}

$aWarnings = array();


function warn($sMsg)
{
    $GLOBALS['aWarnings'][] = $sMsg;
    echo date('Y-m-d H:i:s == ').'WARNING: '.$sMsg."\n";
}


function repeatWarnings()
{
    foreach ($GLOBALS['aWarnings'] as $sMsg) {
        echo '  * ',$sMsg."\n";
    }
}


function setupHTTPProxy()
{
    if (!getSettingBool('HTTP_PROXY')) {
        return;
    }

    $sProxy = 'tcp://'.getSetting('HTTP_PROXY_HOST').':'.getSetting('HTTP_PROXY_PROT');
    $aHeaders = array();

    $sLogin = getSetting('HTTP_PROXY_LOGIN');
    $sPassword = getSetting('HTTP_PROXY_PASSWORD');

    if ($sLogin && $sPassword) {
        $sAuth = base64_encode($sLogin.':'.$sPassword);
        $aHeaders = array('Proxy-Authorization: Basic '.$sAuth);
    }

    $aProxyHeader = array(
                     'proxy' => $sProxy,
                     'request_fulluri' => true,
                     'header' => $aHeaders
                    );

    $aContext = array('http' => $aProxyHeader, 'https' => $aProxyHeader);
    stream_context_set_default($aContext);
}
