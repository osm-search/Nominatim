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
			<input name="lat" type="text" class="form-control input-sm" placeholder="latitude"  value="<?php echo htmlspecialchars($_GET['lat']); ?>" >
			<input name="lon" type="text" class="form-control input-sm" placeholder="longitude" value="<?php echo htmlspecialchars($_GET['lon']); ?>" >
			max zoom

			<select name="zoom" class="form-control input-sm" value="<?php echo htmlspecialchars($_GET['zoom']); ?>">
				<option value="" <?php echo $_GET['zoom']==''?'selected':'' ?> >--</option>
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
						$bSel = isset($_GET['zoom']) && ($_GET['zoom'] == (string)$iZoomLevel);
						echo '<option value="'.$iZoomLevel.'"'.($bSel?'selected':'').'>'.$iZoomLevel.' '.$sLabel.'</option>'."\n";
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

<?php if ($aPlace) { ?>

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
			echo ' <a class="btn btn-default btn-xs details" href="details.php?place_id='.$aResult['place_id'].'&addressdetails=1&linkedplaces=1&childplaces=1">details</a>';
			echo '</div>';
		?>
		</div>

<?php } else { ?>

		<div id="intro" class="sidebar">
			Search for coordinates or click anywhere on the map.
		</div>

<?php } ?>

		<div id="map-wrapper">
			<div id="map-position"></div>
			<div id="map"></div>
		</div>

	</div> <!-- /content -->







	<script type="text/javascript">
	<?php

		$aNominatimMapInit = array(
			'zoom' => isset($_GET['zoom']) ? htmlspecialchars($_GET['zoom']) : CONST_Default_Zoom,
			'lat'  => isset($_GET['lat']) ? htmlspecialchars($_GET['lat']) : CONST_Default_Lat,
			'lon'  => isset($_GET['lon']) ? htmlspecialchars($_GET['lon']) : CONST_Default_Lon,
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
