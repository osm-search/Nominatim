<?php

namespace Nominatim\Token;

/**
 * A standard word token.
 */
class Partial
{
    /// Database word id, if applicable.
    private $iId;
    /// Number of appearances in the database.
    private $iSearchNameCount;
    /// True, if the token consists exclusively of digits and spaces.
    private $bNumberToken;

    public function __construct($iId, $sToken, $iSearchNameCount)
    {
        $this->iId = $iId;
        $this->bNumberToken = (bool) preg_match('#^[0-9 ]+$#', $sToken);
        $this->iSearchNameCount = $iSearchNameCount;
    }

    public function getId()
    {
        return $this->iId;
    }

    /**
     * Derive new searches by adding this token to an existing search.
     *
     * @param object  $oSearch      Partial search description derived so far.
     * @param object  $oPosition    Description of the token position within
                                    the query.
     *
     * @return SearchDescription[] List of derived search descriptions.
     */
    public function extendSearch($oSearch, $oPosition)
    {
        if ($oPosition->isPhrase('country')) {
            return array();
        }

        $aNewSearches = array();

        // Partial token in Address.
        if (($oPosition->isPhrase('') || !$oPosition->isFirstPhrase())
            && $oSearch->hasName()
        ) {
            $iSearchCost = $this->bNumberToken ? 2 : 1;
            if ($this->iSearchNameCount >= CONST_Max_Word_Frequency) {
                $iSearchCost += 1;
            }

            $oNewSearch = $oSearch->clone($iSearchCost);
            $oNewSearch->addAddressToken(
                $this->iId,
                $this->iSearchNameCount < CONST_Max_Word_Frequency
            );

            $aNewSearches[] = $oNewSearch;
        }

        // Partial token in Name.
        if ((!$oSearch->hasPostcode() && !$oSearch->hasAddress())
            && (!$oSearch->hasName(true)
                || $oSearch->getNamePhrase() == $oPosition->getPhrase())
        ) {
            $iSearchCost = 1;
            if (!$oSearch->hasName(true)) {
                $iSearchCost += 1;
            }
            if ($this->bNumberToken) {
                $iSearchCost += 1;
            }

            $oNewSearch = $oSearch->clone($iSearchCost);
            $oNewSearch->addPartialNameToken(
                $this->iId,
                $this->iSearchNameCount < CONST_Max_Word_Frequency,
                $oPosition->getPhrase()
            );

            $aNewSearches[] = $oNewSearch;
        }

        return $aNewSearches;
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

    public function debugCode()
    {
        return 'w';
    }
}
