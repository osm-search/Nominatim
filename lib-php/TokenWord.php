<?php

namespace Nominatim\Token;

/**
 * A standard word token.
 */
class Word
{
    /// Database word id, if applicable.
    public $iId;
    /// If true, the word may represent only part of a place name.
    public $bPartial;
    /// Number of appearances in the database.
    public $iSearchNameCount;
    /// Number of terms in the word.
    public $iTermCount;

    public function __construct($iId, $bPartial, $iSearchNameCount, $iTermCount)
    {
        $this->iId = $iId;
        $this->bPartial = $bPartial;
        $this->iSearchNameCount = $iSearchNameCount;
        $this->iTermCount = $iTermCount;
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
