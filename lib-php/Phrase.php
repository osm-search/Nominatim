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
 * Segment of a query string.
 *
 * The parts of a query strings are usually separated by commas.
 */
class Phrase
{
    // Complete phrase as a string (guaranteed to have no leading or trailing
    // spaces).
    private $sPhrase;
    // Element type for structured searches.
    private $sPhraseType;
    // Possible segmentations of the phrase.
    private $aWordSets;

    public function __construct($sPhrase, $sPhraseType)
    {
        $this->sPhrase = trim($sPhrase);
        $this->sPhraseType = $sPhraseType;
    }

    /**
     * Get the orginal phrase of the string.
     */
    public function getPhrase()
    {
        return $this->sPhrase;
    }

    /**
     * Return the element type of the phrase.
     *
     * @return string Pharse type if the phrase comes from a structured query
     *                or empty string otherwise.
     */
    public function getPhraseType()
    {
        return $this->sPhraseType;
    }

    public function setWordSets($aWordSets)
    {
        $this->aWordSets = $aWordSets;
    }

    /**
     * Return the array of possible segmentations of the phrase.
     *
     * @return string[][] Array of segmentations, each consisting of an
     *                    array of terms.
     */
    public function getWordSets()
    {
        return $this->aWordSets;
    }

    /**
     * Invert the set of possible segmentations.
     *
     * @return void
     */
    public function invertWordSets()
    {
        foreach ($this->aWordSets as $i => $aSet) {
            $this->aWordSets[$i] = array_reverse($aSet);
        }
    }

    public function debugInfo()
    {
        return array(
                'Type' => $this->sPhraseType,
                'Phrase' => $this->sPhrase,
                'WordSets' => $this->aWordSets
               );
    }
}
