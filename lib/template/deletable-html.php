<?php
    header("content-type: text/html; charset=UTF-8");
    include(CONST_BasePath.'/lib/template/includes/html-header.php');
?>
    <title>Nominatim Deleted Data</title>    
    <meta name="description" content="List of OSM data that has been deleted" lang="en-US" />
</head>

<body>
<div class="container">
    <h1>Deletable</h1>
    <p>
        <?php echo sizeof($aPolygons) ?> objects have been deleted in OSM but are still in the Nominatim database.
        Also available in <a href="<?php echo CONST_Website_BaseURL; ?>deletable.php?format=json">JSON format</a>.
    </p>

    <table class="table table-striped table-hover">
<?php

if (!empty($aPolygons)) {
    echo '<tr>';
    foreach (array_keys($aPolygons[0]) as $sCol) {
        echo '<th>'.$sCol.'</th>';
    }
    echo '</tr>';
    foreach ($aPolygons as $aRow) {
        echo '<tr>';
        foreach ($aRow as $sCol => $sVal) {
            switch ($sCol) {
                case 'osm_id':
                    echo '<td>'.osmLink($aRow).'</td>';
                    break;
                case 'place_id':
                    echo '<td>'.detailsLink($aRow).'</td>';
                    break;
                default:
                    echo '<td>'.($sVal?$sVal:'&nbsp;').'</td>';
                    break;
            }
        }
        echo '</tr>';
    }
}
?>
    </table>
</div>
</body>
</html>
