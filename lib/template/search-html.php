<?php
    header("content-type: text/html; charset=UTF-8");
?>
<?php include(CONST_BasePath.'/lib/template/includes/html-header.php'); ?>
    <link href="css/common.css" rel="stylesheet" type="text/css" />
    <link href="css/search.css" rel="stylesheet" type="text/css" />
</head>

<body id="search-page">

    <?php include(CONST_BasePath.'/lib/template/includes/html-top-navigation.php'); ?>

    <div class="top-bar" id="structured-query-selector">
        <div class="search-type-link">
            <a id="switch-to-reverse" href="<?php echo CONST_Website_BaseURL; ?>reverse.php?format=html">reverse search</a>
        </div>
        <?php
        if (empty($aMoreParams['q']) and empty($aMoreParams['street']) and empty($aMoreParams['city']) and empty($aMoreParams['county']) and empty($aMoreParams['state']) and empty($aMoreParams['country']) and empty($aMoreParams['postalcode'])) {
            echo '<div class="radio-inline"><input type="radio" name="query-selector" id="simple" value="simple" checked="checked">';
            echo '<label for="simple">simple</label></div>';
            echo '<div class="radio-inline"><input type="radio" name="query-selector" id="structured" value="structured">';
            echo '<label for="structured">structured</label></div>';
        }
        elseif (!empty($aMoreParams['q'])) {
            echo '<div class="radio-inline"><input type="radio" name="query-selector" id="simple" value="simple" checked="checked">';
            echo '<label for="simple">simple</label></div>';
            echo '<div class="radio-inline"><input type="radio" name="query-selector" id="structured" value="structured">';
            echo '<label for="structured">structured</label></div>';
        }
        else {
            echo '<div class="radio-inline"><input type="radio" name="query-selector" id="simple" value="simple">';
            echo '<label for="simple">simple</label></div>';
            echo '<div class="radio-inline"><input type="radio" name="query-selector" id="structured" value="structured" checked="checked">';
            echo '<label for="structured">structured</label></div>';
        }
        ?>

    <form role="search" accept-charset="UTF-8" action="<?php echo CONST_Website_BaseURL; ?>search.php">
        <div class="form-group-simple"
        <?php
        if (empty($aMoreParams['q']) and empty($aMoreParams['street']) and empty($aMoreParams['city']) and empty($aMoreParams['county']) and empty($aMoreParams['state']) and empty($aMoreParams['country']) and empty($aMoreParams['postalcode'])) {
            echo "style='display:block;'";
        }
        elseif (empty($aMoreParams['q'])) {
            echo "style='display:none;'";
        }
        ?>>
            <input id="q" name="q" type="text" class="form-control input-sm" placeholder="Search" value="<?php echo $aMoreParams['q']; ?>" >
        </div>
        <div class="form-group-structured"
        <?php
        if (empty($aMoreParams['street']) and empty($aMoreParams['city']) and empty($aMoreParams['county']) and empty($aMoreParams['state']) and empty($aMoreParams['country']) and empty($aMoreParams['postalcode'])) {
            echo "style='display:none;'";
        }
        else {
            echo "style='display:block;'";
        }
        ?>>
<div class="form-inline">
            <input id="street" name="street" type="text" class="form-control input-sm" placeholder="House number/Street" value="<?php echo $aMoreParams['street']; ?>" >
            <input id="city" name="city" type="text" class="form-control input-sm" placeholder="City" value="<?php echo $aMoreParams['city']; ?>" >
            <input id="county" name="county" type="text" class="form-control input-sm" placeholder="County" value="<?php echo $aMoreParams['county']; ?>" >
            <input id="state" name="state" type="text" class="form-control input-sm" placeholder="State" value="<?php echo $aMoreParams['state']; ?>" >
            <input id="country" name="country" type="text" class="form-control input-sm" placeholder="Country" value="<?php echo $aMoreParams['country']; ?>" >
            <input id="postalcode" name="postalcode" type="text" class="form-control input-sm" placeholder="Postal Code" value="<?php echo $aMoreParams['postalcode']; ?>" >
        </div></div>
        <div class="form-group search-button-group">
            <button type="submit" class="btn btn-primary btn-sm">Search</button>
            <?php if (CONST_Search_AreaPolygons) { ?>
                <input type="hidden" value="1" name="polygon_geojson" />
            <?php } ?>
            <input type="hidden" name="viewbox" value="<?php if (isset($aMoreParams['viewbox'])) echo ($aMoreParams['viewbox']); ?>" />
            <div class="checkbox-inline">
                <input type="checkbox" id="use_viewbox" <?php if (isset($aMoreParams['viewbox'])) echo "checked='checked'"; ?>>
                <label for="use_viewbox">apply viewbox</label>
            </div>
        </div>
    </form>
</div>

    <div id="content">

<?php if ($sQuery) { ?>

        <div id="searchresults" class="sidebar">
        <?php
            $i = 0;
            foreach($aSearchResults as $iResNum => $aResult)
            {

                echo '<div class="result" data-position=' . $i . '>';

                echo (isset($aResult['icon'])?'<img alt="icon" src="'.$aResult['icon'].'"/>':'');
                echo ' <span class="name">'.htmlspecialchars($aResult['name']).'</span>';
                // echo ' <span class="latlon">'.round($aResult['lat'],3).','.round($aResult['lon'],3).'</span>';
                // echo ' <span class="place_id">'.$aResult['place_id'].'</span>';
                if (isset($aResult['label']))
                    echo ' <span class="type">('.$aResult['label'].')</span>';
                else if ($aResult['type'] == 'yes')
                    echo ' <span class="type">('.ucwords(str_replace('_',' ',$aResult['class'])).')</span>';
                else
                    echo ' <span class="type">('.ucwords(str_replace('_',' ',$aResult['type'])).')</span>';
                echo detailsPermaLink($aResult, 'details', 'class="btn btn-default btn-xs details"');
                echo '</div>';
                $i = $i+1;
            }
            if (!empty($aSearchResults) && $sMoreURL)
            {
                echo '<div class="more"><a class="btn btn-primary" href="'.htmlentities($sMoreURL).'">Search for more results</a></div>';
            }
            else
            {
                echo '<div class="noresults">No search results found</div>';
            }

        ?>
        </div>

<?php } else { ?>

        <div id="intro" class="sidebar">
            <?php include(CONST_BasePath.'/lib/template/includes/introduction.php'); ?>
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
            'zoom' => CONST_Default_Zoom,
            'lat' => CONST_Default_Lat,
            'lon' => CONST_Default_Lon,
            'tile_url' => CONST_Map_Tile_URL,
            'tile_attribution' => CONST_Map_Tile_Attribution
        );
        echo 'var nominatim_map_init = ' . json_encode($aNominatimMapInit, JSON_PRETTY_PRINT) . ';';

        echo 'var nominatim_results = ' . json_encode($aSearchResults, JSON_PRETTY_PRINT) . ';'; 
    ?>
    </script>
    <?php include(CONST_BasePath.'/lib/template/includes/html-footer.php'); ?>

</body>
</html>
