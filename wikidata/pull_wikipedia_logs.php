<?php

for ($iTimestamp = mktime(0, 0, 0, 5, 1, 2013); $iTimestamp < mktime(0, 0, 0, 6, 15, 2013); $iTimestamp += 24*60*60) {
    $sYear = date("Y", $iTimestamp);
    $sMonth = date("Y-m", $iTimestamp);
    $sDay = date("Ymd", $iTimestamp);

    for ($iHour = 0; $iHour < 24; $iHour++) {
        $sFilename = sprintf("pagecounts-".$sDay."-%02d0000", $iHour);
        echo $sFilename."\n";
        if (!file_exists($sFilename.'.gz')) {
            exec('wget http://dumps.wikimedia.org/other/pagecounts-raw/'.$sYear.'/'.$sMonth.'/'.$sFilename.'.gz');
        }

        exec('gzip -dc '.$sFilename.'.gz'.' | grep -e "^[a-z]\{2\} [^ :]\+ [0-9]\+" > hour.txt');

        $hPrevTotals = @fopen("totals.txt", "r");
        $hDayTotals = @fopen("hour.txt", "r");
        $hNewTotals = @fopen("newtotals.txt", "w");

        $sPrevKey = $sDayKey = true;
        $sPrevLine = true;
        $sDayLine = true;

        do {
            if ($sPrevKey === $sDayKey) {
                if ($sPrevLine !== true) fputs($hNewTotals, "$sPrevKey ".($iPrevValue+$iDayValue)."\n");
                $sPrevLine = true;
                $sDayLine = true;
            } elseif ($sDayKey !== false && ($sPrevKey > $sDayKey || $sPrevKey === false)) {
                fputs($hNewTotals, "$sDayKey ".($iDayValue)."\n");
                $sDayLine = true;
            } elseif ($sPrevKey !== false && ($sDayKey > $sPrevKey || $sDayKey === false)) {
                fputs($hNewTotals, "$sPrevKey ".($iPrevValue)."\n");
                $sPrevLine = true;
            }

            if ($sPrevLine === true) {
                $sPrevLine = $hPrevTotals?fgets($hPrevTotals, 4096):false;
                if ($sPrevLine !== false) {
                    $aPrevLine = explode(' ', $sPrevLine);
                    $sPrevKey = $aPrevLine[0].' '.$aPrevLine[1];
                    $iPrevValue = (int)$aPrevLine[2];
                } else {
                    $sPrevKey = false;
                    $iPrevValue =  0;
                }
            }

            if ($sDayLine === true) {
                $sDayLine = $hDayTotals?fgets($hDayTotals, 4096):false;
                if ($sDayLine !== false) {
                    preg_match('#^([a-z]{2}) ([^ :]+) ([0-9]+) [0-9]+$#', $sDayLine, $aMatch);
                    $sDayKey = $aMatch[1].' '.$aMatch[2];
                    $iDayValue = (int)$aMatch[3];
                } else {
                    $sDayKey = false;
                    $iDayValue = 0;
                }
            }
        } while ($sPrevLine !== false || $sDayLine !== false);

        @fclose($hPrevTotals);
        @fclose($hDayTotals);
        @fclose($hNewTotals);

        @unlink("totals.txt");
        rename("newtotals.txt", "totals.txt");
    }
}

// Notes:
/*
 gzip -dc $FILE.gz | grep -e "^en [^ :]\+ [0-9]\+" | sed "s#\(^[a-z]\{2\}\) \([^ :]\+\) \([0-9]\+\) [0-9]\+#update wikipedia_article set hit_count = coalesce(hit_count,0) + \3 where language = '\1' and title = catch_decode_url_part('\2');#g" | /opt/mapquest/stdbase-dev$
 cat totals.txt | sed "s#\(^[a-z]\{2\}\) \([^ ]\+\) \([0-9]\+\)\$#update entity_link set hits = s,0) + \3 where target = '\1wiki' and value = catch_decode_url_part('\2');#g"
 cat totals.txt | sed "s#\(^[a-z]\{2\}\) \([^ ]\+\) \([0-9]\+\)\$#update entity_link set hits = coalesce(hits,0) + \3 where target = '\1wiki' and value = catch_decode_url_part('\2');#g"
*/
