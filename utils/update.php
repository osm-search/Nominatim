#!/usr/bin/php -Cq
<?php

require_once(dirname(dirname(__FILE__)).'/settings/settings.php');
require_once(CONST_BasePath.'/lib/init-cmd.php');
ini_set('memory_limit', '800M');

$aCMDOptions
= array(
   "Import / update / index osm data",
   array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
   array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
   array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

   array('import-osmosis', '', 0, 1, 0, 0, 'bool', 'Import using osmosis'),
   array('import-osmosis-all', '', 0, 1, 0, 0, 'bool', 'Import using osmosis forever'),
   array('no-npi', '', 0, 1, 0, 0, 'bool', '(obsolate)'),
   array('no-index', '', 0, 1, 0, 0, 'bool', 'Do not index the new data'),

   array('import-all', '', 0, 1, 0, 0, 'bool', 'Import all available files'),

   array('import-file', '', 0, 1, 1, 1, 'realpath', 'Re-import data from an OSM file'),
   array('import-diff', '', 0, 1, 1, 1, 'realpath', 'Import a diff (osc) file from local file system'),
   array('osm2pgsql-cache', '', 0, 1, 1, 1, 'int', 'Cache size used by osm2pgsql'),

   array('import-node', '', 0, 1, 1, 1, 'int', 'Re-import node'),
   array('import-way', '', 0, 1, 1, 1, 'int', 'Re-import way'),
   array('import-relation', '', 0, 1, 1, 1, 'int', 'Re-import relation'),
   array('import-from-main-api', '', 0, 1, 0, 0, 'bool', 'Use OSM API instead of Overpass to download objects'),

   array('index', '', 0, 1, 0, 0, 'bool', 'Index'),
   array('index-rank', '', 0, 1, 1, 1, 'int', 'Rank to start indexing from'),
   array('index-instances', '', 0, 1, 1, 1, 'int', 'Number of indexing instances (threads)'),

   array('deduplicate', '', 0, 1, 0, 0, 'bool', 'Deduplicate tokens'),
  );
getCmdOpt($_SERVER['argv'], $aCMDOptions, $aResult, true, true);

if (!isset($aResult['index-instances'])) $aResult['index-instances'] = 1;
if (!isset($aResult['index-rank'])) $aResult['index-rank'] = 0;

date_default_timezone_set('Etc/UTC');

$oDB =& getDB();

$aDSNInfo = DB::parseDSN(CONST_Database_DSN);
if (!isset($aDSNInfo['port']) || !$aDSNInfo['port']) $aDSNInfo['port'] = 5432;

// cache memory to be used by osm2pgsql, should not be more than the available memory
$iCacheMemory = (isset($aResult['osm2pgsql-cache'])?$aResult['osm2pgsql-cache']:2000);
if ($iCacheMemory + 500 > getTotalMemoryMB()) {
    $iCacheMemory = getCacheMemoryMB();
    echo "WARNING: resetting cache memory to $iCacheMemory\n";
}
$sOsm2pgsqlCmd = CONST_Osm2pgsql_Binary.' -klas --number-processes 1 -C '.$iCacheMemory.' -O gazetteer -d '.$aDSNInfo['database'].' -P '.$aDSNInfo['port'];
if (!is_null(CONST_Osm2pgsql_Flatnode_File)) {
    $sOsm2pgsqlCmd .= ' --flat-nodes '.CONST_Osm2pgsql_Flatnode_File;
}


if (isset($aResult['import-diff'])) {
    // import diff directly (e.g. from osmosis --rri)
    $sNextFile = $aResult['import-diff'];
    if (!file_exists($sNextFile)) {
        fail("Cannot open $sNextFile\n");
    }

    // Import the file
    $sCMD = $sOsm2pgsqlCmd.' '.$sNextFile;
    echo $sCMD."\n";
    exec($sCMD, $sJunk, $iErrorLevel);

    if ($iErrorLevel) {
        fail("Error from osm2pgsql, $iErrorLevel\n");
    }

    // Don't update the import status - we don't know what this file contains
}

$sTemporaryFile = CONST_BasePath.'/data/osmosischange.osc';
$bHaveDiff = false;
if (isset($aResult['import-file']) && $aResult['import-file']) {
    $bHaveDiff = true;
    $sCMD = CONST_Osmosis_Binary.' --read-xml \''.$aResult['import-file'].'\' --read-empty --derive-change --write-xml-change '.$sTemporaryFile;
    echo $sCMD."\n";
    exec($sCMD, $sJunk, $iErrorLevel);
    if ($iErrorLevel) {
        fail("Error converting osm to osc, osmosis returned: $iErrorLevel\n");
    }
}

$bUseOSMApi = isset($aResult['import-from-main-api']) && $aResult['import-from-main-api'];
$sContentURL = '';
if (isset($aResult['import-node']) && $aResult['import-node']) {
    if ($bUseOSMApi) {
        $sContentURL = 'http://www.openstreetmap.org/api/0.6/node/'.$aResult['import-node'];
    } else {
        $sContentURL = 'http://overpass-api.de/api/interpreter?data=node('.$aResult['import-node'].');out%20meta;';
    }
}

if (isset($aResult['import-way']) && $aResult['import-way']) {
    if ($bUseOSMApi) {
        $sContentURL = 'http://www.openstreetmap.org/api/0.6/way/'.$aResult['import-way'].'/full';
    } else {
        $sContentURL = 'http://overpass-api.de/api/interpreter?data=(way('.$aResult['import-way'].');node(w););out%20meta;';
    }
}

if (isset($aResult['import-relation']) && $aResult['import-relation']) {
    if ($bUseOSMApi) {
        $sContentURLsModifyXMLstr = 'http://www.openstreetmap.org/api/0.6/relation/'.$aResult['import-relation'].'/full';
    } else {
        $sContentURL = 'http://overpass-api.de/api/interpreter?data=((rel('.$aResult['import-relation'].');way(r);node(w));node(r));out%20meta;';
    }
}

if ($sContentURL) {
    $sModifyXMLstr = file_get_contents($sContentURL);
    $bHaveDiff = true;

    $aSpec = array(
              0 => array("pipe", "r"),  // stdin
              1 => array("pipe", "w"),  // stdout
              2 => array("pipe", "w") // stderr
             );
    $sCMD = CONST_Osmosis_Binary.' --read-xml - --read-empty --derive-change --write-xml-change '.$sTemporaryFile;
    echo $sCMD."\n";
    $hProc = proc_open($sCMD, $aSpec, $aPipes);
    if (!is_resource($hProc)) {
        fail("Error converting osm to osc, osmosis failed\n");
    }
    fwrite($aPipes[0], $sModifyXMLstr);
    fclose($aPipes[0]);
    $sOut = stream_get_contents($aPipes[1]);
    if ($aResult['verbose']) echo $sOut;
    fclose($aPipes[1]);
    $sErrors = stream_get_contents($aPipes[2]);
    if ($aResult['verbose']) echo $sErrors;
    fclose($aPipes[2]);
    if ($iError = proc_close($hProc)) {
        echo $sOut;
        echo $sErrors;
        fail("Error converting osm to osc, osmosis returned: $iError\n");
    }
}

if ($bHaveDiff) {
    // import generated change file
    $sCMD = $sOsm2pgsqlCmd.' '.$sTemporaryFile;
    echo $sCMD."\n";
    exec($sCMD, $sJunk, $iErrorLevel);
    if ($iErrorLevel) {
        fail("osm2pgsql exited with error level $iErrorLevel\n");
    }
}

if ($aResult['deduplicate']) {
    //
    if (getPostgresVersion() < 9.3) {
        fail("ERROR: deduplicate is only currently supported in postgresql 9.3");
    }

    $oDB =& getDB();
    $sSQL = 'select partition from country_name order by country_code';
    $aPartitions = chksql($oDB->getCol($sSQL));
    $aPartitions[] = 0;

    $sSQL = "select word_token,count(*) from word where substr(word_token, 1, 1) = ' '";
    $sSQL .= " and class is null and type is null and country_code is null";
    $sSQL .= " group by word_token having count(*) > 1 order by word_token";
    $aDuplicateTokens = chksql($oDB->getAll($sSQL));
    foreach ($aDuplicateTokens as $aToken) {
        if (trim($aToken['word_token']) == '' || trim($aToken['word_token']) == '-') continue;
        echo "Deduping ".$aToken['word_token']."\n";
        $sSQL = "select word_id,";
        $sSQL .= " (select count(*) from search_name where nameaddress_vector @> ARRAY[word_id]) as num";
        $sSQL .= " from word where word_token = '".$aToken['word_token'];
        $sSQL .= "' and class is null and type is null and country_code is null order by num desc";
        $aTokenSet = chksql($oDB->getAll($sSQL));

        $aKeep = array_shift($aTokenSet);
        $iKeepID = $aKeep['word_id'];

        foreach ($aTokenSet as $aRemove) {
            $sSQL = "update search_name set";
            $sSQL .= " name_vector = array_replace(name_vector,".$aRemove['word_id'].",".$iKeepID."),";
            $sSQL .= " nameaddress_vector = array_replace(nameaddress_vector,".$aRemove['word_id'].",".$iKeepID.")";
            $sSQL .= " where name_vector @> ARRAY[".$aRemove['word_id']."]";
            chksql($oDB->query($sSQL));

            $sSQL = "update search_name set";
            $sSQL .= " nameaddress_vector = array_replace(nameaddress_vector,".$aRemove['word_id'].",".$iKeepID.")";
            $sSQL .= " where nameaddress_vector @> ARRAY[".$aRemove['word_id']."]";
            chksql($oDB->query($sSQL));

            $sSQL = "update location_area_country set";
            $sSQL .= " keywords = array_replace(keywords,".$aRemove['word_id'].",".$iKeepID.")";
            $sSQL .= " where keywords @> ARRAY[".$aRemove['word_id']."]";
            chksql($oDB->query($sSQL));

            foreach ($aPartitions as $sPartition) {
                $sSQL = "update search_name_".$sPartition." set";
                $sSQL .= " name_vector = array_replace(name_vector,".$aRemove['word_id'].",".$iKeepID.")";
                $sSQL .= " where name_vector @> ARRAY[".$aRemove['word_id']."]";
                chksql($oDB->query($sSQL));

                $sSQL = "update location_area_country set";
                $sSQL .= " keywords = array_replace(keywords,".$aRemove['word_id'].",".$iKeepID.")";
                $sSQL .= " where keywords @> ARRAY[".$aRemove['word_id']."]";
                chksql($oDB->query($sSQL));
            }

            $sSQL = "delete from word where word_id = ".$aRemove['word_id'];
            chksql($oDB->query($sSQL));
        }
    }
}

if ($aResult['index']) {
    passthru(CONST_InstallPath.'/nominatim/nominatim -i -d '.$aDSNInfo['database'].' -P '.$aDSNInfo['port'].' -t '.$aResult['index-instances'].' -r '.$aResult['index-rank']);
}

if ($aResult['import-osmosis'] || $aResult['import-osmosis-all']) {
    //
    if (strpos(CONST_Replication_Url, 'download.geofabrik.de') !== false && CONST_Replication_Update_Interval < 86400) {
        fail("Error: Update interval too low for download.geofabrik.de.  Please check install documentation (http://wiki.openstreetmap.org/wiki/Nominatim/Installation#Updates)\n");
    }

    $sImportFile = CONST_BasePath.'/data/osmosischange.osc';
    $sOsmosisConfigDirectory = CONST_InstallPath.'/settings';
    $sCMDDownload = CONST_Osmosis_Binary.' --read-replication-interval workingDirectory='.$sOsmosisConfigDirectory.' --simplify-change --write-xml-change '.$sImportFile;
    $sCMDCheckReplicationLag = CONST_Osmosis_Binary.' -q --read-replication-lag workingDirectory='.$sOsmosisConfigDirectory;
    $sCMDImport = $sOsm2pgsqlCmd.' '.$sImportFile;
    $sCMDIndex = CONST_InstallPath.'/nominatim/nominatim -i -d '.$aDSNInfo['database'].' -P '.$aDSNInfo['port'].' -t '.$aResult['index-instances'];

    while (true) {
        $fStartTime = time();
        $iFileSize = 1001;

        if (!file_exists($sImportFile)) {
            // First check if there are new updates published (except for minutelies - there's always new diffs to process)
            if (CONST_Replication_Update_Interval > 60) {
                unset($aReplicationLag);
                exec($sCMDCheckReplicationLag, $aReplicationLag, $iErrorLevel);
                while ($iErrorLevel > 0 || $aReplicationLag[0] < 1) {
                    if ($iErrorLevel) {
                        echo "Error: $iErrorLevel. ";
                        echo "Re-trying: ".$sCMDCheckReplicationLag." in ".CONST_Replication_Recheck_Interval." secs\n";
                    } else {
                        echo ".";
                    }
                    sleep(CONST_Replication_Recheck_Interval);
                    unset($aReplicationLag);
                    exec($sCMDCheckReplicationLag, $aReplicationLag, $iErrorLevel);
                }
                // There are new replication files - use osmosis to download the file
                echo "\n".date('Y-m-d H:i:s')." Replication Delay is ".$aReplicationLag[0]."\n";
            }
            $fStartTime = time();
            $fCMDStartTime = time();
            echo $sCMDDownload."\n";
            exec($sCMDDownload, $sJunk, $iErrorLevel);
            while ($iErrorLevel > 0) {
                echo "Error: $iErrorLevel\n";
                sleep(60);
                echo 'Re-trying: '.$sCMDDownload."\n";
                exec($sCMDDownload, $sJunk, $iErrorLevel);
            }
            $iFileSize = filesize($sImportFile);
            $sBatchEnd = getosmosistimestamp($sOsmosisConfigDirectory);
            $sSQL = "INSERT INTO import_osmosis_log values ('$sBatchEnd',$iFileSize,'".date('Y-m-d H:i:s', $fCMDStartTime)."','".date('Y-m-d H:i:s')."','osmosis')";
            var_Dump($sSQL);
            $oDB->query($sSQL);
            echo date('Y-m-d H:i:s')." Completed osmosis step for $sBatchEnd in ".round((time()-$fCMDStartTime)/60, 2)." minutes\n";
        }

        $iFileSize = filesize($sImportFile);
        $sBatchEnd = getosmosistimestamp($sOsmosisConfigDirectory);

        // Import the file
        $fCMDStartTime = time();
        echo $sCMDImport."\n";
        exec($sCMDImport, $sJunk, $iErrorLevel);
        if ($iErrorLevel) {
            echo "Error: $iErrorLevel\n";
            exit($iErrorLevel);
        }
        $sSQL = "INSERT INTO import_osmosis_log values ('$sBatchEnd',$iFileSize,'".date('Y-m-d H:i:s', $fCMDStartTime)."','".date('Y-m-d H:i:s')."','osm2pgsql')";
        var_Dump($sSQL);
        $oDB->query($sSQL);
        echo date('Y-m-d H:i:s')." Completed osm2pgsql step for $sBatchEnd in ".round((time()-$fCMDStartTime)/60, 2)." minutes\n";

        // Archive for debug?
        unlink($sImportFile);

        $sBatchEnd = getosmosistimestamp($sOsmosisConfigDirectory);

        // Index file
        $sThisIndexCmd = $sCMDIndex;
        $fCMDStartTime = time();

        if (!$aResult['no-index']) {
            echo "$sThisIndexCmd\n";
            exec($sThisIndexCmd, $sJunk, $iErrorLevel);
            if ($iErrorLevel) {
                echo "Error: $iErrorLevel\n";
                exit($iErrorLevel);
            }
        }

        $sSQL = "INSERT INTO import_osmosis_log values ('$sBatchEnd',$iFileSize,'".date('Y-m-d H:i:s', $fCMDStartTime)."','".date('Y-m-d H:i:s')."','index')";
        var_Dump($sSQL);
        $oDB->query($sSQL);
        echo date('Y-m-d H:i:s')." Completed index step for $sBatchEnd in ".round((time()-$fCMDStartTime)/60, 2)." minutes\n";

        $sSQL = "update import_status set lastimportdate = '$sBatchEnd'";
        $oDB->query($sSQL);

        $fDuration = time() - $fStartTime;
        echo date('Y-m-d H:i:s')." Completed all for $sBatchEnd in ".round($fDuration/60, 2)." minutes\n";
        if (!$aResult['import-osmosis-all']) exit(0);

        if (CONST_Replication_Update_Interval > 60) {
            $iSleep = max(0, (strtotime($sBatchEnd)+CONST_Replication_Update_Interval-time()));
        } else {
            $iSleep = max(0, CONST_Replication_Update_Interval-$fDuration);
        }
        echo date('Y-m-d H:i:s')." Sleeping $iSleep seconds\n";
        sleep($iSleep);
    }
}


function getosmosistimestamp($sOsmosisConfigDirectory)
{
    $sStateFile = file_get_contents($sOsmosisConfigDirectory.'/state.txt');
    preg_match('#timestamp=(.+)#', $sStateFile, $aResult);
    return str_replace('\:', ':', $aResult[1]);
}
