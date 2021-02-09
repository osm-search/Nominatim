<?php

namespace Nominatim\Token;

/**
 * A country token.
 */
class Country
{
    /// Database word id, if available.
    public $iId;
    /// Two-letter country code (lower-cased).
    public $sCountryCode;

    public function __construct($iId, $sCountryCode)
    {
        $this->iId = $iId;
        $this->sCountryCode = $sCountryCode;
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'country',
                'Info' => $this->sCountryCode
               );
    }
}
