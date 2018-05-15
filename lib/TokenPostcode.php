<?php

namespace Nominatim\Token;

/**
 * A postcode token.
 */
class Postcode
{
    /// Database word id, if available.
    public $iId;
    /// Full nomralized postcode (upper cased).
    public $sPostcode;
    // Optional country code the postcode belongs to (currently unused).
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
