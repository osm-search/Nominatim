<?php
	class PoisNear
	{
		protected $oDB;
		protected $fLat;
		protected $fLon;
		protected $iMaxRank = 28;

		protected $aLangPrefOrder = array();

		function __construct(&$oDB)
		{
			$this->oDB =& $oDB;
		}

		function setLanguagePreference($aLangPref)
		{
			$this->aLangPrefOrder = $aLangPref;
		}

		function setLatLon($fLat, $fLon)
		{
			$this->fLat = (float)$fLat;
			$this->fLon = (float)$fLon;
		}

		function setRank($iRank)
		{
			$this->iMaxRank = $iRank;
		}

		function setClassAndType($sClass, $sType){
			//TODO: make one only param poitype, coercing type and class mixed
			$this->sClass = $this->oDB->escapeSimple($sClass);
			$this->sType = $this->oDB->escapeSimple($sType);
		}

		function lookup()
		{
			$sPointSQL = 'ST_SetSRID(ST_MakePoint('.$this->fLon.','.$this->fLat.'),4326)';

			$sSQL = <<<SQL
			SELECT place_id, osm_id, class, type, hstore_to_json(name) as name,
			ST_Distance(geometry,poi)/1000 AS distance_km
			FROM placex,
			(SELECT $sPointSQL as poi ) as poi
			WHERE ST_DWithin(geometry, $sPointSQL, 1)
			AND
			"class"='$this->sClass' and "type"='$this->sType'
			--"class"='amenity' and "type"='hospital'
			--"class"='leisure'  AND "type"  = 'golf_course'
			--"class"='natural'  AND "type"  = 'coastline'
			--"class"='aeroway'  AND  "type" = 'aerodrome'
			--"class"='natural'  AND "type"  = 'beach'
			ORDER BY distance_km ASC
			LIMIT 20;
SQL;
				if (CONST_Debug) var_dump($sSQL);
				$aPlaces = $this->oDB->getAll($sSQL);
				if (PEAR::IsError($aPlaces))
				{
					failInternalError("Could not determine near points of interest.", $sSQL, $aPlaces);
				}


			return $aPlaces;
		}
	}
