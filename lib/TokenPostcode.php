<?php

namespace Nominatim\Token;

/**
 * A postcode token.
 */
class Postcode
{
    public $iId;
    // full postcode
    public $sPostcode;
    // optional restriction to a given country
    public $sCountryCode;

    public function __construct($iId, $sPostcode, $sCountryCode = '')
    {
        $this->iId = $iId;
        $this->sPostcode = $sPostcode;
        $this->sCountryCode = empty($sCountryCode) ? '' : $sCountryCode;
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'postcode',
                'Info' => $this->sPostcode.'('.$this->sCountryCode.')'
               );
    }
}
