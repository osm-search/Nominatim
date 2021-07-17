<?php

namespace Nominatim\Token;

/**
 * A house number token.
 */
class HouseNumber
{
    /// Database word id, if available.
    private $iId;
    /// Normalized house number.
    private $sToken;

    public function __construct($iId, $sToken)
    {
        $this->iId = $iId;
        $this->sToken = $sToken;
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
        $aNewSearches = array();

        if ($oSearch->hasHousenumber()
            || $oSearch->hasOperator(\Nominatim\Operator::POSTCODE)
            || !$oPosition->maybePhrase('street')
        ) {
            return $aNewSearches;
        }

        // sanity check: if the housenumber is not mainly made
        // up of numbers, add a penalty
        $iSearchCost = 1;
        if (preg_match('/\\d/', $this->sToken) === 0
            || preg_match_all('/[^0-9]/', $this->sToken, $aMatches) > 2) {
            $iSearchCost++;
        }
        if (!$oSearch->hasOperator(\Nominatim\Operator::NONE)) {
            $iSearchCost++;
        }
        if (empty($this->iId)) {
            $iSearchCost++;
        }
        // also must not appear in the middle of the address
        if ($oSearch->hasAddress() || $oSearch->hasPostcode()) {
            $iSearchCost++;
        }

        $oNewSearch = $oSearch->clone($iSearchCost);
        $oNewSearch->setHousenumber($this->sToken);
        $aNewSearches[] = $oNewSearch;

        // Housenumbers may appear in the name when the place has its own
        // address terms.
        if ($this->iId !== null
            && ($oSearch->getNamePhrase() >= 0 || !$oSearch->hasName())
            && !$oSearch->hasAddress()
        ) {
            $oNewSearch = $oSearch->clone($iSearchCost);
            $oNewSearch->setHousenumberAsName($this->iId);

            $aNewSearches[] = $oNewSearch;
        }

        return $aNewSearches;
    }


    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'house number',
                'Info' => array('nr' => $this->sToken)
               );
    }

    public function debugCode()
    {
        return 'H';
    }
}
