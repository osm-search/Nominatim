<?php
	header("content-type: text/html; charset=UTF-8");
?>
<html>
  <head>
    <title>OpenStreetMap Nominatim: <?php echo $aPointDetails['localname'];?></title>
    <style>
body {
	margin:0px;
	padding:16px;
  background:#ffffff;
  height: 100%;
  font: normal 12px/15px arial,sans-serif;
}
.line{
  margin-left:20px;
}
.name{
  font-weight: bold;
}
.notused{
  color:#ddd;
}
.noname{
  color:#800;
}
#map {
  width:500px;
  height:500px;
  border: 2px solid #666;
  float: right;
}
    </style>
	<script src="js/OpenLayers.js"></script>
	<script src="js/tiles.js"></script>
	<script type="text/javascript">
        
		var map;

    function init() {
			map = new OpenLayers.Map ("map", {
                controls:[
										new OpenLayers.Control.Permalink(),
										new OpenLayers.Control.Navigation(),
										new OpenLayers.Control.PanZoomBar(),
										new OpenLayers.Control.MouseDefaults(),
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

			var pointList = [];
			var style = {
				strokeColor: "#75ADFF",
				fillColor: "#F0F7FF",
				strokeWidth: 2,
				strokeOpacity: 0.75,
				fillOpacity: 0.75
			};
			var proj_EPSG4326 = new OpenLayers.Projection("EPSG:4326");
			var proj_map = map.getProjectionObject();
			var latlon;
<?php
if (isset($aPolyPoints))
{
	foreach($aPolyPoints as $aPolyPoint)
	{
		echo "                        pointList.push(new OpenLayers.Geometry.Point(".$aPolyPoint[1].",".$aPolyPoint[2]."));\n";
	}
}
?>
			var linearRing = new OpenLayers.Geometry.LinearRing(pointList).transform(proj_EPSG4326, proj_map);;
			var polygonFeature = new OpenLayers.Feature.Vector(new OpenLayers.Geometry.Polygon([linearRing]),null,style);
			vectorLayer.addFeatures([polygonFeature]);

			map.zoomToExtent(new OpenLayers.Bounds(<?php echo $aPointPolygon['minlon']?>, <?php echo $aPointPolygon['minlat']?>, <?php echo $aPointPolygon['maxlon']?>, <?php echo $aPointPolygon['maxlat']?>).transform(proj_EPSG4326, proj_map));
		}
		
	</script>
  </head>
  <body onload="init();">
    <div id="map"></div>
<?php
	echo '<h1>';
	if ($aPointDetails['icon'])
	{
		echo '<img style="float:right;margin-right:40px;" src="'.CONST_Website_BaseURL.'images/mapicons/'.$aPointDetails['icon'].'.n.32.png'.'">';
	}
	echo $aPointDetails['localname'].'</h1>';
	echo '<div class="locationdetails">';
	echo ' <div>Name: ';
	foreach($aPointDetails['aNames'] as $sKey => $sValue)
	{
		echo ' <div class="line"><span class="name">'.$sValue.'</span> ('.$sKey.')</div>';
	}
	echo ' </div>';
	echo ' <div>Type: <span class="type">'.$aPointDetails['class'].':'.$aPointDetails['type'].'</span></div>';
	echo ' <div>Admin Level: <span class="adminlevel">'.$aPointDetails['admin_level'].'</span></div>';
	echo ' <div>Rank: <span class="rankaddress">'.$aPointDetails['rank_search_label'].'</span></div>';
	if ($aPointDetails['importance']) echo ' <div>Importance: <span class="rankaddress">'.$aPointDetails['importance'].'</span></div>';
	echo ' <div>Coverage: <span class="area">'.($aPointDetails['isarea']=='t'?'Polygon':'Point').'</span></div>';
	$sOSMType = ($aPointDetails['osm_type'] == 'N'?'node':($aPointDetails['osm_type'] == 'W'?'way':($aPointDetails['osm_type'] == 'R'?'relation':'')));
	if ($sOSMType) echo ' <div>OSM: <span class="osm"><span class="label"></span>'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aPointDetails['osm_id'].'">'.$aPointDetails['osm_id'].'</a></span></div>';
	echo ' <div>Extra Tags: ';
	foreach($aPointDetails['aExtraTags'] as $sKey => $sValue)
	{
		echo ' <div class="line"><span class="name">'.$sValue.'</span> ('.$sKey.')</div>';
	}
	echo ' </div>';
	echo '</div>';

	echo '<h2>Address</h2>';
	echo '<div class=\"address\">';
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
		if ($sOSMType) echo ', <span class="osm"><span class="label"></span>'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aAddressLine['osm_id'].'">'.$aAddressLine['osm_id'].'</a></span>';
		echo ', <span class="adminlevel">'.$aAddressLine['admin_level'].'</span>';
		echo ', <span class="rankaddress">'.$aAddressLine['rank_search_label'].'</span>';
//		echo ', <span class="area">'.($aAddressLine['fromarea']=='t'?'Polygon':'Point').'</span>';
		echo ', <span class="distance">'.$aAddressLine['distance'].'</span>';
		echo ' <a href="details.php?place_id='.$aAddressLine['place_id'].'">GOTO</a>';
		echo ')';
		echo '</div>';
	}
	echo '</div>';

	if ($aLinkedLines)
	{
		echo '<h2>Linked Places</h2>';
		echo '<div class=\"linked\">';
		foreach($aLinkedLines as $aAddressLine)
		{	
			$sOSMType = ($aAddressLine['osm_type'] == 'N'?'node':($aAddressLine['osm_type'] == 'W'?'way':($aAddressLine['osm_type'] == 'R'?'relation':'')));

			echo '<div class="line">';
			echo '<span class="name">'.(trim($aAddressLine['localname'])?$aAddressLine['localname']:'<span class="noname">No Name</span>').'</span>';
			echo ' (';
			echo '<span class="type"><span class="label">Type: </span>'.$aAddressLine['class'].':'.$aAddressLine['type'].'</span>';
			if ($sOSMType) echo ', <span class="osm"><span class="label"></span>'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aAddressLine['osm_id'].'">'.$aAddressLine['osm_id'].'</a></span>';
			echo ', <span class="adminlevel">'.$aAddressLine['admin_level'].'</span>';
			echo ', <span class="rankaddress">'.$aAddressLine['rank_search_label'].'</span>';
//			echo ', <span class="area">'.($aAddressLine['fromarea']=='t'?'Polygon':'Point').'</span>';
			echo ', <span class="distance">'.$aAddressLine['distance'].'</span>';
			echo ' <a href="details.php?place_id='.$aAddressLine['place_id'].'">GOTO</a>';
			echo ')';
			echo '</div>';
		}
		echo '</div>';
	}

	if ($aPlaceSearchNameKeywords)
	{
		echo '<h2>Name Keywords</h2>';
		foreach($aPlaceSearchNameKeywords as $aRow)
		{
			echo '<div>'.$aRow['word_token'].'</div>';
		}
	}

	if ($aPlaceSearchAddressKeywords)
	{
		echo '<h2>Address Keywords</h2>';
		foreach($aPlaceSearchAddressKeywords as $aRow)
		{
			echo '<div>'.($aRow['word_token'][0]==' '?'*':'').$aRow['word_token'].'('.$aRow['word_id'].')'.'</div>';
		}
	}

	if (sizeof($aParentOfLines))
	{
		echo '<h2>Parent Of (named features only):</h2>';

		$aGroupedAddressLines = array();
		foreach($aParentOfLines as $aAddressLine)
		{
			if (!isset($aGroupedAddressLines[$aAddressLine['type']])) $aGroupedAddressLines[$aAddressLine['type']] = array();
			$aGroupedAddressLines[$aAddressLine['type']][] = $aAddressLine;
		}
		foreach($aGroupedAddressLines as $sGroupHeading => $aParentOfLines)
		{
			$sGroupHeading = ucwords($sGroupHeading);
			echo "<h3>$sGroupHeading</h3>";
		foreach($aParentOfLines as $aAddressLine)
		{
			$aAddressLine['localname'] = $aAddressLine['localname']?$aAddressLine['localname']:$aAddressLine['housenumber'];
			$sOSMType = ($aAddressLine['osm_type'] == 'N'?'node':($aAddressLine['osm_type'] == 'W'?'way':($aAddressLine['osm_type'] == 'R'?'relation':'')));
	
			echo '<div class="line">';
			echo '<span class="name">'.(trim($aAddressLine['localname'])?$aAddressLine['localname']:'<span class="noname">No Name</span>').'</span>';
			echo ' (';
//			echo '<span class="type"><span class="label">Type: </span>'.$aAddressLine['class'].':'.$aAddressLine['type'].'</span>';
//			echo ', <span class="adminlevel">'.$aAddressLine['admin_level'].'</span>';
//			echo ', <span class="rankaddress">'.$aAddressLine['rank_address'].'</span>';
			echo '<span class="area">'.($aAddressLine['isarea']=='t'?'Polygon':'Point').'</span>';
			echo ', <span class="distance">~'.(round($aAddressLine['distance']*69,1)).'&nbsp;miles</span>';
			if ($sOSMType) echo ', <span class="osm"><span class="label"></span>'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aAddressLine['osm_id'].'">'.$aAddressLine['osm_id'].'</a></span>';
			echo ', <a href="details.php?place_id='.$aAddressLine['place_id'].'">GOTO</a>';
			echo ')';
			echo '</div>';
		}
		}
		echo '</div>';
	}

//	echo '<h2>Other Parts:</h2>';
//	echo '<h2>Linked To:</h2>';
?>

  </body>
</html>
