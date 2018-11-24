<?php

namespace Nominatim;

class ParameterParser
{
    private $aParams;


    public function __construct($aParams = null)
    {
        $this->aParams = ($aParams === null) ? $_GET : $aParams;
    }

    public function getBool($sName, $bDefault = false)
    {
        if (!isset($this->aParams[$sName]) || strlen($this->aParams[$sName]) == 0) {
            return $bDefault;
        }

        return (bool) $this->aParams[$sName];
    }

    public function getInt($sName, $bDefault = false)
    {
        if (!isset($this->aParams[$sName])) {
            return $bDefault;
        }

        if (!preg_match('/^[+-]?[0-9]+$/', $this->aParams[$sName])) {
            userError("Integer number expected for parameter '$sName'");
        }

        return (int) $this->aParams[$sName];
    }

    public function getFloat($sName, $bDefault = false)
    {
        if (!isset($this->aParams[$sName])) {
            return $bDefault;
        }

        if (!preg_match('/^[+-]?[0-9]*\.?[0-9]+$/', $this->aParams[$sName])) {
            userError("Floating-point number expected for parameter '$sName'");
        }

        return (float) $this->aParams[$sName];
    }

    public function getString($sName, $bDefault = false)
    {
        if (!isset($this->aParams[$sName]) || strlen($this->aParams[$sName]) == 0) {
            return $bDefault;
        }

        return $this->aParams[$sName];
    }

    public function getSet($sName, $aValues, $sDefault = false)
    {
        if (!isset($this->aParams[$sName]) || strlen($this->aParams[$sName]) == 0) {
            return $sDefault;
        }

        if (!in_array($this->aParams[$sName], $aValues)) {
            userError("Parameter '$sName' must be one of: ".join(', ', $aValues));
        }

        return $this->aParams[$sName];
    }

    public function getStringList($sName, $aDefault = false)
    {
        $sValue = $this->getString($sName);

        if ($sValue) {
            // removes all NULL, FALSE and Empty Strings but leaves 0 (zero) values
            return array_values(array_filter(explode(',', $sValue), 'strlen'));
        }

        return $aDefault;
    }

    public function getPreferredLanguages($sFallback = null)
    {
        if ($sFallback === null && isset($_SERVER['HTTP_ACCEPT_LANGUAGE'])) {
            $sFallback = $_SERVER['HTTP_ACCEPT_LANGUAGE'];
        }

        $aLanguages = array();
        $sLangString = $this->getString('accept-language', $sFallback);

        if ($sLangString) {
            if (preg_match_all('/(([a-z]{1,8})([-_][a-z]{1,8})?)\s*(;\s*q\s*=\s*(1|0\.[0-9]+))?/i', $sLangString, $aLanguagesParse, PREG_SET_ORDER)) {
                foreach ($aLanguagesParse as $iLang => $aLanguage) {
                    $aLanguages[$aLanguage[1]] = isset($aLanguage[5])?(float)$aLanguage[5]:1 - ($iLang/100);
                    if (!isset($aLanguages[$aLanguage[2]])) $aLanguages[$aLanguage[2]] = $aLanguages[$aLanguage[1]]/10;
                }
                arsort($aLanguages);
            }
        }
        if (empty($aLanguages) && CONST_Default_Language) {
            $aLanguages[CONST_Default_Language] = 1;
        }

        foreach ($aLanguages as $sLanguage => $fLanguagePref) {
            $aLangPrefOrder['short_name:'.$sLanguage] = 'short_name:'.$sLanguage;
            $aLangPrefOrder['name:'.$sLanguage] = 'name:'.$sLanguage;
        }
        $aLangPrefOrder['short_name'] = 'short_name';
        $aLangPrefOrder['name'] = 'name';
        $aLangPrefOrder['brand'] = 'brand';
        foreach ($aLanguages as $sLanguage => $fLanguagePref) {
            $aLangPrefOrder['official_name:'.$sLanguage] = 'official_name:'.$sLanguage;
        }
        $aLangPrefOrder['official_name'] = 'official_name';
        $aLangPrefOrder['ref'] = 'ref';
        $aLangPrefOrder['type'] = 'type';
        return $aLangPrefOrder;
    }
}
