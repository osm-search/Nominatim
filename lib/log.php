<?php


function logStart(&$oDB, $sType = '', $sQuery = '', $aLanguageList = array())
{
    $fStartTime = microtime(true);
    $aStartTime = explode('.', $fStartTime);
    if (!isset($aStartTime[1])) $aStartTime[1] = '0';

    $sOutputFormat = '';
    if (isset($_GET['format'])) $sOutputFormat = $_GET['format'];

    if ($sType == 'reverse') {
        $sOutQuery = (isset($_GET['lat'])?$_GET['lat']:'').'/';
        if (isset($_GET['lon'])) $sOutQuery .= $_GET['lon'];
        if (isset($_GET['zoom'])) $sOutQuery .= '/'.$_GET['zoom'];
    } else {
        $sOutQuery = $sQuery;
    }

    $hLog = array(
             date('Y-m-d H:i:s', $aStartTime[0]).'.'.$aStartTime[1],
             $_SERVER['REMOTE_ADDR'],
             $_SERVER['QUERY_STRING'],
             $sOutQuery,
             $sType,
             $fStartTime
            );

    if (CONST_Log_DB) {
        if (isset($_GET['email']))
            $sUserAgent = $_GET['email'];
        elseif (isset($_SERVER['HTTP_REFERER']))
            $sUserAgent = $_SERVER['HTTP_REFERER'];
        elseif (isset($_SERVER['HTTP_USER_AGENT']))
            $sUserAgent = $_SERVER['HTTP_USER_AGENT'];
        else $sUserAgent = '';
        $sSQL = 'insert into new_query_log (type,starttime,query,ipaddress,useragent,language,format,searchterm)';
        $sSQL .= ' values ('.getDBQuoted($sType).','.getDBQuoted($hLog[0]).','.getDBQuoted($hLog[2]);
        $sSQL .= ','.getDBQuoted($hLog[1]).','.getDBQuoted($sUserAgent).','.getDBQuoted(join(',', $aLanguageList)).','.getDBQuoted($sOutputFormat).','.getDBQuoted($hLog[3]).')';
        $oDB->query($sSQL);
    }

    return $hLog;
}

function logEnd(&$oDB, $hLog, $iNumResults)
{
    $fEndTime = microtime(true);

    if (CONST_Log_DB) {
        $aEndTime = explode('.', $fEndTime);
        if (!$aEndTime[1]) $aEndTime[1] = '0';
        $sEndTime = date('Y-m-d H:i:s', $aEndTime[0]).'.'.$aEndTime[1];

        $sSQL = 'update new_query_log set endtime = '.getDBQuoted($sEndTime).', results = '.$iNumResults;
        $sSQL .= ' where starttime = '.getDBQuoted($hLog[0]);
        $sSQL .= ' and ipaddress = '.getDBQuoted($hLog[1]);
        $sSQL .= ' and query = '.getDBQuoted($hLog[2]);
        $oDB->query($sSQL);
    }

    if (CONST_Log_File) {
        $aOutdata = sprintf(
            "[%s] %.4f %d %s \"%s\"\n",
            $hLog[0],
            $fEndTime-$hLog[5],
            $iNumResults,
            $hLog[4],
            $hLog[2]
        );
        file_put_contents(CONST_Log_File, $aOutdata, FILE_APPEND | LOCK_EX);
    }
}
