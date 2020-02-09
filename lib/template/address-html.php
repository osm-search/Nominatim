<?php
    header("content-type: text/html; charset=UTF-8");
?>
<?php include(CONST_BasePath.'/lib/template/includes/html-header.php'); ?>
    <link href="css/common.css" rel="stylesheet" type="text/css" />
    <link href="css/search.css" rel="stylesheet" type="text/css" />
</head>

<body id="reverse-page">

    <?php include(CONST_BasePath.'/lib/template/includes/html-top-navigation.php'); ?>

    <form class="form-inline" role="search" accept-charset="UTF-8" action="<?php echo CONST_Website_BaseURL; ?>reverse.php">
        <div class="form-group">
            <input name="format" type="hidden" value="html">
            lat
            <input name="lat" type="text" class="form-control input-sm" placeholder="latitude" value="<?php echo $fLat; ?>" >
            <a href="#" class="btn btn-default btn-xs" id="switch-coords" title="switch lat and lon">&lt;&gt;</a>
            lon
            <input name="lon" type="text" class="form-control input-sm" placeholder="longitude" value="<?php echo $fLon; ?>" >
            max zoom

            <select name="zoom" class="form-control input-sm">
                <option value="" <?php if ($iZoom === false) echo 'selected="selected"' ?> >--</option>
                <?php

                    $aZoomLevels = array(
                         0 => "Continent / Sea",
                         1 => "",
                         2 => "",
                         3 => "Country",
                         4 => "",
                         5 => "State",
                         6 => "Region",
                         7 => "",
                         8 => "County",
                         9 => "",
                        10 => "City",
                        11 => "",
                        12 => "Town / Village",
                        13 => "",
                        14 => "Suburb",
                        15 => "",
                        16 => "Street",
                        17 => "",
                        18 => "Building",
                        19 => "",
                        20 => "",
                        21 => "",
                    );

                    foreach($aZoomLevels as $iZoomLevel => $sLabel)
                    {
                        $bSel = $iZoom === $iZoomLevel;
                        echo '<option value="'.$iZoomLevel.'"'.($bSel?' selected="selected"':'').'>'.$iZoomLevel.' '.$sLabel.'</option>'."\n";
                    }
                ?>
            </select>
        </div>
        <div class="form-group search-button-group">
            <button type="submit" class="btn btn-primary btn-sm">Search</button>
        </div>
        <div class="search-type-link">
            <a href="<?php echo CONST_Website_BaseURL; ?>search.php">forward search</a>
        </div>
    </form>


    <div id="content">

<?php if (count($aPlace)>0) { ?>

        <div id="searchresults" class="sidebar">
        <?php
            $aResult = $aPlace;

            echo '<div class="result" data-position="0">';

            echo (isset($aResult['icon'])?'<img alt="icon" src="'.$aResult['icon'].'"/>':'');
            echo ' <span class="name">'.htmlspecialchars($aResult['langaddress']).'</span>';
            if (isset($aResult['label']))
                echo ' <span class="type">('.$aResult['label'].')</span>';
            else if ($aResult['type'] == 'yes')
                echo ' <span class="type">('.ucwords(str_replace('_',' ',$aResult['class'])).')</span>';
            else
                echo ' <span class="type">('.ucwords(str_replace('_',' ',$aResult['type'])).')</span>';
            echo '<p>'.$aResult['lat'].','.$aResult['lon'].'</p>';
            echo detailsPermaLink($aResult, 'details', 'class="btn btn-default btn-xs details"');
            echo '</div>';
        ?>
        </div>

<?php } else { ?>

        <div id="intro" class="sidebar">
            Search for coordinates or click anywhere on the map.
        </div>

<?php } ?>

        <div id="map-wrapper">
            <div id="map-position">
                <div id="map-position-inner"></div>
                <div id="map-position-close"><a href="#">hide</a></div>
            </div>
            <div id="map"></div>
        </div>

    </div> <!-- /content -->







    <script type="text/javascript">
    <?php

        $aNominatimMapInit = array(
            'zoom' => $iZoom !== false ? $iZoom : CONST_Default_Zoom,
            'lat'  => $fLat !== false ? $fLat : CONST_Default_Lat,
            'lon'  => $fLon !== false ? $fLon : CONST_Default_Lon,
            'tile_url' => $sTileURL,
            'tile_attribution' => $sTileAttribution
        );
        echo 'var nominatim_map_init = ' . json_encode($aNominatimMapInit, JSON_PRETTY_PRINT) . ';';

        echo 'var nominatim_results = ' . json_encode([$aPlace], JSON_PRETTY_PRINT) . ';'; 
    ?>
    </script>
    <?php include(CONST_BasePath.'/lib/template/includes/html-footer.php'); ?>

</body>
</html>
