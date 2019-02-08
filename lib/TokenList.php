<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/TokenCountry.php');
require_once(CONST_BasePath.'/lib/TokenHousenumber.php');
require_once(CONST_BasePath.'/lib/TokenPostcode.php');
require_once(CONST_BasePath.'/lib/TokenSpecialTerm.php');
require_once(CONST_BasePath.'/lib/TokenWord.php');
require_once(CONST_BasePath.'/lib/SpecialSearchOperator.php');

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

    /**
     * Add token information from the word table in the database.
     *
     * @param object   $oDB           Nominatim::DB instance.
     * @param string[] $aTokens       List of tokens to look up in the database.
     * @param string[] $aCountryCodes List of country restrictions.
     * @param string   $sNormQuery    Normalized query string.
     * @param object   $oNormalizer   Normalizer function to use on tokens.
     *
     * @return void
     */
    public function addTokensFromDB(&$oDB, &$aTokens, &$aCountryCodes, $sNormQuery, $oNormalizer)
    {
        // Check which tokens we have, get the ID numbers
        $sSQL = 'SELECT word_id, word_token, word, class, type, country_code,';
        $sSQL .= ' operator, coalesce(search_name_count, 0) as count';
        $sSQL .= ' FROM word WHERE word_token in (';
        $sSQL .= join(',', $oDB->getDBQuotedList($aTokens)).')';

        Debug::printSQL($sSQL);

        $aDBWords = $oDB->getAll($sSQL, null, 'Could not get word tokens.');

        foreach ($aDBWords as $aWord) {
            $oToken = null;
            $iId = (int) $aWord['word_id'];

            if ($aWord['class']) {
                // Special terms need to appear in their normalized form.
                if ($aWord['word']) {
                    $sNormWord = $aWord['word'];
                    if ($oNormalizer != null) {
                        $sNormWord = $oNormalizer->transliterate($aWord['word']);
                    }
                    if (strpos($sNormQuery, $sNormWord) === false) {
                        continue;
                    }
                }

                if ($aWord['class'] == 'place' && $aWord['type'] == 'house') {
                    $oToken = new Token\HouseNumber($iId, trim($aWord['word_token']));
                } elseif ($aWord['class'] == 'place' && $aWord['type'] == 'postcode') {
                    if ($aWord['word']
                        && pg_escape_string($aWord['word']) == $aWord['word']
                    ) {
                        $oToken = new Token\Postcode(
                            $iId,
                            $aWord['word'],
                            $aWord['country_code']
                        );
                    }
                } else {
                    // near and in operator the same at the moment
                    $oToken = new Token\SpecialTerm(
                        $iId,
                        $aWord['class'],
                        $aWord['type'],
                        $aWord['operator'] ? Operator::NEAR : Operator::NONE
                    );
                }
            } elseif ($aWord['country_code']) {
                // Filter country tokens that do not match restricted countries.
                if (!$aCountryCodes
                    || in_array($aWord['country_code'], $aCountryCodes)
                ) {
                    $oToken = new Token\Country($iId, $aWord['country_code']);
                }
            } else {
                $oToken = new Token\Word(
                    $iId,
                    $aWord['word_token'][0] != ' ',
                    (int) $aWord['count']
                );
            }

            if ($oToken) {
                $this->addToken($aWord['word_token'], $oToken);
            }
        }
    }

    /**
     * Inspecting unmatched tokens check if another variation of postcod exist. A
     * variation might be another normalization (e.g. needs space) or looking for
     * the broader/shortened postcode.
     *
     * @param string[] $aTokens       List of tokens to look up in the database.
     * @param string[] $aCountryCodes List of country restrictions.
     *
     * @return void
     */
    public function addAdditionalPostcodeTokens(&$aTokens, &$aCountryCodes)
    {
        foreach ($aTokens as $sToken) {
            if ($sToken[0] == ' ' && !$this->contains($sToken)) {
                if (!$aCountryCodes || in_array('us', $aCountryCodes)) {
                    // US, ZIP+4 codes. 49418-3076 => 49418
                    if (preg_match('/^ ([0-9]{5}) [0-9]{4}$/', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1], 'us')
                        );
                    }
                }
                if (!$aCountryCodes || in_array('br', $aCountryCodes)) {
                    // Brazil, 97043-105 => 97043
                    if (preg_match('/^ ([0-9]{5}) [0-9]{3}$/', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1], 'br')
                        );
                    }
                }
                if (!$aCountryCodes || in_array('ar', $aCountryCodes)) {
                    // Argentina, X5108DQG => X5108
                    if (preg_match('/^ ([A-Z]{4})[A-Z]{3}$/', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1], 'ar')
                        );
                    }
                }
                if (!$aCountryCodes || in_array('pt', $aCountryCodes)) {
                    // Argentina, 1200-095 => 1200
                    if (preg_match('/^ ([0-9]{4}) [0-9]{3}$/', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1], 'pt')
                        );
                    }
                }
                if (!$aCountryCodes || in_array('se', $aCountryCodes)) {
                    // Sweden, 761 60 => 76160 also 76160 => 761 60
                    // data is OSM is about 50:50 mix of 5 digit vs 3+2
                    if (preg_match('/^ ([1-9]{3}) ([0-9]{2})$/', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1].$aData[2], 'se')
                        );
                    }
                    if (preg_match('/^ ([1-9]{3})([0-9]{2})$/', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1].' '.$aData[2], 'se')
                        );
                    }
                }
                if (!$aCountryCodes || in_array('nl', $aCountryCodes)) {
                    // Nederlands, 1000 AP => 1000AP
                    if (preg_match('/^ ([0-9]{4}) ([A-Z]{2})$/i', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1].$aData[2], 'nl')
                        );
                    }
                }
                if (!$aCountryCodes || in_array('gb', $aCountryCodes)) {
                    // United Kingdom, TQ122DB => TQ12 2DB
                    if (preg_match('/^ ([A-PR-UWYZ0-9][A-HK-Y0-9][AEHMNPRTVXY0-9]?[ABEHMNPRVWXY0-9]?)([0-9][ABD-HJLN-UW-Z]{2})$/i', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1].' '.$aData[2], 'gb')
                        );
                    }
                }
                if (!$aCountryCodes || in_array('ca', $aCountryCodes)) {
                    // Canada, K7A 4R8 => K7A4R8
                    if (preg_match('/^ ([[ABCEGHJKLMNPRSTVXY][0-9][ABCEGHJKLMNPRSTVWXYZ])([0-9][ABCEGHJKLMNPRSTVWXYZ][0-9])$/i', $sToken, $aData)) {
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1].' '.$aData[2], 'ca')
                        );
                    }
                }
                if (!$aCountryCodes || in_array('pl', $aCountryCodes)) {
                    if (preg_match('/^ ([0-9]{2}) ?([0-9]{3})$/', $sToken, $aData)) {
                        // Poland, 12345 => 12-345, also 12 345 => 12-345 because postcodes
                        // in location_postcode table have those dashes
                        // https://en.wikipedia.org/wiki/List_of_postal_codes_in_Poland
                        $this->addToken(
                            $sToken,
                            new Token\Postcode(null, $aData[1].'-'.$aData[2], 'pl')
                        );
                    }
                }
            }
        }
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
