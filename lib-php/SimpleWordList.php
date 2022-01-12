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
 * A word list creator based on simple splitting by space.
 *
 * Creates possible permutations of split phrases by finding all combination
 * of splitting the phrase on space boundaries.
 */
class SimpleWordList
{
    const MAX_WORDSET_LEN = 20;
    const MAX_WORDSETS = 100;

    // The phrase as a list of simple terms (without spaces).
    private $aWords;

    /**
     * Create a new word list
     *
     * @param string sPhrase  Phrase to create the word list from. The phrase is
     *                        expected to be normalised, so that there are no
     *                        subsequent spaces.
     */
    public function __construct($sPhrase)
    {
        if (strlen($sPhrase) > 0) {
            $this->aWords = explode(' ', $sPhrase);
        } else {
            $this->aWords = array();
        }
    }

    /**
     * Get all possible tokens that are present in this word list.
     *
     * @return array The list of string tokens in the word list.
     */
    public function getTokens()
    {
        $aTokens = array();
        $iNumWords = count($this->aWords);

        for ($i = 0; $i < $iNumWords; $i++) {
            $sPhrase = $this->aWords[$i];
            $aTokens[$sPhrase] = $sPhrase;

            for ($j = $i + 1; $j < $iNumWords; $j++) {
                $sPhrase .= ' '.$this->aWords[$j];
                $aTokens[$sPhrase] = $sPhrase;
            }
        }

        return $aTokens;
    }

    /**
     * Compute all possible permutations of phrase splits that result in
     * words which are in the token list.
     */
    public function getWordSets($oTokens)
    {
        $iNumWords = count($this->aWords);

        if ($iNumWords == 0) {
            return null;
        }

        // Caches the word set for the partial phrase up to word i.
        $aSetCache = array_fill(0, $iNumWords, array());

        // Initialise first element of cache. There can only be the word.
        if ($oTokens->containsAny($this->aWords[0])) {
            $aSetCache[0][] = array($this->aWords[0]);
        }

        // Now do the next elements using what we already have.
        for ($i = 1; $i < $iNumWords; $i++) {
            for ($j = $i; $j > 0; $j--) {
                $sPartial = $j == $i ? $this->aWords[$j] : $this->aWords[$j].' '.$sPartial;
                if (!empty($aSetCache[$j - 1]) && $oTokens->containsAny($sPartial)) {
                    $aPartial = array($sPartial);
                    foreach ($aSetCache[$j - 1] as $aSet) {
                        if (count($aSet) < SimpleWordList::MAX_WORDSET_LEN) {
                            $aSetCache[$i][] = array_merge($aSet, $aPartial);
                        }
                    }
                    if (count($aSetCache[$i]) > 2 * SimpleWordList::MAX_WORDSETS) {
                        usort(
                            $aSetCache[$i],
                            array('\Nominatim\SimpleWordList', 'cmpByArraylen')
                        );
                        $aSetCache[$i] = array_slice(
                            $aSetCache[$i],
                            0,
                            SimpleWordList::MAX_WORDSETS
                        );
                    }
                }
            }

            // finally the current full phrase
            $sPartial = $this->aWords[0].' '.$sPartial;
            if ($oTokens->containsAny($sPartial)) {
                $aSetCache[$i][] = array($sPartial);
            }
        }

        $aWordSets = $aSetCache[$iNumWords - 1];
        usort($aWordSets, array('\Nominatim\SimpleWordList', 'cmpByArraylen'));
        return array_slice($aWordSets, 0, SimpleWordList::MAX_WORDSETS);
    }

    public static function cmpByArraylen($aA, $aB)
    {
        $iALen = count($aA);
        $iBLen = count($aB);

        if ($iALen == $iBLen) {
            return 0;
        }

        return ($iALen < $iBLen) ? -1 : 1;
    }

    public function debugInfo()
    {
        return $this->aWords;
    }
}
