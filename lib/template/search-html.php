<?php
	header("content-type: text/html; charset=UTF-8");
?>
<body id="search-page">

<?php include(CONST_BasePath.'/lib/template/includes/html-header.php'); ?>

	<header class="container-fluid">
		<div class="row">
			<div class="col-xs-4">
				<div class="brand">
					<a href="<?php echo CONST_Website_BaseURL;?>">
					<img alt="logo" src="images/osm_logo.120px.png" width="40" height="40"/>
					<h1>Nominatim</h1>
					</a>
				</div>
			</div>
			<div id="last-updated" class="col-xs-4 text-center">
				Data last updated:
				<br>
				<?php echo $sDataDate; ?>
			</div>
			<div class="col-xs-4 text-right">
				<div class="btn-group">
					<button class="dropdown-toggle btn btn-link" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">
						About &amp; Help <span class="caret"></span>
					</button>
					<ul class="dropdown-menu dropdown-menu-right">
						<li><a href="http://wiki.openstreetmap.org/wiki/Nominatim" target="_blank">Documentation</a></li>
						<li><a href="http://wiki.openstreetmap.org/wiki/Nominatim/FAQ" target="_blank">FAQ</a></li>
						<li role="separator" class="divider"></li>
						<li><a href="#" class="" data-toggle="modal" data-target="#report-modal">Report problem with results</a></li>
					</ul>
				</div>
			</div>
		</div>
	</header>

	<form class="form-inline" role="search" accept-charset="UTF-8" action="<?php echo CONST_Website_BaseURL; ?>search.php">
		<div class="form-group">
			<input id="q" name="q" type="text" class="form-control input-sm" placeholder="Search" value="<?php echo htmlspecialchars($sQuery); ?>" >
		</div>
		<div class="form-group">
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
	</form>


	<div id="content">
<?php
	if ($sQuery)
	{
?>
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
		echo ' <a class="btn btn-default btn-xs details" href="details.php?place_id='.$aResult['place_id'].'">details</a>';
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
<?php
	}
	else
	{
?>
	<div id="intro" class="sidebar">
	</div>

<?php

	}
?>
			<div id="map-wrapper">
				<div id="map-position"></div>
				<div id="map"></div>
			</div>
		</div>

	</div>

	<footer>
		<p class="disclaimer">
			Addresses and postcodes are approximate
		</p>
		<p class="copyright">
			&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors
		</p>
	</footer>

	<div class="modal fade" id="report-modal">
		<div class="modal-dialog">
			<div class="modal-content">
				<div class="modal-header">
					<button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
					<h4 class="modal-title">Report a problem</h4>
				</div>
				<div class="modal-body">
					<?php include(CONST_BasePath.'/lib/template/includes/report-errors.php'); ?>
				</div>
				<div class="modal-footer">
					<button type="button" class="btn btn-default" data-dismiss="modal">OK</button>
				</div>
			</div>
		</div>
	</div>




	<script type="text/javascript">
	<?php

		$aNominatimMapInit = [
			'zoom' => $iZoom,
			'lat' => $fLat,
			'lon' => $fLon
		];
		echo 'var nominatim_map_init = ' . json_encode($aNominatimMapInit, JSON_PRETTY_PRINT) . ';';

		$aNominatimResults = [];
		echo 'var nominatim_results = ' . json_encode($aSearchResults, JSON_PRETTY_PRINT) . ';'; 
	?>
	</script>
	<?php include(CONST_BasePath.'/lib/template/includes/html-footer.php'); ?>

</body>
</html>
