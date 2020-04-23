<?php
header('content-type: text/xml; charset=UTF-8');

echo '<';
echo '?xml version="1.0" encoding="UTF-8" ?';
echo ">\n";

echo '<reversegeocode';
echo " timestamp='".date(DATE_RFC822)."'";
// echo " attribution='Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright'";
echo " querystring='".htmlspecialchars($_SERVER['QUERY_STRING'], ENT_QUOTES)."'";
echo ">\n";

if (empty($aPlace)) {
    if (isset($sError)) {
        echo "<error>$sError</error>";
    } else {
        echo '<error>Unable to geocode</error>';
    }
} else {
    echo '<result';
    if ($aPlace['place_id']) {
        echo ' place_id="'.$aPlace['place_id'].'"';
    }
    echo ' licence="'.$aPlace['licence'].'"';
    echo ' copyright="'.$aPlace['copyright'].'"';
    $sOSMType = formatOSMType($aPlace['osm_type']);
    if ($sOSMType) {
        echo ' osm_type="'.$sOSMType.'"'.' osm_id="'.$aPlace['osm_id'].'"';
    }
    if ($aPlace['ref']) {
        echo ' ref="'.htmlspecialchars($aPlace['ref']).'"';
    }
    if (isset($aPlace['lat'])) {
        echo ' lat="'.htmlspecialchars($aPlace['lat']).'"';
    }
    if (isset($aPlace['lon'])) {
        echo ' lon="'.htmlspecialchars($aPlace['lon']).'"';
    }
    if (isset($aPlace['aBoundingBox'])) {
        echo ' boundingbox="';
        echo join(',', $aPlace['aBoundingBox']);
        echo '"';
    }

    if (isset($aPlace['asgeojson'])) {
        echo ' geojson=\'';
        echo $aPlace['asgeojson'];
        echo '\'';
    }

    if (isset($aPlace['assvg'])) {
        echo ' geosvg=\'';
        echo $aPlace['assvg'];
        echo '\'';
    }

    if (isset($aPlace['astext'])) {
        echo ' geotext=\'';
        echo $aPlace['astext'];
        echo '\'';
    }
    echo '>'.htmlspecialchars($aPlace['langaddress']).'</result>';

    if (isset($aPlace['address'])) {
        echo '<addressparts>';
        foreach ($aPlace['address']->getAddressNames() as $sKey => $sValue) {
            $sKey = str_replace(' ', '_', $sKey);
            echo "<$sKey>";
            echo htmlspecialchars($sValue);
            echo "</$sKey>";
        }
        echo '</addressparts>';
    }

    if (isset($aPlace['sExtraTags'])) {
        echo '<extratags>';
        foreach ($aPlace['sExtraTags'] as $sKey => $sValue) {
            echo '<tag key="'.htmlspecialchars($sKey).'" value="'.htmlspecialchars($sValue).'"/>';
        }
        echo '</extratags>';
    }

    if (isset($aPlace['sNameDetails'])) {
        echo '<namedetails>';
        foreach ($aPlace['sNameDetails'] as $sKey => $sValue) {
            echo '<name desc="'.htmlspecialchars($sKey).'">';
            echo htmlspecialchars($sValue);
            echo '</name>';
        }
        echo '</namedetails>';
    }

    if (isset($aPlace['askml'])) {
        echo "\n<geokml>";
        echo $aPlace['askml'];
        echo '</geokml>';
    }
}

echo '</reversegeocode>';
