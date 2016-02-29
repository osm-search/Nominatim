<?php
	class OutlineLookup
	{
		protected $oDB;

		protected $bIncludePolygonAsPoints = false;
		protected $bIncludePolygonAsText = false;
		protected $bIncludePolygonAsGeoJSON = false;
		protected $bIncludePolygonAsKML = false;
		protected $bIncludePolygonAsSVG = false;
		protected $fPolygonSimplificationThreshold = 0.0;

		function OutlineLookup(&$oDB)
		{
			$this->oDB =& $oDB;
		}

		function setIncludePolygonAsPoints($b = true)
		{
			$this->bIncludePolygonAsPoints = $b;
		}

		function getIncludePolygonAsPoints()
		{
			return $this->bIncludePolygonAsPoints;
		}

		function setIncludePolygonAsText($b = true)
		{
			$this->bIncludePolygonAsText = $b;
		}

		function getIncludePolygonAsText()
		{
			return $this->bIncludePolygonAsText;
		}

		function setIncludePolygonAsGeoJSON($b = true)
		{
			$this->bIncludePolygonAsGeoJSON = $b;
		}

		function setIncludePolygonAsKML($b = true)
		{
			$this->bIncludePolygonAsKML = $b;
		}

		function setIncludePolygonAsSVG($b = true)
		{
			$this->bIncludePolygonAsSVG = $b;
		}

		function setPolygonSimplificationThreshold($f)
		{
			$this->fPolygonSimplificationThreshold = $f;
		}

		// bIncludePolygonAsGeoJSON
		// bIncludePolygonAsKML)   
		// bIncludePolygonAsSVG)   
		// bIncludePolygonAsText || bIncludePolygonAsPoints
		// fPolygonSimplificationThreshold

		returns an array
		asgeojson
		askml
		assvg
		astext
		aPolyPoints
		aBoundingBox

		function addOutline($iPlaceID, $fRadius)
		{

			$aResult = array();
			// Get the bounding box and outline polygon
			$sSQL  = "select place_id,0 as numfeatures,st_area(geometry) as area,";
			$sSQL .= "ST_Y(centroid) as centrelat,ST_X(centroid) as centrelon,";
			$sSQL .= "ST_YMin(geometry) as minlat,ST_YMax(geometry) as maxlat,";
			$sSQL .= "ST_XMin(geometry) as minlon,ST_XMax(geometry) as maxlon";
			if ($this->bIncludePolygonAsGeoJSON) $sSQL .= ",ST_AsGeoJSON(geometry) as asgeojson";
			if ($this->bIncludePolygonAsKML)     $sSQL .= ",ST_AsKML(geometry) as askml";
			if ($this->bIncludePolygonAsSVG)     $sSQL .= ",ST_AsSVG(geometry) as assvg";
			if ($this->bIncludePolygonAsText || $this->bIncludePolygonAsPoints) $sSQL .= ",ST_AsText(geometry) as astext";
			$sFrom = " from placex where place_id = ".$iPlaceID;
			if ($this->fPolygonSimplificationThreshold > 0)
			{
				$sSQL .= " from (select place_id,centroid,ST_SimplifyPreserveTopology(geometry,".$this->fPolygonSimplificationThreshold.") as geometry".$sFrom.") as plx";
			}
			else
			{
				$sSQL .= $sFrom;
			}

			$aPointPolygon = $this->oDB->getRow($sSQL);
			if (PEAR::IsError($aPointPolygon))
			{
				failInternalError("Could not get outline.", $sSQL, $aPointPolygon);
			}


			if ($this->bIncludePolygonAsGeoJSON) $aResult['asgeojson'] = $aPointPolygon['asgeojson'];
			if ($this->bIncludePolygonAsKML)     $aResult['askml'] = $aPointPolygon['askml'];
			if ($this->bIncludePolygonAsSVG)     $aResult['assvg'] = $aPointPolygon['assvg'];
			if ($this->bIncludePolygonAsText)    $aResult['astext'] = $aPointPolygon['astext'];


			if ($this->bIncludePolygonAsPoints)
			{
				// Translate geometry string to point array
				if (preg_match('#POLYGON\\(\\(([- 0-9.,]+)#',$aPointPolygon['astext'],$aMatch))
				{
					preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/',$aMatch[1],$aPolyPoints,PREG_SET_ORDER);
				}
				elseif (preg_match('#MULTIPOLYGON\\(\\(\\(([- 0-9.,]+)#',$aPointPolygon['astext'],$aMatch))
				{
					preg_match_all('/(-?[0-9.]+) (-?[0-9.]+)/',$aMatch[1],$aPolyPoints,PREG_SET_ORDER);
				}
				elseif (preg_match('#POINT\\((-?[0-9.]+) (-?[0-9.]+)\\)#',$aPointPolygon['astext'],$aMatch))
				{
					$iSteps = max(8, min(100, ($fRadius * 40000)^2));
					$fStepSize = (2*pi())/$iSteps;
					$aPolyPoints = array();
					for($f = 0; $f < 2*pi(); $f += $fStepSize)
					{
						$aPolyPoints[] = array('',$aMatch[1]+($fRadius*sin($f)),$aMatch[2]+($fRadius*cos($f)));
					}
				}
			}

			// Output data suitable for display (points and a bounding box)
			if ($this->bIncludePolygonAsPoints && isset($aPolyPoints))
			{
				$aResult['aPolyPoints'] = array();
				foreach($aPolyPoints as $aPoint)
				{
					$aResult['aPolyPoints'][] = array($aPoint[1], $aPoint[2]);
				}
			}

			if (abs($aPointPolygon['minlat'] - $aPointPolygon['maxlat']) < 0.0000001)
			{
				$aPointPolygon['minlat'] = $aPointPolygon['minlat'] - $fRadius;
				$aPointPolygon['maxlat'] = $aPointPolygon['maxlat'] + $fRadius;
			}
			if (abs($aPointPolygon['minlon'] - $aPointPolygon['maxlon']) < 0.0000001)
			{
				$aPointPolygon['minlon'] = $aPointPolygon['minlon'] - $fRadius;
				$aPointPolygon['maxlon'] = $aPointPolygon['maxlon'] + $fRadius;
			}

			$aResult['aBoundingBox'] = array(
			                              (string)$aPointPolygon['minlat'],
			                              (string)$aPointPolygon['maxlat'],
			                              (string)$aPointPolygon['minlon'],
			                              (string)$aPointPolygon['maxlon']
			                           );

		}


		function calculateBoundingBox(lon,lat,$fRadius)

			if (!isset($aResult['aBoundingBox']))
			{
				$iSteps = max(8,min(100,$fRadius * 3.14 * 100000));
				$fStepSize = (2*pi())/$iSteps;
				$aPointPolygon['minlat'] = $aResult['lat'] - $fRadius;
				$aPointPolygon['maxlat'] = $aResult['lat'] + $fRadius;
				$aPointPolygon['minlon'] = $aResult['lon'] - $fRadius;
				$aPointPolygon['maxlon'] = $aResult['lon'] + $fRadius;

				// Output data suitable for display (points and a bounding box)
				if ($this->bIncludePolygonAsPoints)
				{
					$aPolyPoints = array();
					for($f = 0; $f < 2*pi(); $f += $fStepSize)
					{
						$aPolyPoints[] = array('',$aResult['lon']+($fRadius*sin($f)),$aResult['lat']+($fRadius*cos($f)));
					}
					$aResult['aPolyPoints'] = array();
					foreach($aPolyPoints as $aPoint)
					{
						$aResult['aPolyPoints'][] = array($aPoint[1], $aPoint[2]);
					}
				}
				$aResult['aBoundingBox'] = array((string)$aPointPolygon['minlat'],(string)$aPointPolygon['maxlat'],(string)$aPointPolygon['minlon'],(string)$aPointPolygon['maxlon']);
			}



			return $aResult;
		}







}