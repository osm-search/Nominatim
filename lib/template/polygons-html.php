<?php
    header("content-type: text/html; charset=UTF-8");
    include(CONST_BasePath.'/lib/template/includes/html-header.php');
?>
    <title>Nominatim Broken Polygon Data</title>    
    <meta name="description" content="List of broken OSM polygon data by date" lang="en-US" />
</head>

<body>

<div class="container">
    <h1>Broken polygons</h1>

    <p>
        Total number of broken polygons: <?php echo $iTotalBroken ?>.
        Also available in <a href="<?php echo CONST_Website_BaseURL; ?>polygons.php?format=json">JSON format</a>.
    </p>

    <table class="table table-striped table-hover">

<?php
if (!empty($aPolygons)) {

    echo '<tr>';
    //var_dump($aPolygons[0]);
    foreach (array_keys($aPolygons[0]) as $sCol) {
        echo '<th>'.$sCol.'</th>';
    }
    echo '<th>&nbsp;</th>';
    echo '</tr>';
    $aSeen = array();
    foreach ($aPolygons as $aRow) {
        if (isset($aSeen[$aRow['osm_type'].$aRow['osm_id']])) continue;
        $aSeen[$aRow['osm_type'].$aRow['osm_id']] = 1;

        echo '<tr>';
        $sOSMType = formatOSMType($aRow['osm_type']);
        foreach ($aRow as $sCol => $sVal) {
            switch ($sCol) {
                case 'errormessage':
                    if (preg_match('/Self-intersection\\[([0-9.\\-]+) ([0-9.\\-]+)\\]/', $sVal, $aMatch)) {
                        $aRow['lat'] = $aMatch[2];
                        $aRow['lon'] = $aMatch[1];
                        $sUrl = sprintf('https://www.openstreetmap.org/?lat=%f&lon=%f&zoom=18&layers=M&%s=%d',
                                $aRow['lat'],
                                $aRow['lon'],
                                $sOSMType,
                                $aRow['osm_id']);
                        echo '<td><a href="'.$sUrl.'">'.($sVal?$sVal:'&nbsp;').'</a></td>';
                    } else {
                        echo '<td>'.($sVal?$sVal:'&nbsp;').'</td>';
                    }
                    break;
                case 'osm_id':
                    echo '<td>'.osmLink(array('osm_type' => $aRow['osm_type'], 'osm_id' => $aRow['osm_id'])).'</td>';
                    break;
                default:
                    echo '<td>'.($sVal?$sVal:'&nbsp;').'</td>';
                    break;
            }
        }
        $sJosmUrl = 'http://localhost:8111/import?url=https://www.openstreetmap.org/api/0.6/'.$sOSMType.'/'.$aRow['osm_id'].'/full';
        echo '<td><a href="'.$sJosmUrl.'" target="josm">josm</a></td>';
        echo '</tr>';
    }
    echo '</table>';
}
?>
</div>
</body>
</html>