<?php
        require_once(dirname(dirname(__FILE__)).'/lib/init-website.php');
        require_once(CONST_BasePath.'/lib/log.php');

	$sOutputFormat = 'html';
	ini_set('memory_limit', '200M');

	$oDB =& getDB();

	$sSQL = "select placex.place_id, calculated_country_code as country_code, name->'name' as name, i.* from placex, import_polygon_delete i where placex.osm_id = i.osm_id and placex.osm_type = i.osm_type and placex.class = i.class and placex.type = i.type";
	$aPolygons = $oDB->getAll($sSQL);
	if (PEAR::isError($aPolygons))
	{
		failInternalError("Could not get list of deleted OSM elements.", $sSQL, $aPolygons);
	}

//var_dump($aPolygons);
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
    
    <title>Nominatim Deleted Data</title>
    
    <meta name="description" content="List of OSM data that has been deleted" lang="en-US" />

</head>

<body>
<style type="text/css">
table {
	border-width: 1px;
	border-spacing: 0px;
	border-style: solid;
	border-color: gray;
	border-collapse: collapse;
	background-color: white;
	margin: 10px;
}
table th {
	border-width: 1px;
	padding: 2px;
	border-style: inset;
	border-color: gray;
	border-left-color: #ddd;
	border-right-color: #ddd;
	background-color: #eee;
	-moz-border-radius: 0px 0px 0px 0px;
}
table td {
	border-width: 1px;
	padding: 2px;
	border-style: inset;
	border-color: gray;
	border-left-color: #ddd;
	border-right-color: #ddd;
	background-color: white;
	-moz-border-radius: 0px 0px 0px 0px;
}
</style>

<p>Objects in this table have been deleted in OSM but are still in the Nominatim database.</p>

<table>
<?php
	echo "<tr>";
//var_dump($aPolygons[0]);
	foreach($aPolygons[0] as $sCol => $sVal)
	{
		echo "<th>".$sCol."</th>";
	}
	echo "</tr>";
	foreach($aPolygons as $aRow)
	{
		echo "<tr>";
		foreach($aRow as $sCol => $sVal)
		{
			switch($sCol)
			{
            case 'osm_id':
                $sOSMType = ($aRow['osm_type'] == 'N'?'node':($aRow['osm_type'] == 'W'?'way':($aRow['osm_type'] == 'R'?'relation':'')));
                echo '<td><a href="http://www.openstreetmap.org/browse/'.$sOSMType.'/'.$sVal.'" target="_new">'.$sVal.'</a></td>';
                                break;
			case 'place_id':
				echo '<td><a href="'.CONST_Website_BaseURL.'details?place_id='.$sVal.'">'.$sVal.'</a></td>';
				break;
			default:
				echo "<td>".($sVal?$sVal:'&nbsp;')."</td>";
				break;
			}
		}
		echo "</tr>";
	}
?>
</table>



</body>
</html>
