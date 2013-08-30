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

			$sSQL = "select placex.*,";
			$sSQL .= " get_address_by_language(place_id, $sLanguagePrefArraySQL) as langaddress,";
			$sSQL .= " get_name_by_language(name, $sLanguagePrefArraySQL) as placename,";
			$sSQL .= " get_name_by_language(name, ARRAY['ref']) as ref,";
			$sSQL .= " st_y(centroid) as lat, st_x(centroid) as lon";
			$sSQL .= " from placex where place_id = ".(int)$this->iPlaceID;
			$aPlace = $this->oDB->getRow($sSQL);

			if (!$aPlace['place_id']) return null;

			if ($this->bAddressDetails)
			{
				$aAddress = getAddressDetails($this->oDB, $sLanguagePrefArraySQL, $this->iPlaceID, $aPlace['calculated_country_code']);
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
	}
?>
