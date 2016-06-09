<?php
	header("content-type: text/html; charset=UTF-8");
?>
<?php include(CONST_BasePath.'/lib/template/includes/html-header.php'); ?>
	<link href="css/common.css" rel="stylesheet" type="text/css" />
	<link href="css/search.css" rel="stylesheet" type="text/css" />
</head>

<body id="search-page">

	<?php include(CONST_BasePath.'/lib/template/includes/html-top-navigation.php'); ?>

	<form class="form-inline" role="search" accept-charset="UTF-8" action="<?php echo CONST_Website_BaseURL; ?>search.php">
		<div class="form-group">
			<input id="q" name="q" type="text" class="form-control input-sm" placeholder="Search" value="<?php echo htmlspecialchars($sQuery); ?>" >
		</div>
		<div class="form-group search-button-group">
			<button type="submit" class="btn btn-primary btn-sm">Search</button>
			<?php if (CONST_Search_AreaPolygons) { ?>
				<!-- <input type="checkbox" value="1" name="polygon" <?php if ($bAsText) echo "checked='checked'"; ?>/> Highlight -->
				<input type="hidden" value="1" name="polygon" />
			<?php } ?>
			<input type="hidden" name="viewbox" value="<?php echo $sViewBox; ?>" />
			<div class="checkbox-inline">
				<label>
					<input type="checkbox" id="use_viewbox" <?php if ($sViewBox) echo "checked='checked'"; ?>>
					apply viewbox
				</label>
			</div>
		</div>
		<div class="search-type-link">
			<a href="<?php echo CONST_Website_BaseURL; ?>reverse.php?format=html">reverse search</a>
		</div>
	</form>


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
				echo ' <a class="btn btn-default btn-xs details" href="details.php?place_id='.$aResult['place_id'].'&addressdetails=1&linkedplaces=1&childplaces=1">details</a>';
				echo '</div>';
				$i = $i+1;
			}
			if (sizeof($aSearchResults) && $sMoreURL)
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
			<div id="map-position"></div>
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
