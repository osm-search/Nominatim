<?php
header('content-type: text/xml; charset=UTF-8');

echo '<';
echo '?xml version="1.0" encoding="UTF-8" ?';
echo ">\n";

echo '<';
echo (isset($sXmlRootTag)?$sXmlRootTag:'searchresults');
echo " timestamp='".date(DATE_RFC822)."'";
// echo " attribution='Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright'";
echo " querystring='".htmlspecialchars($sQuery, ENT_QUOTES)."'";
if (isset($aMoreParams['viewbox'])) {
    echo " viewbox='".htmlspecialchars($aMoreParams['viewbox'], ENT_QUOTES)."'";
}
echo " polygon='".(isset($aMoreParams['polygon'])?'true':'false')."'";
if (isset($aMoreParams['exclude_place_ids'])) {
    echo " exclude_place_ids='".htmlspecialchars($aMoreParams['exclude_place_ids'])."'";
}
echo " more_url='".htmlspecialchars($sMoreURL)."'";
echo ">\n";

foreach ($aSearchResults as $iResNum => $aResult) {
    echo "<place place_id='".$aResult['place_id']."'";
    echo " licence='".$aResult['licence']."'";
    echo " copyright='".$aResult['copyright']."'";
    $sOSMType = formatOSMType($aResult['osm_type']);
    if ($sOSMType) {
        echo " osm_type='$sOSMType'";
        echo " osm_id='".$aResult['osm_id']."'";
    }
    echo " place_rank='".$aResult['rank_search']."'";

    if (isset($aResult['aBoundingBox'])) {
        echo ' boundingbox="';
        echo join(',', $aResult['aBoundingBox']);
        echo '"';

        if (isset($aResult['aPolyPoints'])) {
            echo ' polygonpoints=\'';
            echo json_encode($aResult['aPolyPoints']);
            echo '\'';
        }
    }

    if (isset($aResult['asgeojson'])) {
        echo ' geojson=\'';
        echo $aResult['asgeojson'];
        echo '\'';
    }

    if (isset($aResult['assvg'])) {
        echo ' geosvg=\'';
        echo $aResult['assvg'];
        echo '\'';
    }

    if (isset($aResult['astext'])) {
        echo ' geotext=\'';
        echo $aResult['astext'];
        echo '\'';
    }

    if (isset($aResult['zoom'])) {
        echo " zoom='".$aResult['zoom']."'";
    }

    echo " lat='".$aResult['lat']."'";
    echo " lon='".$aResult['lon']."'";
    echo " display_name='".htmlspecialchars($aResult['name'], ENT_QUOTES)."'";

    echo " class='".htmlspecialchars($aResult['class'])."'";
    echo " type='".htmlspecialchars($aResult['type'], ENT_QUOTES)."'";
    echo " importance='".htmlspecialchars($aResult['importance'])."'";
    if (isset($aResult['icon']) && $aResult['icon']) {
        echo " icon='".htmlspecialchars($aResult['icon'], ENT_QUOTES)."'";
    }

    $bHasDelim = false;

    if (isset($aResult['askml'])) {
        if (!$bHasDelim) {
            $bHasDelim = true;
            echo '>';
        }
        echo "\n<geokml>";
        echo $aResult['askml'];
        echo '</geokml>';
    }

    if (isset($aResult['sExtraTags'])) {
        if (!$bHasDelim) {
            $bHasDelim = true;
            echo '>';
        }
        echo "\n<extratags>";
        foreach ($aResult['sExtraTags'] as $sKey => $sValue) {
            echo '<tag key="'.htmlspecialchars($sKey).'" value="'.htmlspecialchars($sValue).'"/>';
        }
        echo '</extratags>';
    }

    if (isset($aResult['sNameDetails'])) {
        if (!$bHasDelim) {
            $bHasDelim = true;
            echo '>';
        }
        echo "\n<namedetails>";
        foreach ($aResult['sNameDetails'] as $sKey => $sValue) {
            echo '<name desc="'.htmlspecialchars($sKey).'">';
            echo htmlspecialchars($sValue);
            echo '</name>';
        }
        echo '</namedetails>';
    }

    if (isset($aResult['address'])) {
        if (!$bHasDelim) {
            $bHasDelim = true;
            echo '>';
        }
        echo "\n";
        foreach ($aResult['address']->getAddressNames() as $sKey => $sValue) {
            $sKey = str_replace(' ', '_', $sKey);
            echo "<$sKey>";
            echo htmlspecialchars($sValue);
            echo "</$sKey>";
        }
    }

    if ($bHasDelim) {
        echo '</place>';
    } else {
        echo '/>';
    }
}

echo '</' . (isset($sXmlRootTag)?$sXmlRootTag:'searchresults') . '>';
