<?php

namespace Nominatim\Token;

/**
 * A postcode token.
 */
class Postcode
{
    /// Database word id, if available.
    private $iId;
    /// Full nomralized postcode (upper cased).
    private $sPostcode;
    // Optional country code the postcode belongs to (currently unused).
    private $sCountryCode;

    public function __construct($iId, $sPostcode, $sCountryCode = '')
    {
        $this->iId = $iId;
        $this->sPostcode = $sPostcode;
        $this->sCountryCode = empty($sCountryCode) ? '' : $sCountryCode;
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

        if ($oSearch->hasPostcode() || !$oPosition->maybePhrase('postalcode')) {
            return $aNewSearches;
        }

        // If we have structured search or this is the first term,
        // make the postcode the primary search element.
        if ($oSearch->hasOperator(\Nominatim\Operator::NONE) && $oPosition->isFirstToken()) {
            $oNewSearch = $oSearch->clone(1);
            $oNewSearch->setPostcodeAsName($this->iId, $this->sPostcode);

            $aNewSearches[] = $oNewSearch;
        }

        // If we have a structured search or this is not the first term,
        // add the postcode as an addendum.
        if (!$oSearch->hasOperator(\Nominatim\Operator::POSTCODE)
            && ($oPosition->isPhrase('postalcode') || $oSearch->hasName())
        ) {
            $iPenalty = 1;
            if (strlen($this->sPostcode) < 4) {
                $iPenalty += 4 - strlen($this->sPostcode);
            }
            $oNewSearch = $oSearch->clone($iPenalty);
            $oNewSearch->setPostcode($this->sPostcode);

            $aNewSearches[] = $oNewSearch;
        }

        return $aNewSearches;
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'postcode',
                'Info' => $this->sPostcode.'('.$this->sCountryCode.')'
               );
    }

    public function debugCode()
    {
        return 'P';
    }
}
