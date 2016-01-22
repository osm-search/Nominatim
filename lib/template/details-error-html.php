<?php
	header("content-type: text/html; charset=UTF-8");
?>
<?php include(CONST_BasePath.'/lib/template/includes/html-header.php'); ?>
	<link href="css/common.css" rel="stylesheet" type="text/css" />
	<link href="css/details.css" rel="stylesheet" type="text/css" />
</head>


<?php

	function osm_link($aFeature)
	{
		$sOSMType = ($aFeature['osm_type'] == 'N'?'node':($aFeature['osm_type'] == 'W'?'way':($aFeature['osm_type'] == 'R'?'relation':'')));
		if ($sOSMType) {
			return '<a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aFeature['osm_id'].'">'.$sOSMType.' '.$aFeature['osm_id'].'</a>';
		}
		return '';
	}

	function osm_map_url($aFeature)
	{
		$sLon = $aFeature['error_x'];
		$sLat = $aFeature['error_y'];

		if (isset($sLat))
		{
			$sOSMType = ($aFeature['osm_type'] == 'N'?'node':($aFeature['osm_type'] == 'W'?'way':($aFeature['osm_type'] == 'R'?'relation':'')));
			if ($sOSMType)
			{
				return "http://www.openstreetmap.org/?lat=".$sLat."&lon=".$sLon."&zoom=18&layers=M&".$sOSMType."=".$aFeature['osm_id'];
			}
		}
		return '';
	}

	function josm_edit_url($aFeature)
	{
		$fWidth = 0.0002;
		$sLon = $aFeature['error_x'];
		$sLat = $aFeature['error_y'];

		if (isset($sLat))
		{
			return "http://localhost:8111/load_and_zoom?left=".($sLon-$fWidth)."&right=".($sLon+$fWidth)."&top=".($sLat+$fWidth)."&bottom=".($sLat-$fWidth);
		}

		$sOSMType = ($aFeature['osm_type'] == 'N'?'node':($aFeature['osm_type'] == 'W'?'way':($aFeature['osm_type'] == 'R'?'relation':'')));
		if ($sOSMType)
		{
			return 'http://localhost:8111/import?url=http://www.openstreetmap.org/api/0.6/'.$sOSMType.'/'.$aFeature['osm_id'].'/full';
			// Should be better to load by object id - but this doesn't seem to zoom correctly
			// return " <a href=\"http://localhost:8111/load_object?new_layer=true&objects=".strtolower($aFeature['osm_type']).$sOSMID."\" target=\"josm\">Remote Control (JOSM / Merkaartor)</a>";
		}
		return '';
	}

	function potlach_edit_url($aFeature)
	{
		$fWidth = 0.0002;
		$sLat = $aFeature['error_y'];
		$sLon = $aFeature['error_x'];

		if (isset($sLat))
		{
			return "http://www.openstreetmap.org/edit?editor=potlatch2&bbox=".($sLon-$fWidth).",".($sLat-$fWidth).",".($sLon+$fWidth).",".($sLat+$fWidth);
		}
		return '';
	}



?>

<body id="details-page">
	<div class="container">
		<div class="row">
			<div class="col-md-6">


				<h1><?php echo $aPointDetails['localname'] ?></h1>
				<div class="locationdetails">
					<h2 class="bg-danger">This object has an invalid geometry.</h2>

					<div>
						Type: <span class="type"><?php echo $aPointDetails['class'].':'.$aPointDetails['type'];?></span>
					</div>

					<div>
						OSM: <span class="label"><?php echo osm_link($aPointDetails); ?><span>
					</div>


					<h4>Error</h4>
					<p>
						<?php echo $aPointDetails['errormessage']?$aPointDetails['errormessage']:'unknown'; ?>
					</p>
					<?php if (osm_map_url($aPointDetails)) { ?>
						<a href="<?php echo osm_map_url($aPointDetails); ?>">view on osm.org</a>
					<?php } ?>

					<h4>Edit</h4>
					<ul>
					<?php if (josm_edit_url($aPointDetails)) { ?>
							<li><a href="<?php echo josm_edit_url($aPointDetails); ?>" target="josm">Remote Control (JOSM / Merkaartor)</a></li>
					<?php } ?>
					<?php if (potlach_edit_url($aPointDetails)) { ?>
							<li><a href="<?php echo potlach_edit_url($aPointDetails); ?>" target="potlatch2">Potlatch 2</a></li>
					<?php } ?>
					</ul>
			</div>
		</div>
		<div class="col-md-6">
			<div id="map"></div>
		</div>

	</div>


	<script type="text/javascript">

		var nominatim_result = {
			outlinestring: '<?php echo $aPointDetails['outlinestring'];?>',
			lon: <?php echo isset($aPointDetails['error_x']) ? $aPointDetails['error_x'] : 0; ?>,
			lat: <?php echo isset($aPointDetails['error_y']) ? $aPointDetails['error_y'] : 0; ?>
		};

	</script>


	<?php include(CONST_BasePath.'/lib/template/includes/html-footer.php'); ?>
	</body>
</html>