<?php

namespace Nominatim;

require_once(CONST_LibDir.'/TokenCountry.php');
require_once(CONST_LibDir.'/TokenHousenumber.php');
require_once(CONST_LibDir.'/TokenPostcode.php');
require_once(CONST_LibDir.'/TokenSpecialTerm.php');
require_once(CONST_LibDir.'/TokenWord.php');
require_once(CONST_LibDir.'/SpecialSearchOperator.php');

/**
 * Saves information about the tokens that appear in a search query.
 *
 * Tokens are sorted by their normalized form, the token word. There are different
 * kinds of tokens, represented by different Token* classes. Note that
 * tokens do not have a common base class. All tokens need to have a field
 * with the word id that points to an entry in the `word` database table
 * but otherwise the information saved about a token can be very different.
 *
 * There are two different kinds of token words: full words and partial terms.
 *
 * Full words start with a space. They represent a complete name of a place.
 * All special tokens are normally full words.
 *
 * Partial terms have no space at the beginning. They may represent a part of
 * a name of a place (e.g. in the name 'World Trade Center' a partial term
 * would be 'Trade' or 'Trade Center'). They are only used in TokenWord.
 */
class TokenList
{
    // List of list of tokens indexed by their word_token.
    private $aTokens = array();


    /**
     * Return total number of tokens.
     *
     * @return Integer
     */
    public function count()
    {
        return count($this->aTokens);
    }

    /**
     * Check if there are tokens for the given token word.
     *
     * @param string $sWord Token word to look for.
     *
     * @return bool True if there is one or more token for the token word.
     */
    public function contains($sWord)
    {
        return isset($this->aTokens[$sWord]);
    }

    /**
     * Check if there are partial or full tokens for the given word.
     *
     * @param string $sWord Token word to look for.
     *
     * @return bool True if there is one or more token for the token word.
     */
    public function containsAny($sWord)
    {
        return isset($this->aTokens[$sWord]) || isset($this->aTokens[' '.$sWord]);
    }

    /**
     * Get the list of tokens for the given token word.
     *
     * @param string $sWord Token word to look for.
     *
     * @return object[] Array of tokens for the given token word or an
     *                  empty array if no tokens could be found.
     */
    public function get($sWord)
    {
        return isset($this->aTokens[$sWord]) ? $this->aTokens[$sWord] : array();
    }

    public function getFullWordIDs()
    {
        $ids = array();

        foreach ($this->aTokens as $aTokenList) {
            foreach ($aTokenList as $oToken) {
                if (is_a($oToken, '\Nominatim\Token\Word') && !$oToken->bPartial) {
                    $ids[$oToken->iId] = $oToken->iId;
                }
            }
        }

        return $ids;
    }

    /**
     * Add a new token for the given word.
     *
     * @param string $sWord  Word the token describes.
     * @param object $oToken Token object to add.
     *
     * @return void
     */
    public function addToken($sWord, $oToken)
    {
        if (isset($this->aTokens[$sWord])) {
            $this->aTokens[$sWord][] = $oToken;
        } else {
            $this->aTokens[$sWord] = array($oToken);
        }
    }

    public function debugTokenByWordIdList()
    {
        $aWordsIDs = array();
        foreach ($this->aTokens as $sToken => $aWords) {
            foreach ($aWords as $aToken) {
                if ($aToken->iId !== null) {
                    $aWordsIDs[$aToken->iId] =
                        '#'.$sToken.'('.$aToken->iId.')#';
                }
            }
        }

        return $aWordsIDs;
    }

    public function debugInfo()
    {
        return $this->aTokens;
    }
}
