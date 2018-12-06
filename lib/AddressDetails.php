<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/ClassTypes.php');

/**
 * Detailed list of address parts for a single result
 */
class AddressDetails
{
    private $aAddressLines;

    public function __construct(&$oDB, $iPlaceID, $sHousenumber, $mLangPref)
    {
        if (is_array($mLangPref)) {
            $mLangPref = 'ARRAY['.join(',', array_map('getDBQuoted', $mLangPref)).']';
        }

        if (!$sHousenumber) {
            $sHousenumber = -1;
        }

        $sSQL = 'SELECT *,';
        $sSQL .= ' get_name_by_language(name,'.$mLangPref.') as localname';
        $sSQL .= ' FROM get_addressdata('.$iPlaceID.','.$sHousenumber.')';
        $sSQL .= ' ORDER BY rank_address DESC, isaddress DESC';

        $this->aAddressLines = chksql($oDB->getAll($sSQL));
    }

    private static function isAddress($aLine)
    {
        return $aLine['isaddress'] == 't' || $aLine['type'] == 'country_code';
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
            if ($aLine['isaddress'] == 't' && $sPrevResult != $aLine['localname']) {
                $sPrevResult = $aLine['localname'];
                $aParts[] = $sPrevResult;
            }
        }

        return join(', ', $aParts);
    }

    public function getAddressNames()
    {
        $aAddress = array();
        $aFallback = array();

        foreach ($this->aAddressLines as $aLine) {
            if (!self::isAddress($aLine)) {
                continue;
            }

            $bFallback = false;
            $aTypeLabel = ClassTypes\getInfo($aLine);

            if ($aTypeLabel === false) {
                $aTypeLabel = ClassTypes\getFallbackInfo($aLine);
                $bFallback = true;
            }

            $sName = false;
            if (isset($aLine['localname']) && $aLine['localname']) {
                $sName = $aLine['localname'];
            } elseif (isset($aLine['housenumber']) && $aLine['housenumber']) {
                $sName = $aLine['housenumber'];
            }

            if ($sName) {
                $sTypeLabel = strtolower(isset($aTypeLabel['simplelabel']) ? $aTypeLabel['simplelabel'] : $aTypeLabel['label']);
                $sTypeLabel = str_replace(' ', '_', $sTypeLabel);
                if (!isset($aAddress[$sTypeLabel])
                    || isset($aFallback[$sTypeLabel])
                    || $aLine['class'] == 'place'
                ) {
                    $aAddress[$sTypeLabel] = $sName;
                    if ($bFallback) {
                        $aFallback[$sTypeLabel] = $bFallback;
                    }
                }
            }
        }
        return $aAddress;
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
