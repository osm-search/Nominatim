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

   array('init-updates', '', 0, 1, 0, 0, 'bool', 'Set up database for updating'),
   array('import-osmosis', '', 0, 1, 0, 0, 'bool', 'Import updates once'),
   array('import-osmosis-all', '', 0, 1, 0, 0, 'bool', 'Import updates forever'),
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

if ($aResult['init-updates']) {
    // sanity check that the replication URL is correct
    $sBaseState = file_get_contents(CONST_Replication_Url.'/state.txt');
    if ($sBaseState === false) {
        echo "\nCannot find state.txt file at the configured replication URL.\n";
        echo "Does the URL point to a directory containing OSM update data?\n\n";
        fail("replication URL not reachable.");
    }
    $sSetup = CONST_InstallPath.'/utils/setup.php';
    $iRet = -1;
    passthru($sSetup.' --create-functions --enable-diff-updates', $iRet);
    if ($iRet != 0) {
        fail('Error running setup script');
    }

    $sDatabaseDate = getDatabaseDate($oDB);
    if ($sDatabaseDate === false) {
        fail("Cannot determine date of database.");
    }
    $sWindBack = strftime('%Y-%m-%dT%H:%M:%SZ',
                          strtotime($sDatabaseDate) - (3*60*60));

    // get the appropriate state id
    $aOutput = 0;
    $sCmd = CONST_Pyosmium_Binary.' -D '.$sWindBack.' --server '.CONST_Replication_Url;
    exec($sCmd, $aOutput, $iRet);
    if ($iRet != 0 || $aOutput[0] == 'None') {
        fail('Error running pyosmium tools');
    }

    pg_query($oDB->connection, 'TRUNCATE import_status');
    $sSQL = "INSERT INTO import_status (lastimportdate, sequence_id, indexed) VALUES('";
    $sSQL .= $sDatabaseDate."',".$aOutput[0].", true)";
    if (!pg_query($oDB->connection, $sSQL)) {
        fail("Could not enter sequence into database.");
    }

    echo "Done. Database updates will start at sequence $aOutput[0] ($sWindBack)\n";
}

if (isset($aResult['import-diff']) || isset($aResult['import-file'])) {
    // import diffs and files directly (e.g. from osmosis --rri)
    $sNextFile = isset($aResult['import-diff']) ? $aResult['import-diff'] : $aResult['import-file'];
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
    file_put_contents($sTemporaryFile, file_get_contents($sContentURL));
    $bHaveDiff = true;
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
    $oDB =& getDB();

    if (getPostgresVersion($oDB) < 9.3) {
        fail("ERROR: deduplicate is only currently supported in postgresql 9.3");
    }

    $sSQL = 'select partition from country_name order by country_code';
    $aPartitions = chksql($oDB->getCol($sSQL));
    $aPartitions[] = 0;

    // we don't care about empty search_name_* partitions, they can't contain mentions of duplicates
    foreach ($aPartitions as $i => $sPartition) {
        $sSQL = "select count(*) from search_name_".$sPartition;
        $nEntries = chksql($oDB->getOne($sSQL));
        if ($nEntries == 0) {
            unset($aPartitions[$i]);
        }
    }

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

    $sImportFile = CONST_InstallPath.'/osmosischange.osc';
    $sCMDDownload = CONST_Pyosmium_Binary.' --server '.CONST_Replication_Url.' -o '.$sImportFile.' -s '.CONST_Replication_Max_Diff_size;
    $sCMDImport = $sOsm2pgsqlCmd.' '.$sImportFile;
    $sCMDIndex = CONST_InstallPath.'/nominatim/nominatim -i -d '.$aDSNInfo['database'].' -P '.$aDSNInfo['port'].' -t '.$aResult['index-instances'];

    while (true) {
        $fStartTime = time();
        $aLastState = chksql($oDB->getRow('SELECT *, EXTRACT (EPOCH FROM lastimportdate) as unix_ts FROM import_status'));

        if (!$aLastState['sequence_id']) {
            echo "Updates not set up. Please run ./utils/update.php --init-updates.\n";
            exit(1);
        }

        echo 'Currently at sequence '.$aLastState['sequence_id'].' ('.$aLastState['lastimportdate'].') - '.$aLastState['indexed']." indexed\n";

        $sBatchEnd = $aLastState['lastimportdate'];
        $iEndSequence = $aLastState['sequence_id'];

        if ($aLastState['indexed'] == 't') {
            // Sleep if the update interval has not yet been reached.
            $fNextUpdate = $aLastState['unix_ts'] + CONST_Replication_Update_Interval;
            if ($fNextUpdate > $fStartTime) {
                $iSleepTime = $fNextUpdate - $fStartTime;
                echo "Waiting for next update for $iSleepTime sec.";
                sleep($iSleepTime);
            }

            // Download the next batch of changes.
            do {
                $fCMDStartTime = time();
                $iNextSeq = (int) $aLastState['sequence_id'];
                unset($aOutput);
                echo "$sCMDDownload -I $iNextSeq\n";
                unlink($sImportFile);
                exec($sCMDDownload.' -I '.$iNextSeq, $aOutput, $iResult);

                if ($iResult == 3) {
                    echo 'No new updates. Sleeping for '.CONST_Replication_Recheck_Interval." sec.\n";
                    sleep(CONST_Replication_Recheck_Interval);
                } else if ($iResult != 0) {
                    echo 'ERROR: updates failed.';
                    exit($iResult);
                } else {
                    $iEndSequence = (int)$aOutput[0];
                }
            } while ($iResult);

            // get the newest object from the diff file
            $sBatchEnd = 0;
            $iRet = 0;
            exec(CONST_BasePath.'/utils/osm_file_date.py '.$sImportFile, $sBatchEnd, $iRet);
            if ($iRet == 5) {
                echo "Diff file is empty. skipping import.\n";
                if (!$aResult['import-osmosis-all']) {
                    exit(0);
                } else {
                    continue;
                }
            }
            if ($iRet != 0) {
                fail('Error getting date from diff file.');
            }
            $sBatchEnd = $sBatchEnd[0];

            // Import the file
            $fCMDStartTime = time();
            echo $sCMDImport."\n";
            unset($sJunk);
            exec($sCMDImport, $sJunk, $iErrorLevel);
            if ($iErrorLevel) {
                echo "Error executing osm2pgsql: $iErrorLevel\n";
                exit($iErrorLevel);
            }

            // write the update logs
            $iFileSize = filesize($sImportFile);
            $sSQL = "INSERT INTO import_osmosis_log (batchend, batchseq, batchsize, starttime, endtime, event) values ('$sBatchEnd',$iEndSequence,$iFileSize,'".date('Y-m-d H:i:s', $fCMDStartTime)."','".date('Y-m-d H:i:s')."','import')";
            var_Dump($sSQL);
            chksql($oDB->query($sSQL));

            // update the status
            $sSQL = "UPDATE import_status SET lastimportdate = '$sBatchEnd', indexed=false, sequence_id = $iEndSequence";
            var_Dump($sSQL);
            chksql($oDB->query($sSQL));
            echo date('Y-m-d H:i:s')." Completed download step for $sBatchEnd in ".round((time()-$fCMDStartTime)/60, 2)." minutes\n";
        }

        // Index file
        if (!$aResult['no-index']) {
            $sThisIndexCmd = $sCMDIndex;
            $fCMDStartTime = time();

            echo "$sThisIndexCmd\n";
            exec($sThisIndexCmd, $sJunk, $iErrorLevel);
            if ($iErrorLevel) {
                echo "Error: $iErrorLevel\n";
                exit($iErrorLevel);
            }

            $sSQL = "INSERT INTO import_osmosis_log (batchend, batchseq, batchsize, starttime, endtime, event) values ('$sBatchEnd',$iEndSequence,$iFileSize,'".date('Y-m-d H:i:s', $fCMDStartTime)."','".date('Y-m-d H:i:s')."','index')";
            var_Dump($sSQL);
            $oDB->query($sSQL);
            echo date('Y-m-d H:i:s')." Completed index step for $sBatchEnd in ".round((time()-$fCMDStartTime)/60, 2)." minutes\n";

            $sSQL = "update import_status set indexed = true";
            $oDB->query($sSQL);
        }

        $fDuration = time() - $fStartTime;
        echo date('Y-m-d H:i:s')." Completed all for $sBatchEnd in ".round($fDuration/60, 2)." minutes\n";
        if (!$aResult['import-osmosis-all']) exit(0);
    }
}

