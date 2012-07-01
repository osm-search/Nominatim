<?php
	header("content-type: text/html; charset=UTF-8");
?>
<html>
<head>
	<title>OpenStreetMap Nominatim: Search</title>

	<base href="<?php echo CONST_Website_BaseURL;?>" />
	<link href="nominatim.xml" rel="search" title="Nominatim Search" type="application/opensearchdescription+xml" />

	<script src="js/OpenLayers.js"></script>
	<script src="js/tiles.js"></script>
	<script src="js/prototype-1.6.0.3.js"></script>

	<style>
* {-moz-box-sizing: border-box;}
body {
  margin:0px;
  padding:0px;
  overflow: hidden;
  background:#ffffff;
  height: 100%;
  font: normal 12px/15px arial,sans-serif;
}
#seachheader {
  position:absolute;
  z-index:5;
  top:0px;
  left:0px;
  width:100%;
  height:38px;
  background:#F0F7FF;
  border-bottom: 2px solid #75ADFF;
}
#q {
  width:300px;
}
#seachheaderfade1, #seachheaderfade2, #seachheaderfade3, #seachheaderfade4{
  position:absolute;
  z-index:4;
  top:0px;
  left:0px;
  width:100%;
  opacity: 0.15;
  filter: alpha(opacity = 15);
  background:#000000;
  border: 1px solid #000000;
}
#seachheaderfade1{
  height:39px;
}
#seachheaderfade2{
  height:40px;
}
#seachheaderfade3{
  height:41px;
}
#seachheaderfade4{
  height:42px;
}
#searchresultsfade1, #searchresultsfade2, #searchresultsfade3, #searchresultsfade4 {
  position:absolute;
  z-index:2;
  top:0px;
  left:200px;
  height: 100%;
  opacity: 0.2;
  filter: alpha(opacity = 20);
  background:#ffffff;
  border: 1px solid #ffffff;
}
#searchresultsfade1{
  width:1px;
}
#searchresultsfade2{
  width:2px;
}
#searchresultsfade3{
  width:3px;
}
#searchresultsfade4{
  width:4px;
}

#searchresults{
  position:absolute;
  z-index:3;
  top:41px;
  width:200px;
  height: 100%;
  background:#ffffff;
  border: 1px solid #ffffff;
  overflow: auto;
}
#map{
  position:absolute;
  z-index:1;
  top:38px;
  left:200px;
  width:100%;
  height:100%;
  background:#eee;
}
#report{
  position:absolute;
  z-index:2;
  top:38px;
  left:200px;
  width:100%;
  height:100%;
  background:#eee;
  font: normal 12px/15px arial,sans-serif;
  padding:20px;
}
#report table {
  margin-left:20px;
}
#report th {
  vertical-align:top;
  text-align:left;
}
#report td.button {
  text-align:right;
}
.result {
  margin:5px;
  margin-bottom:0px;
  padding:2px;
  padding-left:4px;
  padding-right:4px;
  border-radius: 5px;
  -moz-border-radius: 5px;
  -webkit-border-radius: 5px;
  background:#F0F7FF;
  border: 2px solid #D7E7FF;
  font: normal 12px/15px arial,sans-serif;
  cursor:pointer;
}
.result img{
  float:right;
}
.result .latlon{
  display: none;
}
.result .place_id{
  display: none;
}
.result .type{
  color: #999;
  text-align:center;
  font: normal 9px/10px arial,sans-serif;
  padding-top:4px;
}
.result .details, .result .details a{
  color: #999;
  text-align:center;
  font: normal 9px/10px arial,sans-serif;
  padding-top:4px;
}
.noresults{
  color: #000;
  text-align:center;
  font: normal 12px arial,sans-serif;
  padding-top:4px;
}
.more{
  color: #ccc;
  text-align:center;
  padding-top:4px;
}
.disclaimer{
  color: #ccc;
  text-align:center;
  font: normal 9px/10px arial,sans-serif;
  padding-top:4px;
}
form{
  margin:0px;
  padding:0px;
}
	</style>

	<script type="text/javascript">
        
		var map;

		function handleResize()
		{
			if ($('searchresults'))
			{
				$('map').style.width = (document.documentElement.clientWidth > 0?document.documentElement.clientWidth:document.documentElement.offsetWidth) - 200;
				$('report').style.width = (document.documentElement.clientWidth > 0?document.documentElement.clientWidth:document.documentElement.offsetWidth) - 200;
			}
			else
			{
				$('map').style.width = (document.documentElement.clientWidth > 0?document.documentElement.clientWidth:document.documentElement.offsetWidth) - 0;
				$('map').style.left = 0;
			}
			
			if ($('map')) $('map').style.height = (document.documentElement.clientHeight > 0?document.documentElement.clientHeight:document.documentElement.offsetHeight) - 38;
			if ($('searchresults')) $('searchresults').style.height = (document.documentElement.clientHeight > 0?document.documentElement.clientHeight:document.documentElement.offsetHeight) - 38;
			if ($('report')) $('report').style.height = (document.documentElement.clientHeight > 0?document.documentElement.clientHeight:document.documentElement.offsetHeight) - 38;
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

		function panToLatLonBoundingBox(lat,lon,minlat,maxlat,minlon,maxlon,points) {
		        var proj_EPSG4326 = new OpenLayers.Projection("EPSG:4326");
		        var proj_map = map.getProjectionObject();
                        map.zoomToExtent(new OpenLayers.Bounds(minlon,minlat,maxlon,maxlat).transform(proj_EPSG4326, proj_map));
			var lonLat = new OpenLayers.LonLat(lon, lat).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());
			map.panTo(lonLat, <?php echo $iZoom ?>);

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
			if (points)
			{
				points.each(function(p){
					pointList.push(new OpenLayers.Geometry.Point(p[0],p[1]));
					});
        	                var linearRing = new OpenLayers.Geometry.LinearRing(pointList).transform(proj_EPSG4326, proj_map);;
                	        var polygonFeature = new OpenLayers.Feature.Vector(new OpenLayers.Geometry.Polygon([linearRing]),null,style);
				vectorLayer.destroyFeatures();
                        	vectorLayer.addFeatures([polygonFeature]);
			}
			else
			{
				var lonLat = new OpenLayers.LonLat(lon, lat).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());
				var point = new OpenLayers.Geometry.Point(lonLat.lon, lonLat.lat);
				var pointFeature = new OpenLayers.Feature.Vector(point,null,style);
				vectorLayer.destroyFeatures();
				vectorLayer.addFeatures([pointFeature]);
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
										new OpenLayers.Control.MouseDefaults(),
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
			<table border="0" width="100%">
				<tr>
					<td valign="center" style="width:30px;"><img src="images/logo.gif"></td>
					<td valign="center" style="width:400px;"><input id="q" name="q" value="<?php echo htmlspecialchars($sQuery); 
?>" style="width:270px;"><input type="text" id="viewbox" style="width:130px;" name="viewbox"></td>
					<td style="width:80px;"><input type="submit" value="Search"></td>
<?php if (CONST_Search_AreaPolygons) { ?>					<td style="width:100px;"><input type="checkbox" value="1" name="polygon" <?php if ($bShowPolygons) echo "checked"; ?>> Highlight</td>
<td style="text-align:right;">Data: <?php echo $sDataDate; ?></td>
<td style="text-align:right;">
<a href="http://wiki.openstreetmap.org/wiki/Nominatim" target="_blank">Documentation</a> | <a href="http://wiki.openstreetmap.org/wiki/Nominatim/FAQ" 
target="_blank">FAQ</a></td>

<?php } ?>					<td style="text-align:right;"><?php if ($sQuery) { ?><input type="button" value="Report Problem With Results" onclick="$('report').style.visibility=($('report').style.visibility=='hidden'?'visible':'hidden')"><?php } ?></td>
				</tr>
			</table>
		</form>
	</div>

<?php
	if ($sQuery || sizeof($aSearchResults))
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
			if (isset($aResult['aPolyPoints'])) echo ', '.json_encode($aResult['aPolyPoints']);
			echo ');\'>';
		}
		elseif (isset($aResult['zoom']))
		{
			echo '<div class="result" onClick="panToLatLonZoom('.$aResult['lat'].', '.$aResult['lon'].', '.$aResult['zoom'].');">';
		}
		else
		{
			echo '<div class="result" onClick="panToLatLon('.$aResult['lat'].', '.$aResult['lon'].');">';
		}

		echo (isset($aResult['icon'])?'<img src="'.$aResult['icon'].'">':'');
		echo ' <span class="name">'.$aResult['name'].'</span>';
		echo ' <span class="latlon">'.round($aResult['lat'],3).','.round($aResult['lat'],3).'</span>';
		echo ' <span class="place_id">'.$aResult['place_id'].'</span>';
		if (isset($aResult['label']))
			echo ' <span class="type">('.$aResult['label'].')</span>';
		else
			echo ' <span class="type">('.ucwords(str_replace('_',' ',$aResult['type'])).')</span>';
		echo ' <span class="details">(<a href="details.php?place_id='.$aResult['place_id'].'">details</a>)</span>';
		echo '</div>';
	}
	if (sizeof($aSearchResults))
	{
		if ($sMoreURL)
		{
			echo '<div class="more"><a href="'.$sMoreURL.'">Search for more results</a></div>';
		}
	}
	else
	{
		echo '<div class="noresults">No search results found</div>';
	}

?>
		<div class="disclaimer">Addresses and postcodes are approximate
			<input type="button" value="Report Problem" onclick="$('report').style.visibility=($('report').style.visibility=='hidden'?'visible':'hidden')">
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
the component to 'nominatim'.  You can search for existing bug reports <a href="http://trac.openstreetmap.org/query?status=new&status=assigned&status=reopened&component=nominatim&order=priority">here</a>.</p>
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
			if (isset($aResult['aPolyPoints'])) echo ', '.javascript_renderData($aResult['aPolyPoints']);
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
