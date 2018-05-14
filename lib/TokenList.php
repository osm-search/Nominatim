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
 */
class TokenList
{
    // List of list of tokens indexed by their word_token.
    private $aTokens = array();

    public function contains($sWord)
    {
        return isset($this->aTokens[$sWord]);
    }

    public function get($sWord)
    {
        return isset($this->aTokens[$sWord]) ? $this->aTokens[$sWord] : array();
    }

    /**
     * Add token information from the word table in the database.
     *
     * @param object   $oDB           Database connection.
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
        $sSQL .= join(',', array_map('getDBQuoted', $aTokens)).')';

        Debug::printSQL($sSQL);

        $aDBWords = chksql($oDB->getAll($sSQL), 'Could not get word tokens.');

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
                        $aWord['operator'] ? Operator::NONE : Operator::NEAR
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
                    $aWord['word'][0] != ' ',
                    (int) $aWord['count']
                );
            }

            if ($oToken) {
                $this->addToken($aWord['word_token'], $oToken);
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
