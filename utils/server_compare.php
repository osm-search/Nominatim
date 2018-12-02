#!/usr/bin/php -Cq
<?php

$sFile = 'sample.log.txt'; // Apache log file
$sHost1 = 'http://mq-open-search-lm02.ihost.aol.com:8000/nominatim/v1';
$sHost2 = 'http://mq-open-search-lm03.ihost.aol.com:8000/nominatim/v1';


$sHost1Escaped = str_replace('/', '\\/', $sHost1);
$sHost2Escaped = str_replace('/', '\\/', $sHost2);

$aToDo = array(251, 293, 328, 399.1, 455.1, 479, 496, 499, 574, 609, 702, 790, 846, 865, 878, 894, 902, 961, 980);

$hFile = @fopen($sFile, 'r');
if (!$hFile) {
    echo "Unable to open file: $sFile\n";
    exit;
}

$i = 0;
while (($sLine = fgets($hFile, 10000)) !== false) {
    $i++;
    if (!in_array($i, $aToDo)) continue;

    if (preg_match('#"GET (.*) HTTP/1.[01]"#', $sLine, $aResult)) {
        $sURL1 = $sHost1.$aResult[1];
        $sURL2 = $sHost2.$aResult[1];

        $sRes1 = '';
        $k = 0;
        while (!$sRes1 && $k < 10) {
            $sRes1 = file_get_contents($sURL1);
            $k++;
            if (!$sRes1) sleep(10);
        }
        $sRes2 = file_get_contents($sURL2);

        // Strip out the things that will always change
        $sRes1 =  preg_replace('# timestamp=\'[^\']*\'#', '', $sRes1);
        $sRes1 =  str_replace($sHost1, '', $sRes1);
        $sRes1 =  str_replace($sHost1Escaped, '', $sRes1);
        $sRes2 =  preg_replace('# timestamp=\'[^\']*\'#', '', $sRes2);
        $sRes2 =  str_replace($sHost2, '', $sRes2);
        $sRes2 =  str_replace($sHost2Escaped, '', $sRes2);

        if ($sRes1 != $sRes2) {
            echo "$i:\n";
            var_dump($sURL1, $sURL2);

            $sRes = $sURL1.":\n";
            for ($j = 0; $j < strlen($sRes1); $j+=40) {
                $sRes .= substr($sRes1, $j, 40)."\n";
            }
            file_put_contents('log/'.$i.'.1', $sRes);

            $sRes = $sURL2.":\n";
            for ($j = 0; $j < strlen($sRes2); $j+=40) {
                $sRes .= substr($sRes2, $j, 40)."\n";
            }
            file_put_contents('log/'.$i.'.2', $sRes);
        }
        echo ".\n";
    } else {
        var_dump($sLine);
    }
}

fclose($hFile);
