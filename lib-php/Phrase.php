<?php

namespace Nominatim;

/**
 * Segment of a query string.
 *
 * The parts of a query strings are usually separated by commas.
 */
class Phrase
{
    const MAX_WORDSET_LEN = 20;
    const MAX_WORDSETS = 100;

    // Complete phrase as a string.
    private $sPhrase;
    // Element type for structured searches.
    private $sPhraseType;
    // Possible segmentations of the phrase.
    private $aWordSets;

    public static function cmpByArraylen($aA, $aB)
    {
        $iALen = count($aA);
        $iBLen = count($aB);

        if ($iALen == $iBLen) {
            return 0;
        }

        return ($iALen < $iBLen) ? -1 : 1;
    }


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

    public function computeWordSets($aWords, $oTokens)
    {
        $iNumWords = count($aWords);

        if ($iNumWords == 0) {
            $this->aWordSets = null;
            return;
        }

        // Caches the word set for the partial phrase up to word i.
        $aSetCache = array_fill(0, $iNumWords, array());

        // Initialise first element of cache. There can only be the word.
        if ($oTokens->containsAny($aWords[0])) {
            $aSetCache[0][] = array($aWords[0]);
        }

        // Now do the next elements using what we already have.
        for ($i = 1; $i < $iNumWords; $i++) {
            for ($j = $i; $j > 0; $j--) {
                $sPartial = $j == $i ? $aWords[$j] : $aWords[$j].' '.$sPartial;
                if (!empty($aSetCache[$j - 1]) && $oTokens->containsAny($sPartial)) {
                    $aPartial = array($sPartial);
                    foreach ($aSetCache[$j - 1] as $aSet) {
                        if (count($aSet) < Phrase::MAX_WORDSET_LEN) {
                            $aSetCache[$i][] = array_merge($aSet, $aPartial);
                        }
                    }
                    if (count($aSetCache[$i]) > 2 * Phrase::MAX_WORDSETS) {
                        usort(
                            $aSetCache[$i],
                            array('\Nominatim\Phrase', 'cmpByArraylen')
                        );
                        $aSetCache[$i] = array_slice(
                            $aSetCache[$i],
                            0,
                            Phrase::MAX_WORDSETS
                        );
                    }
                }
            }

            // finally the current full phrase
            $sPartial = $aWords[0].' '.$sPartial;
            if ($oTokens->containsAny($sPartial)) {
                $aSetCache[$i][] = array($sPartial);
            }
        }

        $this->aWordSets = $aSetCache[$iNumWords - 1];
        usort($this->aWordSets, array('\Nominatim\Phrase', 'cmpByArraylen'));
        $this->aWordSets = array_slice($this->aWordSets, 0, Phrase::MAX_WORDSETS);
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
