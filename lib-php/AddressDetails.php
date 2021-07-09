<?php

namespace Nominatim;

require_once(CONST_LibDir.'/ClassTypes.php');

/**
 * Detailed list of address parts for a single result
 */
class AddressDetails
{
    private $iPlaceID;
    private $aAddressLines;

    public function __construct(&$oDB, $iPlaceID, $sHousenumber, $mLangPref)
    {
        $this->iPlaceID = $iPlaceID;

        if (is_array($mLangPref)) {
            $mLangPref = $oDB->getArraySQL($oDB->getDBQuotedList($mLangPref));
        }

        if (!isset($sHousenumber)) {
            $sHousenumber = -1;
        }

        $sSQL = 'SELECT *,';
        $sSQL .= ' get_name_by_language(name,'.$mLangPref.') as localname';
        $sSQL .= ' FROM get_addressdata('.$iPlaceID.','.$sHousenumber.')';
        $sSQL .= ' ORDER BY rank_address DESC, isaddress DESC';

        $this->aAddressLines = $oDB->getAll($sSQL);
    }

    private static function isAddress($aLine)
    {
        return $aLine['isaddress'] || $aLine['type'] == 'country_code';
    }

    public function getAddressDetails($bAll = false)
    {
        if ($bAll) {
            return $this->aAddressLines;
        }

        return array_filter($this->aAddressLines, array(__CLASS__, 'isAddress'));
    }

    public function getLocaleAddress()
    {
        $aParts = array();
        $sPrevResult = '';

        foreach ($this->aAddressLines as $aLine) {
            if ($aLine['isaddress'] && $sPrevResult != $aLine['localname']) {
                $sPrevResult = $aLine['localname'];
                $aParts[] = $sPrevResult;
            }
        }

        return join(', ', $aParts);
    }

    public function getAddressNames()
    {
        $aAddress = array();

        foreach ($this->aAddressLines as $aLine) {
            if (!self::isAddress($aLine)) {
                continue;
            }

            $sTypeLabel = ClassTypes\getLabelTag($aLine);

            $sName = null;
            if (isset($aLine['localname']) && $aLine['localname']!=='') {
                $sName = $aLine['localname'];
            } elseif (isset($aLine['housenumber']) && $aLine['housenumber']!=='') {
                $sName = $aLine['housenumber'];
            }

            if (isset($sName)) {
                if (!isset($aAddress[$sTypeLabel])
                    || $aLine['class'] == 'place'
                ) {
                    $aAddress[$sTypeLabel] = $sName;
                }
            }
        }

        return $aAddress;
    }

    /**
     * Annotates the given json with geocodejson address information fields.
     *
     * @param array  $aJson  Json hash to add the fields to.
     *
     * Geocodejson has the following fields:
     *  street, locality, postcode, city, district,
     *  county, state, country
     *
     * Postcode and housenumber are added by type, district is not used.
     * All other fields are set according to address rank.
     */
    public function addGeocodeJsonAddressParts(&$aJson)
    {
        foreach (array_reverse($this->aAddressLines) as $aLine) {
            if (!$aLine['isaddress']) {
                continue;
            }

            if (!isset($aLine['localname']) || $aLine['localname'] == '') {
                continue;
            }

            if ($aLine['type'] == 'postcode' || $aLine['type'] == 'postal_code') {
                $aJson['postcode'] = $aLine['localname'];
                continue;
            }

            if ($aLine['type'] == 'house_number') {
                $aJson['housenumber'] = $aLine['localname'];
                continue;
            }

            if ($this->iPlaceID == $aLine['place_id']) {
                continue;
            }

            $iRank = (int)$aLine['rank_address'];

            if ($iRank > 25 && $iRank < 28) {
                $aJson['street'] = $aLine['localname'];
            } elseif ($iRank >= 22 && $iRank <= 25) {
                $aJson['locality'] = $aLine['localname'];
            } elseif ($iRank >= 17 && $iRank <= 21) {
                $aJson['district'] = $aLine['localname'];
            } elseif ($iRank >= 13 && $iRank <= 16) {
                $aJson['city'] = $aLine['localname'];
            } elseif ($iRank >= 10 && $iRank <= 12) {
                $aJson['county'] = $aLine['localname'];
            } elseif ($iRank >= 5 && $iRank <= 9) {
                $aJson['state'] = $aLine['localname'];
            } elseif ($iRank == 4) {
                $aJson['country'] = $aLine['localname'];
            }
        }
    }

    public function getAdminLevels()
    {
        $aAddress = array();
        foreach (array_reverse($this->aAddressLines) as $aLine) {
            if (self::isAddress($aLine)
                && isset($aLine['admin_level'])
                && $aLine['admin_level'] < 15
                && !isset($aAddress['level'.$aLine['admin_level']])
            ) {
                $aAddress['level'.$aLine['admin_level']] = $aLine['localname'];
            }
        }
        return $aAddress;
    }

    public function debugInfo()
    {
        return $this->aAddressLines;
    }
}
