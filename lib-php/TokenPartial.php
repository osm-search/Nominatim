<?php

namespace Nominatim\Token;

/**
 * A standard word token.
 */
class Partial
{
    /// Database word id, if applicable.
    public $iId;
    /// Number of appearances in the database.
    public $iSearchNameCount;
    /// Normalised version of the partial word.
    public $sToken;

    public function __construct($iId, $sToken, $iSearchNameCount)
    {
        $this->iId = $iId;
        $this->sToken = $sToken;
        $this->iSearchNameCount = $iSearchNameCount;
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'partial',
                'Info' => array(
                           'count' => $this->iSearchNameCount
                          )
               );
    }
}
