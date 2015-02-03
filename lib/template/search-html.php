<?php
	header("content-type: text/html; charset=UTF-8");
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
	<title>OpenStreetMap Nominatim: Search</title>

	<base href="<?php echo CONST_Website_BaseURL;?>" />
	<link href="nominatim.xml" rel="search" title="Nominatim Search" type="application/opensearchdescription+xml" />
	<link href="css/search.css" rel="stylesheet" type="text/css" />

	<script src="js/OpenLayers.js" type="text/javascript"></script>
	<script src="js/tiles.js" type="text/javascript"></script>
	<script src="js/prototype-1.6.0.3.js" type="text/javascript"></script>

	<script type="text/javascript">

		var map;

		function handleResize()
		{
			if ($('searchresults'))
			{
				var viewwidth = ((document.documentElement.clientWidth > 0?document.documentElement.clientWidth:document.documentElement.offsetWidth) - 200) + 'px';
				$('map').style.width = viewwidth;
				$('report').style.width = viewwidth;
			}
			else
			{
				$('map').style.width = ((document.documentElement.clientWidth > 0?document.documentElement.clientWidth:document.documentElement.offsetWidth) - 0) + 'px';
				$('map').style.left = '0px';
			}

			if ($('map')) $('map').style.height = ((document.documentElement.clientHeight > 0?document.documentElement.clientHeight:document.documentElement.offsetHeight) - 38) + 'px';
			if ($('searchresults')) $('searchresults').style.height = ((document.documentElement.clientHeight > 0?document.documentElement.clientHeight:document.documentElement.offsetHeight) - 38) + 'px';
			if ($('report')) $('report').style.height = ((document.documentElement.clientHeight > 0?document.documentElement.clientHeight:document.documentElement.offsetHeight) - 38) + 'px';
		}
		window.onresize = handleResize;

		function panToLatLon(lat,lon) {
			var lonLat = new OpenLayers.LonLat(lon, lat).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());
			map.panTo(lonLat, <?php echo $iZoom ?>);
		}

		function panToLatLonZoom(lat, lon, zoom) {
			var lonLat = new OpenLayers.LonLat(lon, lat).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());
			if (zoom != map.getZoom())
				map.setCenter(lonLat, zoom);
			else
				map.panTo(lonLat, 10);
		}

		function panToLatLonBoundingBox(lat,lon,minlat,maxlat,minlon,maxlon,wkt) {
			vectorLayer.destroyFeatures();
			var proj_EPSG4326 = new OpenLayers.Projection("EPSG:4326");
			var proj_map = map.getProjectionObject();
			map.zoomToExtent(new OpenLayers.Bounds(minlon,minlat,maxlon,maxlat).transform(proj_EPSG4326, proj_map));
			var lonLat = new OpenLayers.LonLat(lon, lat).transform(proj_EPSG4326, proj_map);
			map.panTo(lonLat, <?php echo $iZoom ?>);

			if (wkt)
			{
				var freader = new OpenLayers.Format.WKT({
						'internalProjection': proj_map,
						'externalProjection': proj_EPSG4326
						});

				var feature = freader.read(wkt);
				if (feature)
				{
					feature.style = {
							strokeColor: "#75ADFF",
							fillColor: "#F0F7FF",
							strokeWidth: 2,
							strokeOpacity: 0.75,
							fillOpacity: 0.75,
							pointRadius: 100
                    };
					vectorLayer.addFeatures([feature]);
				}
			}
		}

		function round(v,n)
		{
			n = Math.pow(10,n);
			return Math.round(v*n)/n;
		}
		function floor(v,n)
		{
			n = Math.pow(10,n);
			return Math.floor(v*n)/n;
		}
		function ceil(v,n)
		{
			n = Math.pow(10,n);
			return Math.ceil(v*n)/n;
		}

		function mapEventMove() {
			var proj = new OpenLayers.Projection("EPSG:4326");
			var bounds = map.getExtent();
			bounds = bounds.transform(map.getProjectionObject(), proj);
			$('viewbox').value = floor(bounds.left,2)+','+ceil(bounds.top,2)+','+ceil(bounds.right,2)+','+floor(bounds.bottom,2);
		}

    function init() {
			handleResize();
			map = new OpenLayers.Map ("map", {
                controls:[
										new OpenLayers.Control.Navigation(),
										new OpenLayers.Control.PanZoomBar(),
										new OpenLayers.Control.MousePosition(),
										new OpenLayers.Control.Attribution()],
                maxExtent: new OpenLayers.Bounds(-20037508.34,-20037508.34,20037508.34,20037508.34),
                maxResolution: 156543.0399,
                numZoomLevels: 19,
                units: 'm',
                projection: new OpenLayers.Projection("EPSG:900913"),
                displayProjection: new OpenLayers.Projection("EPSG:4326"),
                eventListeners: {
									"moveend": mapEventMove
								}
            	} );
			map.addLayer(new OpenLayers.Layer.OSM.<?php echo CONST_Tile_Default;?>("Default"));

			var layer_style = OpenLayers.Util.extend({}, OpenLayers.Feature.Vector.style['default']);
			layer_style.fillOpacity = 0.2;
			layer_style.graphicOpacity = 1;
			vectorLayer = new OpenLayers.Layer.Vector("Points", {style: layer_style});
			map.addLayer(vectorLayer);
			
//			var lonLat = new OpenLayers.LonLat(<?php echo $fLon ?>, <?php echo $fLat ?>).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());
//			map.setCenter (lonLat, <?php echo $iZoom ?>);
		}

		function setfocus(field_id) { 
			$(field_id).focus() 
		} 
		
	</script>
</head>

<body onload="setfocus('q');">

	<div id="seachheaderfade1"></div><div id="seachheaderfade2"></div><div id="seachheaderfade3"></div><div id="seachheaderfade4"></div>

	<div id="seachheader">
		<form accept-charset="UTF-8" action="<?php echo CONST_Website_BaseURL; ?>search.php" method="get">
			<table border="0" width="100%" summary="header">
				<tr>
					<td valign="middle" style="width:30px;"><img alt="logo" src="images/logo.gif" /></td>
					<td valign="middle" style="width:400px;"><input id="q" name="q" value="<?php echo htmlspecialchars($sQuery); 
?>" style="width:270px;" /><input type="text" id="viewbox" style="width:120px;" name="viewbox" /></td>
					<td style="width:80px;"><input type="submit" value="Search"/></td>
<?php if (CONST_Search_AreaPolygons) { ?>					<td style="width:100px;"><input type="checkbox" value="1" name="polygon" <?php if ($bAsText) echo "checked='checked'"; ?>/> Highlight</td>
<td style="text-align:right;">Data: <?php echo $sDataDate; ?></td>
<td style="text-align:right;">
<a href="http://wiki.openstreetmap.org/wiki/Nominatim" target="_blank">Documentation</a> | <a href="http://wiki.openstreetmap.org/wiki/Nominatim/FAQ" 
target="_blank">FAQ</a></td>

<?php } ?>					<td style="text-align:right;"><?php if ($sQuery) { ?><input type="button" value="Report Problem With Results" onclick="$('report').style.visibility=($('report').style.visibility=='hidden'?'visible':'hidden')"/><?php } ?></td>
				</tr>
			</table>
		</form>
	</div>

<?php
	if ($sQuery)
	{
?>
	<div id="searchresultsfade1"></div><div id="searchresultsfade2"></div><div id="searchresultsfade3"></div><div id="searchresultsfade4"></div>
	<div id="searchresults">
<?php
	if ($sSuggestionURL)
	{
		echo '<div class="more"><b>Suggest: </b><a href="'.$sSuggestionURL.'"><b>'.$sSuggestion.'</b></a></div>';
	}
	foreach($aSearchResults as $iResNum => $aResult)
	{
		if ($aResult['aBoundingBox'])
		{
			echo '<div class="result" onClick=\'panToLatLonBoundingBox('.$aResult['lat'].', '.$aResult['lon'];
			echo ', '.$aResult['aBoundingBox'][0];
			echo ', '.$aResult['aBoundingBox'][1];
			echo ', '.$aResult['aBoundingBox'][2];
			echo ', '.$aResult['aBoundingBox'][3];
			if (isset($aResult['astext'])) echo ', "'.$aResult['astext'].'"';
			echo ");'>\n";
		}
		elseif (isset($aResult['zoom']))
		{
			echo '<div class="result" onClick="panToLatLonZoom('.$aResult['lat'].', '.$aResult['lon'].', '.$aResult['zoom'].');">';
		}
		else
		{
			echo '<div class="result" onClick="panToLatLon('.$aResult['lat'].', '.$aResult['lon'].');">';
		}

		echo (isset($aResult['icon'])?'<img alt="icon" src="'.$aResult['icon'].'"/>':'');
		echo ' <span class="name">'.htmlspecialchars($aResult['name']).'</span>';
		echo ' <span class="latlon">'.round($aResult['lat'],3).','.round($aResult['lon'],3).'</span>';
		echo ' <span class="place_id">'.$aResult['place_id'].'</span>';
		if (isset($aResult['label']))
			echo ' <span class="type">('.$aResult['label'].')</span>';
		else if ($aResult['type'] == 'yes')
			echo ' <span class="type">('.ucwords(str_replace('_',' ',$aResult['class'])).')</span>';
		else
			echo ' <span class="type">('.ucwords(str_replace('_',' ',$aResult['type'])).')</span>';
		echo ' <span class="details">(<a href="details.php?place_id='.$aResult['place_id'].'">details</a>)</span>';
		echo '</div>';
	}
	if (sizeof($aSearchResults))
	{
		if ($sMoreURL)
		{
			echo '<div class="more"><a href="'.htmlentities($sMoreURL).'">Search for more results</a></div>';
		}
	}
	else
	{
		echo '<div class="noresults">No search results found</div>';
	}

?>
		<div class="disclaimer">Addresses and postcodes are approximate
			<input type="button" value="Report Problem" onclick="$('report').style.visibility=($('report').style.visibility=='hidden'?'visible':'hidden')"/>
		</div>
	</div>
<?php
}
?>

	<div id="map"></div>
	<div id="report" style="visibility:hidden;"><div style="width:600px;margin:auto;margin-top:60px;">
		<h2>Report a problem</h2>
		<p>Before reporting problems please read the <a href="http://wiki.openstreetmap.org/wiki/Nominatim">user documentation</a> and <a 
href="http://wiki.openstreetmap.org/wiki/Nominatim/FAQ">FAQ</a>.  If your problem relates to the address of a particular search result please use the 'details' link 
to check how the address was generated before reporting a problem.</p>
		<p>Please use <a href="http://trac.openstreetmap.org/newticket?component=nominatim">trac.openstreetmap.org</a> to report problems 
making sure to set 
the component to 'nominatim'.  You can search for existing bug reports <a href="http://trac.openstreetmap.org/query?status=new&amp;status=assigned&amp;status=reopened&amp;component=nominatim&amp;order=priority">here</a>.</p>
		<p>Please ensure that you include a full description of the problem, including the search query that you used, the problem with the result and, if 
the problem relates to missing data, the osm id of the item that is missing.  Problems that contain enough detail are likely to get looked at before ones that 
require significant research!</p>
		</div>

<!--
 		<p>Please use this form to report problems with the search results.  Of particular interest are items missing, but please also use this form to 
report any other problems.</p>
 		<p>If your problem relates to the address of a particular search result please use the 'details' link to check how the address was generated before 
reporting a problem.</p>
 		<p>If you are reporting a missing result please (if possible) include the OSM ID of the item you where expecting (i.e. node 422162)</p>
		<form method="post">
		<table>
		<tr><th>Your Query:</th><td><input type="hidden" name="report:query" value="<?php echo htmlspecialchars($sQuery); ?>" style="width:500px;"><?php echo htmlspecialchars($sQuery); ?></td></tr>
		<tr><th>Your Email Address(opt):</th><td><input type="text" name="report:email" value="" style="width:500px;"></td></tr>
		<tr><th>Description of Problem:</th><td><textarea name="report:description" style="width:500px;height:200px;"></textarea></td></tr>
		<tr><td colspan="2" class="button"><input type="button" value="Cancel" onclick="$('report').style.visibility='hidden'"><input type="submit" value="Report"></td></tr>
		</table>
		</form>
		<h2>Known Problems</h2>
		<ul>
		<li>Countries where missed out of the index</li>
		<li>Area Polygons relate to the search area - not the address area which would make more sense</li>
		</ul>
-->
	</div>

	<script type="text/javascript">
init();
<?php
	foreach($aSearchResults as $iResNum => $aResult)
	{
		if ($aResult['aBoundingBox'])
		{
			echo 'panToLatLonBoundingBox('.$aResult['lat'].', '.$aResult['lon'];
			echo ', '.$aResult['aBoundingBox'][0];
			echo ', '.$aResult['aBoundingBox'][1];
			echo ', '.$aResult['aBoundingBox'][2];
			echo ', '.$aResult['aBoundingBox'][3];
			if (isset($aResult['astext'])) echo ", '".$aResult['astext']."'";
			echo ');'."\n";
		}
		else
		{
			echo 'panToLatLonZoom('.$fLat.', '.$fLon.', '.$iZoom.');'."\n";
		}
		break;
	}
	if (!sizeof($aSearchResults))
	{
		echo 'panToLatLonZoom('.$fLat.', '.$fLon.', '.$iZoom.');'."\n";
	}
?>
</script>
</body>

</html>
