<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

namespace Nominatim\Token;

/**
 * A standard word token.
 */
class Word
{
    /// Database word id, if applicable.
    private $iId;
    /// Number of appearances in the database.
    private $iSearchNameCount;
    /// Number of terms in the word.
    private $iTermCount;

    public function __construct($iId, $iSearchNameCount, $iTermCount)
    {
        $this->iId = $iId;
        $this->iSearchNameCount = $iSearchNameCount;
        $this->iTermCount = $iTermCount;
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
        return !$oPosition->isPhrase('country');
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
        // Full words can only be a name if they appear at the beginning
        // of the phrase. In structured search the name must forcibly in
        // the first phrase. In unstructured search it may be in a later
        // phrase when the first phrase is a house number.
        if ($oSearch->hasName()
            || !($oPosition->isFirstPhrase() || $oPosition->isPhrase(''))
        ) {
            if ($this->iTermCount > 1
                && ($oPosition->isPhrase('') || !$oPosition->isFirstPhrase())
            ) {
                $oNewSearch = $oSearch->clone(1);
                $oNewSearch->addAddressToken($this->iId);

                return array($oNewSearch);
            }
        } elseif (!$oSearch->hasName(true)) {
            $oNewSearch = $oSearch->clone(1);
            $oNewSearch->addNameToken(
                $this->iId,
                CONST_Search_NameOnlySearchFrequencyThreshold
                && $this->iSearchNameCount
                          < CONST_Search_NameOnlySearchFrequencyThreshold
            );

            return array($oNewSearch);
        }

        return array();
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'word',
                'Info' => array(
                           'count' => $this->iSearchNameCount,
                           'terms' => $this->iTermCount
                          )
               );
    }

    public function debugCode()
    {
        return 'W';
    }
}
