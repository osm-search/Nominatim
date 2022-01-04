<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

namespace Nominatim;

/**
 * Description of the position of a token within a query.
 */
class SearchPosition
{
    private $sPhraseType;

    private $iPhrase;
    private $iNumPhrases;

    private $iToken;
    private $iNumTokens;


    public function __construct($sPhraseType, $iPhrase, $iNumPhrases)
    {
        $this->sPhraseType = $sPhraseType;
        $this->iPhrase = $iPhrase;
        $this->iNumPhrases = $iNumPhrases;
    }

    public function setTokenPosition($iToken, $iNumTokens)
    {
        $this->iToken = $iToken;
        $this->iNumTokens = $iNumTokens;
    }

    /**
     * Check if the phrase can be of the given type.
     *
     * @param string  $sType  Type of phrse requested.
     *
     * @return True if the phrase is untyped or of the given type.
     */
    public function maybePhrase($sType)
    {
        return $this->sPhraseType == '' || $this->sPhraseType == $sType;
    }

    /**
     * Check if the phrase is exactly of the given type.
     *
     * @param string  $sType  Type of phrse requested.
     *
     * @return True if the phrase of the given type.
     */
    public function isPhrase($sType)
    {
        return $this->sPhraseType == $sType;
    }

    /**
     * Return true if the token is the very first in the query.
     */
    public function isFirstToken()
    {
        return $this->iPhrase == 0 && $this->iToken == 0;
    }

    /**
     * Check if the token is the final one in the query.
     */
    public function isLastToken()
    {
        return $this->iToken + 1 == $this->iNumTokens && $this->iPhrase + 1 == $this->iNumPhrases;
    }

    /**
     * Check if the current token is part of the first phrase in the query.
     */
    public function isFirstPhrase()
    {
        return $this->iPhrase == 0;
    }

    /**
     * Get the phrase position in the query.
     */
    public function getPhrase()
    {
        return $this->iPhrase;
    }
}
