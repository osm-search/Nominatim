<?php

function fail($sError, $sUserError = false)
{
    if (!$sUserError) $sUserError = $sError;
    error_log('ERROR: '.$sError);
    echo $sUserError."\n";
    exit(-1);
}


function getProcessorCount()
{
    $sCPU = file_get_contents('/proc/cpuinfo');
    preg_match_all('#processor\s+: [0-9]+#', $sCPU, $aMatches);
    return count($aMatches[0]);
}


function getTotalMemoryMB()
{
    $sCPU = file_get_contents('/proc/meminfo');
    preg_match('#MemTotal: +([0-9]+) kB#', $sCPU, $aMatches);
    return (int)($aMatches[1]/1024);
}


function getCacheMemoryMB()
{
    $sCPU = file_get_contents('/proc/meminfo');
    preg_match('#Cached: +([0-9]+) kB#', $sCPU, $aMatches);
    return (int)($aMatches[1]/1024);
}

function getDatabaseDate(&$oDB)
{
    // Find the newest node in the DB
    $iLastOSMID = $oDB->getOne("select max(osm_id) from place where osm_type = 'N'");
    // Lookup the timestamp that node was created
    $sLastNodeURL = 'https://www.openstreetmap.org/api/0.6/node/'.$iLastOSMID.'/1';
    $sLastNodeXML = file_get_contents($sLastNodeURL);

    if ($sLastNodeXML === false) {
        return false;
    }

    preg_match('#timestamp="(([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z)"#', $sLastNodeXML, $aLastNodeDate);

    return $aLastNodeDate[1];
}


function byImportance($a, $b)
{
    if ($a['importance'] != $b['importance'])
        return ($a['importance'] > $b['importance']?-1:1);

    return ($a['foundorder'] < $b['foundorder']?-1:1);
}


function javascript_renderData($xVal, $iOptions = 0)
{
    $sCallback = isset($_GET['json_callback']) ? $_GET['json_callback'] : '';
    if ($sCallback && !preg_match('/^[$_\p{L}][$_\p{L}\p{Nd}.[\]]*$/u', $sCallback)) {
        // Unset, we call javascript_renderData again during exception handling
        unset($_GET['json_callback']);
        throw new Exception('Invalid json_callback value', 400);
    }

    $iOptions |= JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES;
    if (isset($_GET['pretty']) && in_array(strtolower($_GET['pretty']), array('1', 'true'))) {
        $iOptions |= JSON_PRETTY_PRINT;
    }

    $jsonout = json_encode($xVal, $iOptions);

    if ($sCallback) {
        header('Content-Type: application/javascript; charset=UTF-8');
        echo $_GET['json_callback'].'('.$jsonout.')';
    } else {
        header('Content-Type: application/json; charset=UTF-8');
        echo $jsonout;
    }
}

function addQuotes($s)
{
    return "'".$s."'";
}

function parseLatLon($sQuery)
{
    $sFound    = null;
    $fQueryLat = null;
    $fQueryLon = null;

    if (preg_match('/\\s*([NS])[ ]+([0-9]+[0-9.]*)[° ]+([0-9.]+)?[′\']*[, ]+([EW])[ ]+([0-9]+)[° ]+([0-9]+[0-9.]*)[′\']*\\s*/', $sQuery, $aData)) {
        /*               1         2                   3                    4         5            6
         * degrees decimal minutes
         * N 40 26.767, W 79 58.933
         * N 40°26.767′, W 79°58.933′
         */
        $sFound    = $aData[0];
        $fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2] + $aData[3]/60);
        $fQueryLon = ($aData[4]=='E'?1:-1) * ($aData[5] + $aData[6]/60);
    } elseif (preg_match('/\\s*([0-9]+)[° ]+([0-9]+[0-9.]*)?[′\']*[ ]+([NS])[, ]+([0-9]+)[° ]+([0-9]+[0-9.]*)?[′\' ]+([EW])\\s*/', $sQuery, $aData)) {
        /*                     1            2                         3          4            5                      6
         * degrees decimal minutes
         * 40 26.767 N, 79 58.933 W
         * 40° 26.767′ N 79° 58.933′ W
         */
        $sFound    = $aData[0];
        $fQueryLat = ($aData[3]=='N'?1:-1) * ($aData[1] + $aData[2]/60);
        $fQueryLon = ($aData[6]=='E'?1:-1) * ($aData[4] + $aData[5]/60);
    } elseif (preg_match('/\\s*([NS])[ ]([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″"]*[, ]+([EW])[ ]([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″"]*\\s*/', $sQuery, $aData)) {
        /*                     1        2            3              4                 5        6            7              8
         * degrees decimal seconds
         * N 40 26 46 W 79 58 56
         * N 40° 26′ 46″, W 79° 58′ 56″
         */
        $sFound    = $aData[0];
        $fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2] + $aData[3]/60 + $aData[4]/3600);
        $fQueryLon = ($aData[5]=='E'?1:-1) * ($aData[6] + $aData[7]/60 + $aData[8]/3600);
    } elseif (preg_match('/\\s*([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+[0-9.]*)[″" ]+([NS])[, ]+([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+[0-9.]*)[″" ]+([EW])\\s*/', $sQuery, $aData)) {
        /*                     1            2              3                    4          5            6              7                     8
         * degrees decimal seconds
         * 40 26 46 N 79 58 56 W
         * 40° 26′ 46″ N, 79° 58′ 56″ W
         * 40° 26′ 46.78″ N, 79° 58′ 56.89″ W
         */
        $sFound    = $aData[0];
        $fQueryLat = ($aData[4]=='N'?1:-1) * ($aData[1] + $aData[2]/60 + $aData[3]/3600);
        $fQueryLon = ($aData[8]=='E'?1:-1) * ($aData[5] + $aData[6]/60 + $aData[7]/3600);
    } elseif (preg_match('/\\s*([NS])[ ]([0-9]+[0-9]*\\.[0-9]+)[°]*[, ]+([EW])[ ]([0-9]+[0-9]*\\.[0-9]+)[°]*\\s*/', $sQuery, $aData)) {
        /*                     1        2                               3        4
         * degrees decimal
         * N 40.446° W 79.982°
         */
        $sFound    = $aData[0];
        $fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2]);
        $fQueryLon = ($aData[3]=='E'?1:-1) * ($aData[4]);
    } elseif (preg_match('/\\s*([0-9]+[0-9]*\\.[0-9]+)[° ]+([NS])[, ]+([0-9]+[0-9]*\\.[0-9]+)[° ]+([EW])\\s*/', $sQuery, $aData)) {
        /*                     1                           2          3                           4
         * degrees decimal
         * 40.446° N 79.982° W
         */
        $sFound    = $aData[0];
        $fQueryLat = ($aData[2]=='N'?1:-1) * ($aData[1]);
        $fQueryLon = ($aData[4]=='E'?1:-1) * ($aData[3]);
    } elseif (preg_match('/(\\s*\\[|^\\s*|\\s*)(-?[0-9]+[0-9]*\\.[0-9]+)[, ]+(-?[0-9]+[0-9]*\\.[0-9]+)(\\]\\s*|\\s*$|\\s*)/', $sQuery, $aData)) {
        /*                 1                   2                             3                        4
         * degrees decimal
         * 12.34, 56.78
         * 12.34 56.78
         * [12.456,-78.90]
         */
        $sFound    = $aData[0];
        $fQueryLat = $aData[2];
        $fQueryLon = $aData[3];
    } else {
        return false;
    }

    return array($sFound, $fQueryLat, $fQueryLon);
}


function geometryText2Points($geometry_as_text, $fRadius)
{
    $aPolyPoints = null;
    if (preg_match('#POLYGON\\(\\(([- 0-9.,]+)#', $geometry_as_text, $aMatch)) {
        //
        preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/', $aMatch[1], $aPolyPoints, PREG_SET_ORDER);
        //
    } elseif (preg_match('#LINESTRING\\(([- 0-9.,]+)#', $geometry_as_text, $aMatch)) {
        //
        preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/', $aMatch[1], $aPolyPoints, PREG_SET_ORDER);
        //
    } elseif (preg_match('#MULTIPOLYGON\\(\\(\\(([- 0-9.,]+)#', $geometry_as_text, $aMatch)) {
        //
        preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/', $aMatch[1], $aPolyPoints, PREG_SET_ORDER);
        //
    } elseif (preg_match('#POINT\\((-?[0-9.]+) (-?[0-9.]+)\\)#', $geometry_as_text, $aMatch)) {
        //
        $aPolyPoints = createPointsAroundCenter($aMatch[1], $aMatch[2], $fRadius);
        //
    }

    if (isset($aPolyPoints)) {
        $aResultPoints = array();
        foreach ($aPolyPoints as $aPoint) {
            $aResultPoints[] = array($aPoint[1], $aPoint[2]);
        }
        return $aResultPoints;
    }

    return;
}

function createPointsAroundCenter($fLon, $fLat, $fRadius)
{
    $iSteps = max(8, min(100, ($fRadius * 40000)^2));
    $fStepSize = (2*pi())/$iSteps;
    $aPolyPoints = array();
    for ($f = 0; $f < 2*pi(); $f += $fStepSize) {
        $aPolyPoints[] = array('', $fLon+($fRadius*sin($f)), $fLat+($fRadius*cos($f)) );
    }
    return $aPolyPoints;
}

function closestHouseNumber($aRow)
{
    $fHouse = $aRow['startnumber']
                + ($aRow['endnumber'] - $aRow['startnumber']) * $aRow['fraction'];

    switch ($aRow['interpolationtype']) {
        case 'odd':
            $iHn = (int)($fHouse/2) * 2 + 1;
            break;
        case 'even':
            $iHn = (int)(round($fHouse/2)) * 2;
            break;
        default:
            $iHn = (int)(round($fHouse));
            break;
    }

    return max(min($aRow['endnumber'], $iHn), $aRow['startnumber']);
}
