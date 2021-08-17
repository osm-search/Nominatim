<?php

namespace Nominatim\Token;

/**
 * A country token.
 */
class Country
{
    /// Database word id, if available.
    private $iId;
    /// Two-letter country code (lower-cased).
    private $sCountryCode;

    public function __construct($iId, $sCountryCode)
    {
        $this->iId = $iId;
        $this->sCountryCode = $sCountryCode;
    }

    public function getId()
    {
        return $this->iId;
    }

    /**
     * Check if the token can be added to the given search.
     * Derive new searches by adding this token to an existing search.
     *
     * @param object  $oSearch      Partial search description derived so far.
     * @param object  $oPosition    Description of the token position within
                                    the query.
     *
     * @return True if the token is compatible with the search configuration
     *         given the position.
     */
    public function isExtendable($oSearch, $oPosition)
    {
        return !$oSearch->hasCountry()
               && $oPosition->maybePhrase('country')
               && $oSearch->getContext()->isCountryApplicable($this->sCountryCode);
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
        $oNewSearch = $oSearch->clone($oPosition->isLastToken() ? 1 : 6);
        $oNewSearch->setCountry($this->sCountryCode);

        return array($oNewSearch);
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'country',
                'Info' => $this->sCountryCode
               );
    }

    public function debugCode()
    {
        return 'C';
    }
}
