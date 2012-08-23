<?php
header("content-type: text/html; charset=UTF-8");
?>
<html>
  <head>
    <title>OpenStreetMap Nominatim: Suburbs</title>
  </head>

<?php

if (sizeof($aParentOfLines)) {
    $aGroupedAddressLines = array();
    foreach ($aParentOfLines as $aAddressLine) {
        if (!isset($aGroupedAddressLines[$aAddressLine['type']]))
            $aGroupedAddressLines[$aAddressLine['type']] = array();
        $aGroupedAddressLines[$aAddressLine['type']][] = $aAddressLine;
    }
    foreach ($aGroupedAddressLines as $sGroupHeading => $aParentOfLines) {
        $sGroupHeading = ucwords($sGroupHeading);
        echo "<h3>$sGroupHeading</h3>";
        foreach ($aParentOfLines as $aAddressLine) {
            echo '<div class="line">';
            echo '<span class="name">' . (trim($aAddressLine['localname']) ? $aAddressLine['localname'] : '<span class="noname">No Name</span>') . '</span>';
            echo ', <span class="distance">~' . (round($aAddressLine['distance'] * 69, 1)) . '&nbsp;miles</span>';
            echo ', <span class="lat">lat=' . $aAddressLine['lat'] . '</span>';
            echo ', <span class="lon">lon=' . $aAddressLine['lon'] . '</span>';
            echo ', <span class="osm_id">osm_id=' . $aAddressLine['osm_id'] . '</span>';
            echo ', <span class="place_id">place_id=' . $aAddressLine['place_id'] . '</span>';
            echo '</div>';
        }
    }
    echo '</div>';
} else {
    echo 'No suburbs.';
}

?>

  </body>
</html>