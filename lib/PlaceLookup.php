<?php
	class PlaceLookup
	{
		protected $oDB;

		protected $iPlaceID;

		protected $aLangPrefOrder = array();

		protected $bAddressDetails = false;

		function PlaceLookup(&$oDB)
		{
			$this->oDB =& $oDB;
		}

		function setLanguagePreference($aLangPrefOrder)
		{
			$this->aLangPrefOrder = $aLangPrefOrder;
		}

		function setIncludeAddressDetails($bAddressDetails = true)
		{
			$this->bAddressDetails = $bAddressDetails;
		}

		function setPlaceID($iPlaceID)
		{
			$this->iPlaceID = $iPlaceID;
		}

		function setOSMID($sType, $iID)
		{
			$sSQL = "select place_id from placex where osm_type = '".pg_escape_string($sType)."' and osm_id = ".(int)$iID." order by type = 'postcode' asc";
			$this->iPlaceID = $this->oDB->getOne($sSQL);
		}

		function lookup()
		{
			if (!$this->iPlaceID) return null;

			$sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted", $this->aLangPrefOrder))."]";

			$sSQL = "select placex.place_id, partition, osm_type, osm_id, class, type, admin_level, housenumber, street, isin, postcode, country_code, extratags, parent_place_id, linked_place_id, rank_address, rank_search, ";
			$sSQL .= " coalesce(importance,0.75-(rank_search::float/40)) as importance, indexed_status, indexed_date, wikipedia, calculated_country_code, ";
			$sSQL .= " get_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
			$sSQL .= " get_name_by_language(name, $sLanguagePrefArraySQL) as placename,";
			$sSQL .= " get_name_by_language(name, ARRAY['ref']) as ref,";
			$sSQL .= " (case when centroid is null then st_y(st_centroid(geometry)) else st_y(centroid) end) as lat,";
			$sSQL .= " (case when centroid is null then st_x(st_centroid(geometry)) else st_x(centroid) end) as lon";
			$sSQL .= " from placex where place_id = ".(int)$this->iPlaceID;
			$aPlace = $this->oDB->getRow($sSQL);

			if (!$aPlace['place_id']) return null;

			if ($this->bAddressDetails)
			{
				$aAddress = $this->getAddressNames();
				$aPlace['aAddress'] = $aAddress;
			}

			$aClassType = getClassTypes();
			$sAddressType = '';
			$sClassType = $aPlace['class'].':'.$aPlace['type'].':'.$aPlace['admin_level'];
			if (isset($aClassType[$sClassType]) && isset($aClassType[$sClassType]['simplelabel']))
			{
				$sAddressType = $aClassType[$aClassType]['simplelabel'];
			}
			else
			{
				$sClassType = $aPlace['class'].':'.$aPlace['type'];
				if (isset($aClassType[$sClassType]) && isset($aClassType[$sClassType]['simplelabel']))
					$sAddressType = $aClassType[$sClassType]['simplelabel'];
				else $sAddressType = $aPlace['class'];
			}

			$aPlace['addresstype'] = $sAddressType;

			return $aPlace;
		}

		function getAddressDetails($bAll = false)
		{
			if (!$this->iPlaceID) return null;

			$sLanguagePrefArraySQL = "ARRAY[".join(',',array_map("getDBQuoted", $this->aLangPrefOrder))."]";

			$sSQL = "select *,get_name_by_language(name,$sLanguagePrefArraySQL) as localname from get_addressdata(".$this->iPlaceID.")";
			if (!$bAll) $sSQL .= " WHERE isaddress OR type = 'country_code'";
			$sSQL .= " order by rank_address desc,isaddress desc";

			$aAddressLines = $this->oDB->getAll($sSQL);
			if (PEAR::IsError($aAddressLines))
			{
				var_dump($aAddressLines);
				exit;
			}
			return $aAddressLines;
		}

		function getAddressNames()
		{
			$aAddressLines = $this->getAddressDetails(false);;

			$aAddress = array();
			$aFallback = array();
			$aClassType = getClassTypes();
			foreach($aAddressLines as $aLine)
			{
				$bFallback = false;
				$aTypeLabel = false;
				if (isset($aClassType[$aLine['class'].':'.$aLine['type'].':'.$aLine['admin_level']])) $aTypeLabel = $aClassType[$aLine['class'].':'.$aLine['type'].':'.$aLine['admin_level']];
				elseif (isset($aClassType[$aLine['class'].':'.$aLine['type']])) $aTypeLabel = $aClassType[$aLine['class'].':'.$aLine['type']];
				elseif (isset($aClassType['boundary:administrative:'.((int)($aLine['rank_address']/2))]))
				{
					$aTypeLabel = $aClassType['boundary:administrative:'.((int)($aLine['rank_address']/2))];
					$bFallback = true;
				}
				else
				{
					$aTypeLabel = array('simplelabel'=>'address'.$aLine['rank_address']);
					$bFallback = true;
				}
				if ($aTypeLabel && ((isset($aLine['localname']) && $aLine['localname']) || (isset($aLine['housenumber']) && $aLine['housenumber'])))
				{
					$sTypeLabel = strtolower(isset($aTypeLabel['simplelabel'])?$aTypeLabel['simplelabel']:$aTypeLabel['label']);
					$sTypeLabel = str_replace(' ','_',$sTypeLabel);
					if (!isset($aAddress[$sTypeLabel]) || (isset($aFallback[$sTypeLabel]) && $aFallback[$sTypeLabel]) || $aLine['class'] == 'place')
					{
						$aAddress[$sTypeLabel] = $aLine['localname']?$aLine['localname']:$aLine['housenumber'];
					}
					$aFallback[$sTypeLabel] = $bFallback;
				}
			}
			return $aAddress;
		}

	}
?>
