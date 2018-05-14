<?php

namespace Nominatim\Token;

/**
 * A standard word token.
 */
class Word
{
    public $iId;
    // If true, the word may represent only part of a place name.
    public $bPartial;
    // Number of appearances in the database.
    public $iSearchNameCount;

    public function __construct($iId, $bPartial, $iSearchNameCount)
    {
        $this->iId = $iId;
        $this->bPartial = $bPartial;
        $this->iSearchNameCount = $iSearchNameCount;
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'word',
                'Info' => array(
                           'partial' => $this->bPartial,
                           'count' => $this->iSearchNameCount
                          )
               );
    }
}
