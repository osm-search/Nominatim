<?php

namespace Nominatim;

/**
 * Segment of a query string.
 *
 * The parts of a query strings are usually separated by commas.
 */
class Phrase
{
    const MAX_DEPTH = 7;

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
        $this->sPhrase = preg_replace('/  +/', ' ', trim($sPhrase));
        $this->sPhraseType = $sPhraseType;
        $this->aWords = explode(' ', $this->sPhrase);
        $this->aWordSets = $this->createWordSets($this->aWords, 0);
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
     * Add the tokens from this phrase to the given list of tokens.
     *
     * @param string[] $aTokens List of tokens to append.
     *
     * @return void
     */
    public function addTokens(&$aTokens)
    {
        foreach ($this->aWordSets as $aSet) {
            foreach ($aSet as $sWord) {
                $aTokens[' '.$sWord] = ' '.$sWord;
                $aTokens[$sWord] = $sWord;
            }
        }
    }

    /**
     * Invert the set of possible segmentations.
     *
     * @return void
     */
    public function invertWordSets()
    {
        $this->aWordSets = $this->createInverseWordSets($this->aWords, 0);
    }

    private function createWordSets($aWords, $iDepth)
    {
        $aResult = array(array(join(' ', $aWords)));
        $sFirstToken = '';
        if ($iDepth < Phrase::MAX_DEPTH) {
            while (count($aWords) > 1) {
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

    private function createInverseWordSets($aWords, $iDepth)
    {
        $aResult = array(array(join(' ', $aWords)));
        $sFirstToken = '';
        if ($iDepth < Phrase::MAX_DEPTH) {
            while (count($aWords) > 1) {
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

    public function debugInfo()
    {
        return array(
                'Type' => $this->sPhraseType,
                'Phrase' => $this->sPhrase,
                'Words' => $this->aWords,
                'WordSets' => $this->aWordSets
               );
    }
}
