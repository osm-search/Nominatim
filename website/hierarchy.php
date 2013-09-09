<?php
	@define('CONST_ConnectionBucket_PageType', 'Details');

	require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
	require_once(CONST_BasePath.'/lib/log.php');
	require_once(CONST_BasePath.'/lib/PlaceLookup.php');

	$sOutputFormat = 'html';
	if (isset($_GET['format']) && ($_GET['format'] == 'html' || $_GET['format'] == 'xml' || $_GET['format'] == 'json' ||  $_GET['format'] == 'jsonv2'))
	{
		$sOutputFormat = $_GET['format'];
	}

	ini_set('memory_limit', '200M');

	$oDB =& getDB();

	$aLangPrefOrder = getPreferredLanguages();
	$sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted",$aLangPrefOrder))."]";

	if (isset($_GET['osmtype']) && isset($_GET['osmid']) && (int)$_GET['osmid'] && ($_GET['osmtype'] == 'N' || $_GET['osmtype'] == 'W' || $_GET['osmtype'] == 'R'))
	{
		$_GET['place_id'] = $oDB->getOne("select place_id from placex where osm_type = '".$_GET['osmtype']."' and osm_id = ".(int)$_GET['osmid']." order by type = 'postcode' asc");

		// Be nice about our error messages for broken geometry
		if (!$_GET['place_id'])
		{
			$aPointDetails = $oDB->getRow("select osm_type, osm_id, errormessage, class, type, get_name_by_language(name,$sLanguagePrefArraySQL) as localname, ST_AsText(prevgeometry) as prevgeom, ST_AsText(newgeometry) as newgeom from import_polygon_error where osm_type = '".$_GET['osmtype']."' and osm_id = ".(int)$_GET['osmid']." order by updated desc limit 1");
			if (!PEAR::isError($aPointDetails) && $aPointDetails) {
				if (preg_match('/\[(-?\d+\.\d+) (-?\d+\.\d+)\]/', $aPointDetails['errormessage'], $aMatches))
				{
					$aPointDetails['error_x'] = $aMatches[1];
					$aPointDetails['error_y'] = $aMatches[2];
				}
				include(CONST_BasePath.'/lib/template/details-error-'.$sOutputFormat.'.php');
				exit;
			}
		}
	}

	if (!isset($_GET['place_id']))
	{
		echo "Please select a place id";
		exit;
	}

	$iPlaceID = (int)$_GET['place_id'];

	$sAuxHouseNumber = false;
	$iParentPlaceID = $oDB->getOne('select parent_place_id from location_property_tiger where place_id = '.$iPlaceID);
	if ($iParentPlaceID)
	{
		$iPlaceID = $iParentPlaceID;
	}
	else
	{
		$iParentPlaceID = $oDB->getOne('select parent_place_id from location_property_aux where place_id = '.$iPlaceID);
		if ($iParentPlaceID) $iPlaceID = $iParentPlaceID;
	}

	$oPlaceLookup = new PlaceLookup($oDB);
	$oPlaceLookup->setLanguagePreference($aLangPrefOrder);
	$oPlaceLookup->setIncludeAddressDetails(true);
	$oPlaceLookup->setPlaceId($iPlaceID);

	$aPlaceAddress = array_reverse($oPlaceLookup->getAddressDetails());
	$aBreadcrums = array();
	foreach($aPlaceAddress as $i => $aPlace)
	{
		if (!$aPlace['place_id']) continue;
		$aBreadcrums[] = array('placeId'=>$aPlace['place_id'], 'osmType'=>$aPlace['osm_type'], 'osmId'=>$aPlace['osm_id'], 'localName'=>$aPlace['localname']);
		$sPlaceUrl = 'hierarchy.php?place_id='.$aPlace['place_id'];
		$sOSMType = ($aPlace['osm_type'] == 'N'?'node':($aPlace['osm_type'] == 'W'?'way':($aPlace['osm_type'] == 'R'?'relation':'')));
                $sOSMUrl = 'http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aPlace['osm_id'];
		if ($sOutputFormat == 'html') if ($i) echo " > ";
		if ($sOutputFormat == 'html') echo '<a href="'.$sPlaceUrl.'">'.$aPlace['localname'].'</a> (<a href="'.$sOSMUrl.'">osm</a>)';
	}

	$aDetails = array();
	$aDetails['breadcrumbs'] = $aBreadcrums;

	if ($sOutputFormat == 'json')
	{
		header("content-type: application/json; charset=UTF-8");
		javascript_renderData($aDetails);
		exit;
	}

	$aRelatedPlaceIDs = $oDB->getCol($sSQL = "select place_id from placex where linked_place_id = $iPlaceID or place_id = $iPlaceID");

	$sSQL = "select obj.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea,  st_area(geometry) as area, ";
	$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
	$sSQL .= " from (select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, rank_search, geometry, name from placex ";
	$sSQL .= " where parent_place_id in (".join(',',$aRelatedPlaceIDs).") and name is not null order by rank_address asc,rank_search asc limit 500) as obj";
	$sSQL .= " order by rank_address asc,rank_search asc,localname,class, type,housenumber";
	$aParentOfLines = $oDB->getAll($sSQL);

        if (sizeof($aParentOfLines))
        {
                echo '<h2>Parent Of:</h2>';
		$aClassType = getClassTypesWithImportance();
                $aGroupedAddressLines = array();
                foreach($aParentOfLines as $aAddressLine)
                {
			if (isset($aClassType[$aAddressLine['class'].':'.$aAddressLine['type'].':'.$aAddressLine['admin_level']]['label'])
                                              && $aClassType[$aAddressLine['class'].':'.$aAddressLine['type'].':'.$aAddressLine['admin_level']]['label'])
                                {
                                        $aAddressLine['label'] = $aClassType[$aAddressLine['class'].':'.$aAddressLine['type'].':'.$aAddressLine['admin_level']]['label'];
                                }
			elseif (isset($aClassType[$aAddressLine['class'].':'.$aAddressLine['type']]['label'])
                                              && $aClassType[$aAddressLine['class'].':'.$aAddressLine['type']]['label'])
                                {
                                        $aAddressLine['label'] = $aClassType[$aAddressLine['class'].':'.$aAddressLine['type']]['label'];
                                }
			else $aAddressLine['label'] = ucwords($aAddressLine['type']);

                        if (!isset($aGroupedAddressLines[$aAddressLine['label']])) $aGroupedAddressLines[$aAddressLine['label']] = array();
                        $aGroupedAddressLines[$aAddressLine['label']][] = $aAddressLine;
                }
                foreach($aGroupedAddressLines as $sGroupHeading => $aParentOfLines)
                {
                        echo "<h3>$sGroupHeading</h3>";
                foreach($aParentOfLines as $aAddressLine)
                {
                        $aAddressLine['localname'] = $aAddressLine['localname']?$aAddressLine['localname']:$aAddressLine['housenumber'];
                        $sOSMType = ($aAddressLine['osm_type'] == 'N'?'node':($aAddressLine['osm_type'] == 'W'?'way':($aAddressLine['osm_type'] == 'R'?'relation':'')));

                        echo '<div class="line">';
                        echo '<span class="name">'.(trim($aAddressLine['localname'])?$aAddressLine['localname']:'<span class="noname">No Name</span>').'</span>';
                        echo ' (';
                        echo '<span class="area">'.($aAddressLine['isarea']=='t'?'Polygon':'Point').'</span>';
                        if ($sOSMType) echo ', <span class="osm"><span class="label"></span>'.$sOSMType.' <a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$aAddressLine['osm_id'].'">'.$aAddressLine['osm_id'].'</a></span>';
                        echo ', <a href="hierarchy.php?place_id='.$aAddressLine['place_id'].'">GOTO</a>';
                        echo ', '.$aAddressLine['area'];
                        echo ')';
                        echo '</div>';
                }
                }
                if (sizeof($aParentOfLines) >= 500) {
                        echo '<p>There are more child objects which are not shown.</p>';
                }
                echo '</div>';
        }
exit;


	$hLog = logStart($oDB, 'details', $_SERVER['QUERY_STRING'], $aLangPrefOrder);

	// Make sure the point we are reporting on is fully indexed
	//$sSQL = "UPDATE placex set indexed = true where indexed = false and place_id = $iPlaceID";
	//$oDB->query($sSQL);

	// Get the details for this point
	$sSQL = "select place_id, osm_type, osm_id, class, type, name, admin_level, housenumber, street, isin, postcode, calculated_country_code as country_code, importance, wikipedia,";
	$sSQL .= " to_char(indexed_date, 'YYYY-MM-DD HH24:MI') as indexed_date, parent_place_id, rank_address, rank_search, get_searchrank_label(rank_search) as rank_search_label, get_name_by_language(name,$sLanguagePrefArraySQL) as localname, ";
	$sSQL .= " ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, ";
	//$sSQL .= " ST_Area(geometry::geography) as area, ";
	$sSQL .= " ST_y(centroid) as lat, ST_x(centroid) as lon,";
	$sSQL .= " case when importance = 0 OR importance IS NULL then 0.75-(rank_search::float/40) else importance end as calculated_importance, ";
	$sSQL .= " ST_AsText(CASE WHEN ST_NPoints(geometry) > 5000 THEN ST_SimplifyPreserveTopology(geometry, 0.0001) ELSE geometry END) as outlinestring";
	$sSQL .= " from placex where place_id = $iPlaceID";
	$aPointDetails = $oDB->getRow($sSQL);
	if (PEAR::IsError($aPointDetails))
	{
		failInternalError("Could not get details of place object.", $sSQL, $aPointDetails);
	}
	$aPointDetails['localname'] = $aPointDetails['localname']?$aPointDetails['localname']:$aPointDetails['housenumber'];

	$aClassType = getClassTypesWithImportance();
	$aPointDetails['icon'] = $aClassType[$aPointDetails['class'].':'.$aPointDetails['type']]['icon'];

	// Get all alternative names (languages, etc)
	$sSQL = "select (each(name)).key,(each(name)).value from placex where place_id = $iPlaceID order by (each(name)).key";
	$aPointDetails['aNames'] = $oDB->getAssoc($sSQL);

	// Extra tags
	$sSQL = "select (each(extratags)).key,(each(extratags)).value from placex where place_id = $iPlaceID order by (each(extratags)).key";
	$aPointDetails['aExtraTags'] = $oDB->getAssoc($sSQL);

	// Address
	$aAddressLines = getAddressDetails($oDB, $sLanguagePrefArraySQL, $iPlaceID, $aPointDetails['country_code'], true);

	// Linked places
	$sSQL = "select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, st_distance(geometry, placegeometry) as distance, ";
	$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
	$sSQL .= " from placex, (select geometry as placegeometry from placex where place_id = $iPlaceID) as x";
	$sSQL .= " where linked_place_id = $iPlaceID";
	$sSQL .= " order by rank_address asc,rank_search asc,get_name_by_language(name,$sLanguagePrefArraySQL),housenumber";
	$aLinkedLines = $oDB->getAll($sSQL);

	// All places this is an imediate parent of
	$sSQL = "select obj.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon') as isarea, st_distance(geometry, placegeometry) as distance, ";
	$sSQL .= " get_name_by_language(name,$sLanguagePrefArraySQL) as localname, length(name::text) as namelength ";
	$sSQL .= " from (select placex.place_id, osm_type, osm_id, class, type, housenumber, admin_level, rank_address, rank_search, geometry, name from placex ";
	$sSQL .= " where parent_place_id = $iPlaceID order by rank_address asc,rank_search asc limit 500) as obj,";
	$sSQL .= " (select geometry as placegeometry from placex where place_id = $iPlaceID) as x";
	$sSQL .= " order by rank_address asc,rank_search asc,localname,housenumber";
	$aParentOfLines = $oDB->getAll($sSQL);

	$aPlaceSearchNameKeywords = false;
	$aPlaceSearchAddressKeywords = false;
	if (isset($_GET['keywords']) && $_GET['keywords'])
	{
		$sSQL = "select * from search_name where place_id = $iPlaceID";
		$aPlaceSearchName = $oDB->getRow($sSQL);
		$sSQL = "select * from word where word_id in (".substr($aPlaceSearchName['name_vector'],1,-1).")";
		$aPlaceSearchNameKeywords = $oDB->getAll($sSQL);
		$sSQL = "select * from word where word_id in (".substr($aPlaceSearchName['nameaddress_vector'],1,-1).")";
		$aPlaceSearchAddressKeywords = $oDB->getAll($sSQL);
	}

	logEnd($oDB, $hLog, 1);

	include(CONST_BasePath.'/lib/template/details-'.$sOutputFormat.'.php');
