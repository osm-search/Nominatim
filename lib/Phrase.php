<?php

namespace Nominatim;

/**
 * Segment of a query string.
 *
 * The parts of a query strings are usually separated by commas.
 */
class Phrase
{
    CONST MAX_DEPTH = 7;

    // Complete phrase as a string.
    private $sPhrase;
    // Element type for structured searches.
    private $sPhraseType;
    // Space-separated words of the phrase.
    private $aWords;
    // Possible segmentations of the phrase.
    private $aWordSets;


    public function __construct($sPhrase, $sPhraseType)
    {
        $this->sPhrase = trim($sPhrase);
        $this->sPhraseType = $sPhraseType;
        $this->aWords = explode(' ', $this->sPhrase);
        $this->aWordSets = $this->createWordSets($this->aWords, 0);
    }

    public function getPhraseType()
    {
        return $this->sPhraseType;
    }

    public function getWordSets()
    {
        return $this->aWordSets;
    }

    public function addTokens(&$aTokens)
    {
        foreach ($this->aWordSets as $aSet) {
            foreach ($aSet as $sWord) {
                $aTokens[' '.$sWord] = ' '.$sWord;
                $aTokens[$sWord] = $sWord;
            }
        }
    }

    public function invertWordSets()
    {
        $this->aWordSets = $this->createInverseWordSets($this->aWords, 0);
    }

    private function createWordSets($aWords, $iDepth)
    {
        $aResult = array(array(join(' ', $aWords)));
        $sFirstToken = '';
        if ($iDepth < Phrase::MAX_DEPTH) {
            while (sizeof($aWords) > 1) {
                $sWord = array_shift($aWords);
                $sFirstToken .= ($sFirstToken?' ':'').$sWord;
                $aRest = $this->createWordSets($aWords, $iDepth + 1);
                foreach ($aRest as $aSet) {
                    $aResult[] = array_merge(array($sFirstToken), $aSet);
                }
            }
        }

        return $aResult;
    }

    public function createInverseWordSets($aWords, $iDepth)
    {
        $aResult = array(array(join(' ', $aWords)));
        $sFirstToken = '';
        if ($iDepth < Phrase::MAX_DEPTH) {
            while (sizeof($aWords) > 1) {
                $sWord = array_pop($aWords);
                $sFirstToken = $sWord.($sFirstToken?' ':'').$sFirstToken;
                $aRest = $this->createInverseWordSets($aWords, $iDepth + 1);
                foreach ($aRest as $aSet) {
                    $aResult[] = array_merge(array($sFirstToken), $aSet);
                }
            }
        }

        return $aResult;
    }
};
