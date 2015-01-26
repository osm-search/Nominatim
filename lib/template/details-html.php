<?php
	header("content-type: text/html; charset=UTF-8");
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>OpenStreetMap Nominatim: <?php echo $aPointDetails['localname'];?></title>
    <link href="css/details.css" rel="stylesheet" type="text/css" />
	<script src="js/OpenLayers.js" type="text/javascript"></script>
	<script src="js/tiles.js" type="text/javascript"></script>
	<script type="text/javascript">

		var map;

    function init() {
			map = new OpenLayers.Map ("map", {
                controls:[
										new OpenLayers.Control.Permalink(),
										new OpenLayers.Control.Navigation(),
										new OpenLayers.Control.PanZoomBar(),
										new OpenLayers.Control.MousePosition(),
										new OpenLayers.Control.Attribution()],
                maxExtent: new OpenLayers.Bounds(-20037508.34,-20037508.34,20037508.34,20037508.34),
                maxResolution: 156543.0399,
                numZoomLevels: 19,
                units: 'm',
                projection: new OpenLayers.Projection("EPSG:900913"),
                displayProjection: new OpenLayers.Projection("EPSG:4326")
            	} );
			map.addLayer(new OpenLayers.Layer.OSM.<?php echo CONST_Tile_Default;?>("Default"));

			var layer_style = OpenLayers.Util.extend({}, OpenLayers.Feature.Vector.style['default']);
			layer_style.fillOpacity = 0.2;
			layer_style.graphicOpacity = 0.2;

			vectorLayer = new OpenLayers.Layer.Vector("Points", {style: layer_style});
			map.addLayer(vectorLayer);

			var proj_EPSG4326 = new OpenLayers.Projection("EPSG:4326");
			var proj_map = map.getProjectionObject();

			freader = new OpenLayers.Format.WKT({
				'internalProjection': proj_map,
				'externalProjection': proj_EPSG4326
			});

			var feature = freader.read('<?php echo $aPointDetails['outlinestring'];?>');
			var featureCentre = freader.read('POINT(<?php echo $aPointDetails['lon'];?> <?php echo $aPointDetails['lat'];?>)');
			if (feature) {
				map.zoomToExtent(feature.geometry.getBounds());
				feature.style = {
					strokeColor: "#75ADFF",
					fillColor: "#F0F7FF",
					strokeWidth: <?php echo ($aPointDetails['isarea']=='t'?'2':'5');?>,
					strokeOpacity: 0.75,
					fillOpacity: 0.75,
					pointRadius: 50
				};

<?php if ($aPointDetails['isarea']=='t') {?>
				featureCentre.style = {
					strokeColor: "#008800",
					fillColor: "#338833",
					strokeWidth: <?php echo ($aPointDetails['isarea']=='t'?'2':'5');?>,
					strokeOpacity: 0.75,
					fillOpacity: 0.75,
					pointRadius: 8
				};
				vectorLayer.addFeatures([feature,featureCentre]);
<?php } else { ?>
				vectorLayer.addFeatures([feature]);
<?php } ?>
			}
		}
	</script>
  </head>
  <body onload="init();">
    <div id="map"></div>
<?php
	echo '<h1>';
	if ($aPointDetails['icon'])
	{
		echo '<img style="float:right;margin-right:40px;" src="'.CONST_Website_BaseURL.'images/mapicons/'.$aPointDetails['icon'].'.n.32.png'.'" alt="'.$aPointDetails['icon'].'" />';
	}
	echo $aPointDetails['localname']."</h1>\n";
	echo '<div class="locationdetails">';
	echo ' <div>Name: ';
	foreach($aPointDetails['aNames'] as $sKey => $sValue)
	{
		echo ' <div class="line"><span class="name">'.$sValue.'</span> ('.$sKey.')</div>';
	}
	echo ' </div>';
	echo ' <div>Type: <span class="type">'.$aPointDetails['class'].':'.$aPointDetails['type'].'</span></div>';
	echo ' <div>Last Updated: <span class="type">'.$aPointDetails['indexed_date'].'</span></div>';
	echo ' <div>Admin Level: <span class="adminlevel">'.$aPointDetails['admin_level'].'</span></div>';
	echo ' <div>Rank: <span class="rankaddress">'.$aPointDetails['rank_search_label'].'</span></div>';
	if ($aPointDetails['calculated_importance']) echo ' <div>Importance: <span class="rankaddress">'.$aPointDetails['calculated_importance'].($aPointDetails['importance']?'':' (estimated)').'</span></div>';
	echo ' <div>Coverage: <span class="area">'.($aPointDetails['isarea']=='t'?'Polygon':'Point').'</span></div>';
	echo ' <div>Centre Point: <span class="area">'.$aPointDetails['lat'].','.$aPointDetails['lon'].'</span></div>';
	$sOSMType = ($aPointDetails['osm_type'] == 'N'?'node':($aPointDetails['osm_type'] == 'W'?'way':($aPointDetails['osm_type'] == 'R'?'relation':'')));
	if ($sOSMType) echo ' <div>OSM: <span class="osm">'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aPointDetails['osm_id'].'">'.$aPointDetails['osm_id'].'</a></span></div>';
	if ($aPointDetails['wikipedia'])
	{
		list($sWikipediaLanguage,$sWikipediaArticle) = explode(':',$aPointDetails['wikipedia']);
		echo ' <div>Wikipedia Calculated: <span class="wikipedia"><a href="http://'.$sWikipediaLanguage.'.wikipedia.org/wiki/'.urlencode($sWikipediaArticle).'">'.$aPointDetails['wikipedia'].'</a></span></div>';
	}
	echo ' <div>Extra Tags: ';
	foreach($aPointDetails['aExtraTags'] as $sKey => $sValue)
	{
		echo ' <div class="line"><span class="name">'.$sValue.'</span> ('.$sKey.')</div>';
	}
	echo ' </div>';
	echo "</div>\n";

	echo "<h2>Address</h2>\n";
	echo '<div class="address">';
	$iPrevRank = 1000000;
	$sPrevLocalName = '';
	foreach($aAddressLines as $aAddressLine)
	{	
		$sOSMType = ($aAddressLine['osm_type'] == 'N'?'node':($aAddressLine['osm_type'] == 'W'?'way':($aAddressLine['osm_type'] == 'R'?'relation':'')));

		echo '<div class="line'.($aAddressLine['isaddress']=='f'?' notused':'').'">';
		if (!($iPrevRank<=$aAddressLine['rank_address'] || $sPrevLocalName == $aAddressLine['localname']))
		{
			$iPrevRank = $aAddressLine['rank_address'];
			$sPrevLocalName = $aAddressLine['localname'];
		}
		echo '<span class="name">'.(trim($aAddressLine['localname'])?$aAddressLine['localname']:'<span class="noname">No Name</span>').'</span>';
		echo ' (';
		echo '<span class="type"><span class="label">Type: </span>'.$aAddressLine['class'].':'.$aAddressLine['type'].'</span>';
		if ($sOSMType) echo ', <span class="osm">'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aAddressLine['osm_id'].'">'.$aAddressLine['osm_id'].'</a></span>';
		if (isset($aAddressLine['admin_level'])) echo ', <span class="adminlevel">'.$aAddressLine['admin_level'].'</span>';
		if (isset($aAddressLine['rank_search_label'])) echo ', <span class="rankaddress">'.$aAddressLine['rank_search_label'].'</span>';
//		echo ', <span class="area">'.($aAddressLine['fromarea']=='t'?'Polygon':'Point').'</span>';
		echo ', <span class="distance">'.$aAddressLine['distance'].'</span>';
		echo ' <a href="details.php?place_id='.$aAddressLine['place_id'].'">GOTO</a>';
		echo ')';
		echo "</div>\n";
	}
	echo "</div>\n";

	if ($aLinkedLines)
	{
		echo "<h2>Linked Places</h2>\n";
		echo '<div class="linked">';
		foreach($aLinkedLines as $aAddressLine)
		{	
			$sOSMType = ($aAddressLine['osm_type'] == 'N'?'node':($aAddressLine['osm_type'] == 'W'?'way':($aAddressLine['osm_type'] == 'R'?'relation':'')));

			echo '<div class="line">';
			echo '<span class="name">'.(trim($aAddressLine['localname'])?$aAddressLine['localname']:'<span class="noname">No Name</span>').'</span>';
			echo ' (';
			echo '<span class="type"><span class="label">Type: </span>'.$aAddressLine['class'].':'.$aAddressLine['type'].'</span>';
			if ($sOSMType) echo ', <span class="osm">'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aAddressLine['osm_id'].'">'.$aAddressLine['osm_id'].'</a></span>';
			echo ', <span class="adminlevel">'.$aAddressLine['admin_level'].'</span>';
			if (isset($aAddressLine['rank_search_label'])) echo ', <span class="rankaddress">'.$aAddressLine['rank_search_label'].'</span>';
//			echo ', <span class="area">'.($aAddressLine['fromarea']=='t'?'Polygon':'Point').'</span>';
			echo ', <span class="distance">'.$aAddressLine['distance'].'</span>';
			echo ' <a href="details.php?place_id='.$aAddressLine['place_id'].'">GOTO</a>';
			echo ')';
			echo "</div>\n";
		}
		echo "</div>\n";
	}

	if ($aPlaceSearchNameKeywords)
	{
		echo '<h2>Name Keywords</h2>';
		foreach($aPlaceSearchNameKeywords as $aRow)
		{
			echo '<div>'.$aRow['word_token']."</div>\n";
		}
	}

	if ($aPlaceSearchAddressKeywords)
	{
		echo '<h2>Address Keywords</h2>';
		foreach($aPlaceSearchAddressKeywords as $aRow)
		{
			echo '<div>'.($aRow['word_token'][0]==' '?'*':'').$aRow['word_token'].'('.$aRow['word_id'].')'."</div>\n";
		}
	}

	if (sizeof($aParentOfLines))
	{
		echo "<h2>Parent Of:</h2>\n<div>\n";

		$aGroupedAddressLines = array();
		foreach($aParentOfLines as $aAddressLine)
		{
			if ($aAddressLine['type'] == 'yes') $sType = $aAddressLine['class'];
			else $sType = $aAddressLine['type'];

			if (!isset($aGroupedAddressLines[$sType]))
				$aGroupedAddressLines[$sType] = array();
			$aGroupedAddressLines[$sType][] = $aAddressLine;
		}
		foreach($aGroupedAddressLines as $sGroupHeading => $aParentOfLines)
		{
			$sGroupHeading = ucwords($sGroupHeading);
			echo "<h3>$sGroupHeading</h3>\n";
		foreach($aParentOfLines as $aAddressLine)
		{
			$aAddressLine['localname'] = $aAddressLine['localname']?$aAddressLine['localname']:$aAddressLine['housenumber'];
			$sOSMType = ($aAddressLine['osm_type'] == 'N'?'node':($aAddressLine['osm_type'] == 'W'?'way':($aAddressLine['osm_type'] == 'R'?'relation':'')));
	
			echo '<div class="line">';
			echo '<span class="name">'.(trim($aAddressLine['localname'])?$aAddressLine['localname']:'<span class="noname">No Name</span>').'</span>';
			echo ' (';
			echo '<span class="area">'.($aAddressLine['isarea']=='t'?'Polygon':'Point').'</span>';
			echo ', <span class="distance">~'.(round($aAddressLine['distance']*69,1)).'&nbsp;miles</span>';
			if ($sOSMType) echo ', <span class="osm">'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aAddressLine['osm_id'].'">'.$aAddressLine['osm_id'].'</a></span>';
			echo ', <a href="details.php?place_id='.$aAddressLine['place_id'].'">GOTO</a>';
			echo ')';
			echo "</div>\n";
		}
		}
		if (sizeof($aParentOfLines) >= 500) {
			echo '<p>There are more child objects which are not shown.</p>';
		}
		echo '</div>';
	}

//	echo '<h2>Other Parts:</h2>';
//	echo '<h2>Linked To:</h2>';
?>

  </body>
</html>
