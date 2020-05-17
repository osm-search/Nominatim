<?php
    header("content-type: text/html; charset=UTF-8");
?>
<?php include(CONST_BasePath.'/lib/template/includes/html-header.php'); ?>
    <link href="css/common.css" rel="stylesheet" type="text/css" />
    <link href="css/details.css" rel="stylesheet" type="text/css" />
</head>


<?php

    function headline($sTitle)
    {
        echo "<tr class='all-columns'><td colspan='6'><h2>".$sTitle."</h2></td></tr>\n";
    }

    function headline3($sTitle)
    {
        echo "<tr class='all-columns'><td colspan='6'><h3>".$sTitle."</h3></td></tr>\n";
    }


    function format_distance($fDistance, $bInMeters = false)
    {
        if ($bInMeters) {
            // $fDistance is in meters
            if ($fDistance < 1) {
                return '0';
            }
            elseif ($fDistance < 1000) {
                return '<abbr class="distance" title="'.$fDistance.' meters">~'.(round($fDistance,0)).' m</abbr>';
            }
            else {
                return '<abbr class="distance" title="'.$fDistance.' meters">~'.(round($fDistance/1000,1)).' km</abbr>';
            }
        } else {
            if ($fDistance == 0) {
                return '0';
            } else {
                return '<abbr class="distance" title="spheric distance '.$fDistance.'">'.(round($fDistance,4)).'</abbr>';
            }
        }
    }

    function kv($sKey,$sValue)
    {
        echo ' <tr><td>' . $sKey . '</td><td>'.$sValue.'</td></tr>'. "\n";
    }


    function hash_to_subtable($aAssociatedList)
    {
        $sHTML = '';
        foreach ($aAssociatedList as $sKey => $sValue) {
            $sHTML = $sHTML.' <div class="line"><span class="name">'.$sValue.'</span> ('.$sKey.')</div>'."\n";
        }
        return $sHTML;
    }

    function map_icon($aPlace)
    {
        $sIcon = Nominatim\ClassTypes\getIconFile($aPlace);
        if (isset($sIcon)) {
            $sLabel = Nominatim\ClassTypes\getIcon($aPlace);
            echo '<img id="mapicon" src="'.$sIcon.'" alt="'.$sLabel.'" />';
        }
    }


    function _one_row($aAddressLine, $bDistanceInMeters = false){
        $bNotUsed = isset($aAddressLine['isaddress']) && !$aAddressLine['isaddress'];

        echo '<tr class="' . ($bNotUsed?'notused':'') . '">'."\n";
        echo '  <td class="name">'.(trim($aAddressLine['localname'])!==null?$aAddressLine['localname']:'<span class="noname">No Name</span>')."</td>\n";
        echo '  <td>' . $aAddressLine['class'].':'.$aAddressLine['type'];
        if ($aAddressLine['type'] == 'administrative'
            && isset($aAddressLine['place_type']))
        {
            echo '('.$aAddressLine['place_type'].')';
        }
        echo "</td>\n";
        echo '  <td>' . osmLink($aAddressLine) . "</td>\n";
        echo '  <td>' . (isset($aAddressLine['rank_address']) ? $aAddressLine['rank_address'] : '') . "</td>\n";
        echo '  <td>' . ($aAddressLine['admin_level'] < 15 ? $aAddressLine['admin_level'] : '') . "</td>\n";
        echo '  <td>' . format_distance($aAddressLine['distance'], $bDistanceInMeters)."</td>\n";
        echo '  <td>' . detailsPermaLink($aAddressLine,'details &gt;') . "</td>\n";
        echo "</tr>\n";
    }

    function _one_keyword_row($keyword_token,$word_id){
        echo "<tr>\n";
        echo '<td>';
        // mark partial tokens (those starting with a space) with a star for readability
        echo ($keyword_token[0]==' '?'*':'');
        echo $keyword_token;
        if (isset($word_id))
        {
            echo '</td><td>word id: '.$word_id;
        }
        echo "</td></tr>\n";
    }

?>



<body id="details-page">
    <?php include(CONST_BasePath.'/lib/template/includes/html-top-navigation.php'); ?>
    <div class="container">
        <div class="row">
            <div class="col-sm-10">
                <h1>
                    <?php echo $aPointDetails['localname'] ?>
                </h1>
            </div>
            <div class="col-sm-2 text-right">
                <?php map_icon($aPointDetails) ?>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6">
                <table id="locationdetails" class="table table-striped">

                <?php

                    kv('Name'            , hash_to_subtable($aPointDetails['aNames']) );
                    kv('Type'            , $aPointDetails['class'].':'.$aPointDetails['type'] );
                    kv('Last Updated'    , (new DateTime('@'.$aPointDetails['indexed_epoch']))->format(DateTime::RFC822) );
                    kv('Admin Level'     , $aPointDetails['admin_level'] );
                    kv('Rank'            , $aPointDetails['rank_search_label'] );
                    if ($aPointDetails['calculated_importance']) {
                        kv('Importance'    , $aPointDetails['calculated_importance'].($aPointDetails['importance']?'':' (estimated)') );
                    }
                    kv('Coverage'        , ($aPointDetails['isarea']?'Polygon':'Point') );
                    kv('Centre Point'    , $aPointDetails['lat'].','.$aPointDetails['lon'] );
                    kv('OSM'             , osmLink($aPointDetails) );
                    kv('Place Id (<a href="https://nominatim.org/release-docs/develop/api/Output/#place_id-is-not-a-persistent-id">on this server</a>)'
                                         , $aPointDetails['place_id'] );
                    if ($aPointDetails['wikipedia'])
                    {
                        kv('Wikipedia Calculated' , wikipediaLink($aPointDetails) );
                    }

                    kv('Computed Postcode', $aPointDetails['postcode']);
                    kv('Address Tags'    , hash_to_subtable($aPointDetails['aAddressTags']) );
                    kv('Extra Tags'      , hash_to_subtable($aPointDetails['aExtraTags']) );

                ?>

                </table>
            </div>

            <div class="col-md-6">
                <div id="map"></div>
            </div>

        </div>
        <div class="row">
            <div class="col-md-12">

            <h2>Address</h2>

            <table id="address" class="table table-striped table-responsive">
                <thead>
                    <tr>
                      <td>Local name</td>
                      <td>Type</td>
                      <td>OSM</td>
                      <td>Address rank</td>
                      <td>Admin level</td>
                      <td>Distance</td>
                      <td></td>
                    </tr>
                </thead>
                <tbody>

                <?php
                    foreach ($aAddressLines as $aAddressLine) {
                        _one_row($aAddressLine);
                    }
                ?>


<?php

    if ($aLinkedLines)
    {
        headline('Linked Places');
        foreach ($aLinkedLines as $aAddressLine) {
            _one_row($aAddressLine, true);
        }
    }

    if ($bIncludeKeywords)
    {
        headline('Name Keywords');
        if ($aPlaceSearchNameKeywords) {
            foreach ($aPlaceSearchNameKeywords as $aRow) {
                _one_keyword_row($aRow['word_token'], $aRow['word_id']);
            }
        }

        headline('Address Keywords');
        if ($aPlaceSearchAddressKeywords) {
            foreach ($aPlaceSearchAddressKeywords as $aRow) {
                _one_keyword_row($aRow['word_token'], $aRow['word_id']);
            }
        }
    }

    if (!empty($aHierarchyLines))
    {
        headline('Parent Of');

        $aGroupedAddressLines = array();
        foreach ($aHierarchyLines as $aAddressLine) {
            if ($aAddressLine['type'] == 'yes') $sType = $aAddressLine['class'];
            else $sType = $aAddressLine['type'];

            if (!isset($aGroupedAddressLines[$sType]))
                $aGroupedAddressLines[$sType] = array();
            $aGroupedAddressLines[$sType][] = $aAddressLine;
        }
        foreach ($aGroupedAddressLines as $sGroupHeading => $aHierarchyLines) {
            $sGroupHeading = ucwords($sGroupHeading);
            headline3($sGroupHeading);

            foreach ($aHierarchyLines as $aAddressLine) {
                _one_row($aAddressLine, true);
            }
        }
        if (count($aHierarchyLines) >= 500) {
            echo '<p>There are more child objects which are not shown.</p>';
        }
    }

    echo "</table>\n";
?>

            </div>
        </div>
    </div>

    <script type="text/javascript">
    <?php

        $aNominatimMapInit = array(
          'tile_url' => $sTileURL,
          'tile_attribution' => $sTileAttribution
        );
        echo 'var nominatim_map_init = ' . json_encode($aNominatimMapInit, JSON_PRETTY_PRINT) . ';';

        $aPlace = array(
                'asgeojson' => $aPointDetails['asgeojson'],
                'lon' => $aPointDetails['lon'],
                'lat' => $aPointDetails['lat'],
        );
        echo 'var nominatim_result = ' . json_encode($aPlace, JSON_PRETTY_PRINT) . ';';


    ?>
    </script>



    <?php include(CONST_BasePath.'/lib/template/includes/html-footer.php'); ?>
</body>
</html>
