<?php

namespace Nominatim\Token;

/**
 * A house number token.
 */
class HouseNumber
{
    /// Database word id, if available.
    public $iId;
    /// Normalized house number.
    public $sToken;

    public function __construct($iId, $sToken)
    {
        $this->iId = $iId;
        $this->sToken = $sToken;
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'house number',
                'Info' => array('nr' => $this->sToken)
               );
    }
}
