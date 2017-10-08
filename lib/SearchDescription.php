<?php

namespace Nominatim;

/**
 * Operators describing special searches.
 */
abstract class Operator
{
    /// No operator selected.
    const NONE = 0;
    /// Search for POI of the given type.
    const TYPE = 1;
    /// Search for POIs near the given place.
    const NEAR = 2;
    /// Search for POIS in the given place.
    const IN = 3;
    /// Search for POIS named as given.
    const NAME = 4;
    /// Search for postcodes.
    const POSTCODE = 5;

    private static $aConstantNames = null;

    public static function toString($iOperator)
    {
        if ($iOperator == Operator::NONE) {
            return '';
        }

        if (Operator::$aConstantNames === null) {
            $oReflector = new \ReflectionClass ('Nominatim\Operator');
            $aConstants = $oReflector->getConstants();

            Operator::$aConstantNames = array();
            foreach ($aConstants as $sName => $iValue) {
                Operator::$aConstantNames[$iValue] = $sName;
            }
        }

        return Operator::$aConstantNames[$iOperator];
    }
}

/**
 * Description of a single interpretation of a search query.
 */
class SearchDescription
{
    /// Ranking how well the description fits the query.
    private $iSearchRank = 0;
    /// Country code of country the result must belong to.
    private $sCountryCode = '';
    /// List of word ids making up the name of the object.
    private $aName = array();
    /// List of word ids making up the address of the object.
    private $aAddress = array();
    /// Subset of word ids of full words making up the address.
    private $aFullNameAddress = array();
    /// List of word ids that appear in the name but should be ignored.
    private $aNameNonSearch = array();
    /// List of word ids that appear in the address but should be ignored.
    private $aAddressNonSearch = array();
    /// Kind of search for special searches, see Nominatim::Operator.
    private $iOperator = Operator::NONE;
    /// Class of special feature to search for.
    private $sClass = '';
    /// Type of special feature to search for.
    private $sType = '';
    /// Housenumber of the object.
    private $sHouseNumber = '';
    /// Postcode for the object.
    private $sPostcode = '';
    /// Geographic search area.
    private $oNearPoint = false;

    // Temporary values used while creating the search description.

    /// Index of phrase currently processed
    private $iNamePhrase = -1;

    public function getRank()
    {
        return $this->iSearchRank;
    }

    public function addToRank($iAddRank)
    {
        $this->iSearchRank += $iAddRank;
        return $this->iSearchRank;
    }

    public function getPostCode()
    {
        return $this->sPostcode;
    }

    /**
     * Set the geographic search radius.
     */
    public function setNear(&$oNearPoint)
    {
        $this->oNearPoint = $oNearPoint;
    }

    public function setPoiSearch($iOperator, $sClass, $sType)
    {
        $this->iOperator = $iOperator;
        $this->sClass = $sClass;
        $this->sType = $sType;
    }

    /**
     * Check if name or address for the search are specified.
     */
    public function isNamedSearch()
    {
        return sizeof($this->aName) > 0 || sizeof($this->aAddress) > 0;
    }

    /**
     * Check if only a country is requested.
     */
    public function isCountrySearch()
    {
        return $this->sCountryCode && sizeof($this->aName) == 0
               && !$this->iOperator && !$this->oNearPoint;
    }

    /**
     * Check if a search near a geographic location is requested.
     */
    public function isNearSearch()
    {
        return (bool) $this->oNearPoint;
    }

    public function isPoiSearch()
    {
        return (bool) $this->sClass;
    }

    public function looksLikeFullAddress()
    {
        return sizeof($this->aName)
               && (sizeof($this->aAddress || $this->sCountryCode))
               && preg_match('/[0-9]+/', $this->sHouseNumber);
    }

    public function isOperator($iType)
    {
        return $this->iOperator == $iType;
    }

    public function hasHouseNumber()
    {
        return (bool) $this->sHouseNumber;
    }

    private function poiTable()
    {
        return 'place_classtype_'.$this->sClass.'_'.$this->sType;
    }

    public function countryCodeSQL($sVar, $sCountryList)
    {
        if ($this->sCountryCode) {
            return $sVar.' = \''.$this->sCountryCode."'";
        }
        if ($sCountryList) {
            return $sVar.' in ('.$sCountryList.')';
        }

        return '';
    }

    public function hasOperator()
    {
        return $this->iOperator != Operator::NONE;
    }

    /**
     * Extract special terms from the query, amend the search
     * and return the shortended query.
     *
     * Only the first special term found will be used but all will
     * be removed from the query.
     */
    public function extractKeyValuePairs($sQuery)
    {
        // Search for terms of kind [<key>=<value>].
        preg_match_all(
            '/\\[([\\w_]*)=([\\w_]*)\\]/',
            $sQuery,
            $aSpecialTermsRaw,
            PREG_SET_ORDER
        );

        foreach ($aSpecialTermsRaw as $aTerm) {
            $sQuery = str_replace($aTerm[0], ' ', $sQuery);
            if (!$this->hasOperator()) {
                $this->setPoiSearch(Operator::TYPE, $aTerm[1], $aTerm[2]);
            }
        }

        return $sQuery;
    }

    public function isValidSearch(&$aCountryCodes)
    {
        if (!sizeof($this->aName)) {
            if ($this->sHouseNumber) {
                return false;
            }
        }
        if ($aCountryCodes
            && $this->sCountryCode
            && !in_array($this->sCountryCode, $aCountryCodes)
        ) {
            return false;
        }

        return true;
    }

    /////////// Search building functions

    public function extendWithFullTerm($aSearchTerm, $bWordInQuery, $bHasPartial, $sPhraseType, $bFirstToken, $bFirstPhrase, $bLastToken, &$iGlobalRank)
    {
        $aNewSearches = array();

        if (($sPhraseType == '' || $sPhraseType == 'country')
            && !empty($aSearchTerm['country_code'])
            && $aSearchTerm['country_code'] != '0'
        ) {
            if (!$this->sCountryCode) {
                $oSearch = clone $this;
                $oSearch->iSearchRank++;
                $oSearch->sCountryCode = $aSearchTerm['country_code'];
                // Country is almost always at the end of the string
                // - increase score for finding it anywhere else (optimisation)
                if (!$bLastToken) {
                    $oSearch->iSearchRank += 5;
                }
                $aNewSearches[] = $oSearch;

                // If it is at the beginning, we can be almost sure that
                // the terms are in the wrong order. Increase score for all searches.
                if ($bFirstToken) {
                    $iGlobalRank++;
                }
            }
        } elseif (($sPhraseType == '' || $sPhraseType == 'postalcode')
                  && $aSearchTerm['class'] == 'place' && $aSearchTerm['type'] == 'postcode'
        ) {
            // We need to try the case where the postal code is the primary element
            // (i.e. no way to tell if it is (postalcode, city) OR (city, postalcode)
            // so try both.
            if (!$this->sPostcode && $bWordInQuery) {
                // If we have structured search or this is the first term,
                // make the postcode the primary search element.
                if ($this->iOperator == Operator::NONE
                    && ($sPhraseType == 'postalcode' || $bFirstToken)
                ) {
                    $oSearch = clone $this;
                    $oSearch->iSearchRank++;
                    $oSearch->iOperator = Operator::POSTCODE;
                    $oSearch->aAddress = array_merge($this->aAddress, $this->aName);
                    $oSearch->aName =
                        array($aSearchTerm['word_id'] => $aSearchTerm['word']);
                    $aNewSearches[] = $oSearch;
                }

                // If we have a structured search or this is not the first term,
                // add the postcode as an addendum.
                if ($this->iOperator != Operator::POSTCODE
                    && ($sPhraseType == 'postalcode' || sizeof($this->aName))
                ) {
                    $oSearch = clone $this;
                    $oSearch->iSearchRank++;
                    $oSearch->sPostcode = $aSearchTerm['word'];
                    $aNewSearches[] = $oSearch;
                }
            }
        } elseif (($sPhraseType == '' || $sPhraseType == 'street')
                 && $aSearchTerm['class'] == 'place' && $aSearchTerm['type'] == 'house'
        ) {
            if (!$this->sHouseNumber && $this->iOperator != Operator::POSTCODE) {
                $oSearch = clone $this;
                $oSearch->iSearchRank++;
                $oSearch->sHouseNumber = trim($aSearchTerm['word_token']);
                // sanity check: if the housenumber is not mainly made
                // up of numbers, add a penalty
                if (preg_match_all("/[^0-9]/", $oSearch->sHouseNumber, $aMatches) > 2) {
                    $oSearch->iSearchRank++;
                }
                // also must not appear in the middle of the address
                if (sizeof($this->aAddress) || sizeof($this->aAddressNonSearch)) {
                    $oSearch->iSearchRank++;
                }
                $aNewSearches[] = $oSearch;
            }
        } elseif ($sPhraseType == ''
                  && $aSearchTerm['class'] !== '' && $aSearchTerm['class'] !== null
        ) {
            // require a normalized exact match of the term
            // if we have the normalizer version of the query
            // available
            if ($this->iOperator == Operator::NONE
                && (isset($aSearchTerm['word']) && $aSearchTerm['word'])
                && $bWordInQuery
            ) {
                $oSearch = clone $this;
                $oSearch->iSearchRank++;

                $iOp = Operator::NEAR; // near == in for the moment
                if ($aSearchTerm['operator'] == '') {
                    if (sizeof($this->aName)) {
                        $iOp = Operator::NAME;
                    }
                    $oSearch->iSearchRank += 2;
                }

                $oSearch->setPoiSearch($iOp, $aSearchTerm['class'], $aSearchTerm['type']);
                $aNewSearches[] = $oSearch;
            }
        } elseif (isset($aSearchTerm['word_id']) && $aSearchTerm['word_id']) {
            $iWordID = $aSearchTerm['word_id'];
            if (sizeof($this->aName)) {
                if (($sPhraseType == '' || !$bFirstPhrase)
                    && $sPhraseType != 'country'
                    && !$bHasPartial
                ) {
                    $oSearch = clone $this;
                    $oSearch->iSearchRank++;
                    $oSearch->aAddress[$iWordID] = $iWordID;
                    $aNewSearches[] = $oSearch;
                }
                else {
                    $this->aFullNameAddress[$iWordID] = $iWordID;
                }
            } else {
                $oSearch = clone $this;
                $oSearch->iSearchRank++;
                $oSearch->aName = array($iWordID => $iWordID);
                $aNewSearches[] = $oSearch;
            }
        }

        return $aNewSearches;
    }

    public function extendWithPartialTerm($aSearchTerm, $bStructuredPhrases, $iPhrase, &$aWordFrequencyScores, $aFullTokens)
    {
        // Only allow name terms.
        if (!(isset($aSearchTerm['word_id']) && $aSearchTerm['word_id'])) {
            return array();
        }

        $aNewSearches = array();
        $iWordID = $aSearchTerm['word_id'];

        if ((!$bStructuredPhrases || $iPhrase > 0)
            && sizeof($this->aName)
            && strpos($aSearchTerm['word_token'], ' ') === false
        ) {
            if ($aWordFrequencyScores[$iWordID] < CONST_Max_Word_Frequency) {
                $oSearch = clone $this;
                $oSearch->iSearchRank++;
                $oSearch->aAddress[$iWordID] = $iWordID;
                $aNewSearches[] = $oSearch;
            } else {
                $oSearch = clone $this;
                $oSearch->iSearchRank++;
                $oSearch->aAddressNonSearch[$iWordID] = $iWordID;
                if (preg_match('#^[0-9]+$#', $aSearchTerm['word_token'])) {
                    $oSearch->iSearchRank += 2;
                }
                if (sizeof($aFullTokens)) {
                    $oSearch->iSearchRank++;
                }
                $aNewSearches[] = $oSearch;

                // revert to the token version?
                foreach ($aFullTokens as $aSearchTermToken) {
                    if (empty($aSearchTermToken['country_code'])
                        && empty($aSearchTermToken['lat'])
                        && empty($aSearchTermToken['class'])
                    ) {
                        $oSearch = clone $this;
                        $oSearch->iSearchRank++;
                        $oSearch->aAddress[$aSearchTermToken['word_id']] = $aSearchTermToken['word_id'];
                        $aNewSearches[] = $oSearch;
                    }
                }
            } 
        }

        if ((!$this->sPostcode && !$this->aAddress && !$this->aAddressNonSearch)
            && (!sizeof($this->aName) || $this->iNamePhrase == $iPhrase)
        ) {
            $oSearch = clone $this;
            $oSearch->iSearchRank++;
            if (!sizeof($this->aName)) {
                $oSearch->iSearchRank += 1;
            }
            if (preg_match('#^[0-9]+$#', $aSearchTerm['word_token'])) {
                $oSearch->iSearchRank += 2;
            }
            if ($aWordFrequencyScores[$iWordID] < CONST_Max_Word_Frequency) {
                $oSearch->aName[$iWordID] = $iWordID;
            } else {
                $oSearch->aNameNonSearch[$iWordID] = $iWordID;
            }
            $oSearch->iNamePhrase = $iPhrase;
            $aNewSearches[] = $oSearch;
        }

        return $aNewSearches;
    }

    /////////// Query functions

    public function queryCountry(&$oDB, $sViewboxSQL)
    {
        $sSQL = 'SELECT place_id FROM placex ';
        $sSQL .= "WHERE country_code='".$this->sCountryCode."'";
        $sSQL .= ' AND rank_search = 4';
        if ($sViewboxSQL) {
            $sSQL .= " AND ST_Intersects($sViewboxSQL, geometry)";
        }
        $sSQL .= " ORDER BY st_area(geometry) DESC LIMIT 1";

        if (CONST_Debug) var_dump($sSQL);

        return chksql($oDB->getCol($sSQL));
    }

    public function queryNearbyPoi(&$oDB, $sCountryList, $sViewboxSQL, $sViewboxCentreSQL, $sExcludeSQL, $iLimit)
    {
        if (!$this->sClass) {
            return array();
        }

        $sPoiTable = $this->poiTable();

        $sSQL = 'SELECT count(*) FROM pg_tables WHERE tablename = \''.$sPoiTable."'";
        if (chksql($oDB->getOne($sSQL))) {
            $sSQL = 'SELECT place_id FROM '.$sPoiTable.' ct';
            if ($sCountryList) {
                $sSQL .= ' JOIN placex USING (place_id)';
            }
            if ($this->oNearPoint) {
                $sSQL .= ' WHERE '.$this->oNearPoint->withinSQL('ct.centroid');
            } else {
                $sSQL .= " WHERE ST_Contains($sViewboxSQL, ct.centroid)";
            }
            if ($sCountryList) {
                $sSQL .= " AND country_code in ($sCountryList)";
            }
            if ($sExcludeSQL) {
                $sSQL .= ' AND place_id not in ('.$sExcludeSQL.')';
            }
            if ($sViewboxCentreSQL) {
                $sSQL .= " ORDER BY ST_Distance($sViewboxCentreSQL, ct.centroid) ASC";
            } elseif ($this->oNearPoint) {
                $sSQL .= ' ORDER BY '.$this->oNearPoint->distanceSQL('ct.centroid').' ASC';
            }
            $sSQL .= " limit $iLimit";
            if (CONST_Debug) var_dump($sSQL);
            return chksql($oDB->getCol($sSQL));
        }

        if ($this->oNearPoint) {
            $sSQL = 'SELECT place_id FROM placex WHERE ';
            $sSQL .= 'class=\''.$this->sClass."' and type='".$this->sType."'";
            $sSQL .= ' AND '.$this->oNearPoint->withinSQL('geometry');
            $sSQL .= ' AND linked_place_id is null';
            if ($sCountryList) {
                $sSQL .= " AND country_code in ($sCountryList)";
            }
            $sSQL .= ' ORDER BY '.$this->oNearPoint->distanceSQL('centroid')." ASC";
            $sSQL .= " LIMIT $iLimit";
            if (CONST_Debug) var_dump($sSQL);
            return chksql($oDB->getCol($sSQL));
        }

        return array();
    }

    public function queryPostcode(&$oDB, $sCountryList, $iLimit)
    {
        $sSQL  = 'SELECT p.place_id FROM location_postcode p ';

        if (sizeof($this->aAddress)) {
            $sSQL .= ', search_name s ';
            $sSQL .= 'WHERE s.place_id = p.parent_place_id ';
            $sSQL .= 'AND array_cat(s.nameaddress_vector, s.name_vector)';
            $sSQL .= '      @> '.getArraySQL($this->aAddress).' AND ';
        } else {
            $sSQL .= 'WHERE ';
        }

        $sSQL .= "p.postcode = '".pg_escape_string(reset($this->aName))."'";
        $sCountryTerm = $this->countryCodeSQL('p.country_code', $sCountryList);
        if ($sCountryTerm) {
            $sSQL .= ' AND '.$sCountryTerm;
        }
        $sSQL .= " LIMIT $iLimit";

        if (CONST_Debug) var_dump($sSQL);

        return chksql($oDB->getCol($sSQL));
    }

    public function queryNamedPlace(&$oDB, $aWordFrequencyScores, $sCountryList, $iMinAddressRank, $iMaxAddressRank, $sExcludeSQL, $sViewboxSmall, $sViewboxLarge, $iLimit)
    {
        $aTerms = array();
        $aOrder = array();

        if ($this->sHouseNumber && sizeof($this->aAddress)) {
            $sHouseNumberRegex = '\\\\m'.$this->sHouseNumber.'\\\\M';
            $aOrder[] = ' (';
            $aOrder[0] .= 'EXISTS(';
            $aOrder[0] .= '  SELECT place_id';
            $aOrder[0] .= '  FROM placex';
            $aOrder[0] .= '  WHERE parent_place_id = search_name.place_id';
            $aOrder[0] .= "    AND transliteration(housenumber) ~* E'".$sHouseNumberRegex."'";
            $aOrder[0] .= '  LIMIT 1';
            $aOrder[0] .= ') ';
            // also housenumbers from interpolation lines table are needed
            if (preg_match('/[0-9]+/', $this->sHouseNumber)) {
                $iHouseNumber = intval($this->sHouseNumber);
                $aOrder[0] .= 'OR EXISTS(';
                $aOrder[0] .= '  SELECT place_id ';
                $aOrder[0] .= '  FROM location_property_osmline ';
                $aOrder[0] .= '  WHERE parent_place_id = search_name.place_id';
                $aOrder[0] .= '    AND startnumber is not NULL';
                $aOrder[0] .= '    AND '.$iHouseNumber.'>=startnumber ';
                $aOrder[0] .= '    AND '.$iHouseNumber.'<=endnumber ';
                $aOrder[0] .= '  LIMIT 1';
                $aOrder[0] .= ')';
            }
            $aOrder[0] .= ') DESC';
        }

        if (sizeof($this->aName)) {
            $aTerms[] = 'name_vector @> '.getArraySQL($this->aName);
        }
        if (sizeof($this->aAddress)) {
            // For infrequent name terms disable index usage for address
            if (CONST_Search_NameOnlySearchFrequencyThreshold
                && sizeof($this->aName) == 1
                && $aWordFrequencyScores[$this->aName[reset($this->aName)]]
                     < CONST_Search_NameOnlySearchFrequencyThreshold
            ) {
                $aTerms[] = 'array_cat(nameaddress_vector,ARRAY[]::integer[]) @> '.getArraySQL($this->aAddress);
            } else {
                $aTerms[] = 'nameaddress_vector @> '.getArraySQL($this->aAddress);
            }
        }

        $sCountryTerm = $this->countryCodeSQL('country_code', $sCountryList);
        if ($sCountryTerm) {
            $aTerms[] = $sCountryTerm;
        }

        if ($this->sHouseNumber) {
            $aTerms[] = "address_rank between 16 and 27";
        } elseif (!$this->sClass || $this->iOperator == Operator::NAME) {
            if ($iMinAddressRank > 0) {
                $aTerms[] = "address_rank >= ".$iMinAddressRank;
            }
            if ($iMaxAddressRank < 30) {
                $aTerms[] = "address_rank <= ".$iMaxAddressRank;
            }
        }

        if ($this->oNearPoint) {
            $aTerms[] = $this->oNearPoint->withinSQL('centroid');
            $aOrder[] = $this->oNearPoint->distanceSQL('centroid');
        } elseif ($this->sPostcode) {
            if (!sizeof($this->aAddress)) {
                $aTerms[] = "EXISTS(SELECT place_id FROM location_postcode p WHERE p.postcode = '".$this->sPostcode."' AND ST_DWithin(search_name.centroid, p.geometry, 0.1))";
            } else {
                $aOrder[] = "(SELECT min(ST_Distance(search_name.centroid, p.geometry)) FROM location_postcode p WHERE p.postcode = '".$this->sPostcode."')";
            }
        }

        if ($sExcludeSQL) {
            $aTerms[] = 'place_id not in ('.$sExcludeSQL.')';
        }

        if ($sViewboxSmall) {
           $aTerms[] = 'centroid && '.$sViewboxSmall;
        }

        if ($this->oNearPoint) {
            $aOrder[] = $this->oNearPoint->distanceSQL('centroid');
        }

        if ($this->sHouseNumber) {
            $sImportanceSQL = '- abs(26 - address_rank) + 3';
        } else {
            $sImportanceSQL = '(CASE WHEN importance = 0 OR importance IS NULL THEN 0.75-(search_rank::float/40) ELSE importance END)';
        }
        if ($sViewboxSmall) {
            $sImportanceSQL .= " * CASE WHEN ST_Contains($sViewboxSmall, centroid) THEN 1 ELSE 0.5 END";
        }
        if ($sViewboxLarge) {
            $sImportanceSQL .= " * CASE WHEN ST_Contains($sViewboxLarge, centroid) THEN 1 ELSE 0.5 END";
        }
        $aOrder[] = "$sImportanceSQL DESC";

        if (sizeof($this->aFullNameAddress)) {
            $sExactMatchSQL = ' ( ';
            $sExactMatchSQL .= ' SELECT count(*) FROM ( ';
            $sExactMatchSQL .= '  SELECT unnest('.getArraySQL($this->aFullNameAddress).')';
            $sExactMatchSQL .= '    INTERSECT ';
            $sExactMatchSQL .= '  SELECT unnest(nameaddress_vector)';
            $sExactMatchSQL .= ' ) s';
            $sExactMatchSQL .= ') as exactmatch';
            $aOrder[] = 'exactmatch DESC';
        } else {
            $sExactMatchSQL = '0::int as exactmatch';
        }

        if ($this->sHouseNumber || $this->sClass) {
            $iLimit = 20;
        }

        if (sizeof($aTerms)) {
            $sSQL = 'SELECT place_id,'.$sExactMatchSQL;
            $sSQL .= ' FROM search_name';
            $sSQL .= ' WHERE '.join(' and ', $aTerms);
            $sSQL .= ' ORDER BY '.join(', ', $aOrder);
            $sSQL .= ' LIMIT '.$iLimit;

            if (CONST_Debug) var_dump($sSQL);

            return chksql(
                $oDB->getAll($sSQL),
                "Could not get places for search terms."
            );
        }

        return array();
    }


    public function queryHouseNumber(&$oDB, $aRoadPlaceIDs, $sExcludeSQL, $iLimit)
    {
        $sPlaceIDs = join(',', $aRoadPlaceIDs);

        $sHouseNumberRegex = '\\\\m'.$this->sHouseNumber.'\\\\M';
        $sSQL = 'SELECT place_id FROM placex ';
        $sSQL .= 'WHERE parent_place_id in ('.$sPlaceIDs.')';
        $sSQL .= "  AND transliteration(housenumber) ~* E'".$sHouseNumberRegex."'";
        if ($sExcludeSQL) {
            $sSQL .= ' AND place_id not in ('.$sExcludeSQL.')';
        }
        $sSQL .= " LIMIT $iLimit";

        if (CONST_Debug) var_dump($sSQL);

        $aPlaceIDs = chksql($oDB->getCol($sSQL));

        if (sizeof($aPlaceIDs)) {
            return array('aPlaceIDs' => $aPlaceIDs, 'iHouseNumber' => -1);
        }

        $bIsIntHouseNumber= (bool) preg_match('/[0-9]+/', $this->sHouseNumber);
        $iHousenumber = intval($this->sHouseNumber);
        if ($bIsIntHouseNumber) {
            // if nothing found, search in the interpolation line table
            $sSQL = 'SELECT distinct place_id FROM location_property_osmline';
            $sSQL .= ' WHERE startnumber is not NULL';
            $sSQL .= '  AND parent_place_id in ('.$sPlaceIDs.') AND (';
            if ($iHousenumber % 2 == 0) {
                // If housenumber is even, look for housenumber in streets
                // with interpolationtype even or all.
                $sSQL .= "interpolationtype='even'";
            } else {
                // Else look for housenumber with interpolationtype odd or all.
                $sSQL .= "interpolationtype='odd'";
            }
            $sSQL .= " or interpolationtype='all') and ";
            $sSQL .= $iHousenumber.">=startnumber and ";
            $sSQL .= $iHousenumber."<=endnumber";

            if ($sExcludeSQL) {
                $sSQL .= ' AND place_id not in ('.$sExcludeSQL.')';
            }
            $sSQL .= " limit $iLimit";

            if (CONST_Debug) var_dump($sSQL);

            $aPlaceIDs = chksql($oDB->getCol($sSQL, 0));

            if (sizeof($aPlaceIDs)) {
                return array('aPlaceIDs' => $aPlaceIDs, 'iHouseNumber' => $iHousenumber);
            }
        }

        // If nothing found try the aux fallback table
        if (CONST_Use_Aux_Location_data) {
            $sSQL = 'SELECT place_id FROM location_property_aux';
            $sSQL .= ' WHERE parent_place_id in ('.$sPlaceIDs.')';
            $sSQL .= " AND housenumber = '".$this->sHouseNumber."'";
            if ($sExcludeSQL) {
                $sSQL .= " AND place_id not in ($sExcludeSQL)";
            }
            $sSQL .= " limit $iLimit";

            if (CONST_Debug) var_dump($sSQL);

            $aPlaceIDs = chksql($oDB->getCol($sSQL));

            if (sizeof($aPlaceIDs)) {
                return array('aPlaceIDs' => $aPlaceIDs, 'iHouseNumber' => -1);
            }
        }

        // If nothing found then search in Tiger data (location_property_tiger)
        if (CONST_Use_US_Tiger_Data && $bIsIntHouseNumber) {
            $sSQL = 'SELECT distinct place_id FROM location_property_tiger';
            $sSQL .= ' WHERE parent_place_id in ('.$sPlaceIDs.') and (';
            if ($iHousenumber % 2 == 0) {
                $sSQL .= "interpolationtype='even'";
            } else {
                $sSQL .= "interpolationtype='odd'";
            }
            $sSQL .= " or interpolationtype='all') and ";
            $sSQL .= $iHousenumber.">=startnumber and ";
            $sSQL .= $iHousenumber."<=endnumber";

            if ($sExcludeSQL) {
                $sSQL .= ' AND place_id not in ('.$sExcludeSQL.')';
            }
            $sSQL .= " limit $iLimit";

            if (CONST_Debug) var_dump($sSQL);

            $aPlaceIDs = chksql($oDB->getCol($sSQL, 0));

            if (sizeof($aPlaceIDs)) {
                return array('aPlaceIDs' => $aPlaceIDs, 'iHouseNumber' => $iHousenumber);
            }
        }

        return array();
    }


    public function queryPoiByOperator(&$oDB, $aParentIDs, $sExcludeSQL, $iLimit)
    {
        $sPlaceIDs = join(',', $aParentIDs);
        $aClassPlaceIDs = array();

        if ($this->iOperator == Operator::TYPE || $this->iOperator == Operator::NAME) {
            // If they were searching for a named class (i.e. 'Kings Head pub')
            // then we might have an extra match
            $sSQL = 'SELECT place_id FROM placex ';
            $sSQL .= " WHERE place_id in ($sPlaceIDs)";
            $sSQL .= "   AND class='".$this->sClass."' ";
            $sSQL .= "   AND type='".$this->sType."'";
            $sSQL .= "   AND linked_place_id is null";
            $sSQL .= " ORDER BY rank_search ASC ";
            $sSQL .= " LIMIT $iLimit";

            if (CONST_Debug) var_dump($sSQL);

            $aClassPlaceIDs = chksql($oDB->getCol($sSQL));
        }

        // NEAR and IN are handled the same
        if ($this->iOperator == Operator::TYPE || $this->iOperator == Operator::NEAR) {
            $sClassTable = $this->poiTable();
            $sSQL = "SELECT count(*) FROM pg_tables WHERE tablename = '$sClassTable'";
            $bCacheTable = (bool) chksql($oDB->getOne($sSQL));

            $sSQL = "SELECT min(rank_search) FROM placex WHERE place_id in ($sPlaceIDs)";
            if (CONST_Debug) var_dump($sSQL);
            $iMaxRank = (int)chksql($oDB->getOne($sSQL));

            // For state / country level searches the normal radius search doesn't work very well
            $sPlaceGeom = false;
            if ($iMaxRank < 9 && $bCacheTable) {
                // Try and get a polygon to search in instead
                $sSQL = 'SELECT geometry FROM placex';
                $sSQL .= " WHERE place_id in ($sPlaceIDs)";
                $sSQL .= "   AND rank_search < $iMaxRank + 5";
                $sSQL .= "   AND ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon')";
                $sSQL .= " ORDER BY rank_search ASC ";
                $sSQL .= " LIMIT 1";
                if (CONST_Debug) var_dump($sSQL);
                $sPlaceGeom = chksql($oDB->getOne($sSQL));
            }

            if ($sPlaceGeom) {
                $sPlaceIDs = false;
            } else {
                $iMaxRank += 5;
                $sSQL = 'SELECT place_id FROM placex';
                $sSQL .= " WHERE place_id in ($sPlaceIDs) and rank_search < $iMaxRank";
                if (CONST_Debug) var_dump($sSQL);
                $aPlaceIDs = chksql($oDB->getCol($sSQL));
                $sPlaceIDs = join(',', $aPlaceIDs);
            }

            if ($sPlaceIDs || $sPlaceGeom) {
                $fRange = 0.01;
                if ($bCacheTable) {
                    // More efficient - can make the range bigger
                    $fRange = 0.05;

                    $sOrderBySQL = '';
                    if ($this->oNearPoint) {
                        $sOrderBySQL = $this->oNearPoint->distanceSQL('l.centroid');
                    } elseif ($sPlaceIDs) {
                        $sOrderBySQL = "ST_Distance(l.centroid, f.geometry)";
                    } elseif ($sPlaceGeom) {
                        $sOrderBySQL = "ST_Distance(st_centroid('".$sPlaceGeom."'), l.centroid)";
                    }

                    $sSQL = 'SELECT distinct i.place_id';
                    if ($sOrderBySQL) {
                        $sSQL .= ', i.order_term';
                    }
                    $sSQL .= ' from (SELECT l.place_id';
                    if ($sOrderBySQL) {
                        $sSQL .= ','.$sOrderBySQL.' as order_term';
                    }
                    $sSQL .= ' from '.$sClassTable.' as l';

                    if ($sPlaceIDs) {
                        $sSQL .= ",placex as f WHERE ";
                        $sSQL .= "f.place_id in ($sPlaceIDs) ";
                        $sSQL .= " AND ST_DWithin(l.centroid, f.centroid, $fRange)";
                    } elseif ($sPlaceGeom) {
                        $sSQL .= " WHERE ST_Contains('$sPlaceGeom', l.centroid)";
                    }

                    if ($sExcludeSQL) {
                        $sSQL .= ' AND l.place_id not in ('.$sExcludeSQL.')';
                    }
                    $sSQL .= 'limit 300) i ';
                    if ($sOrderBySQL) {
                        $sSQL .= 'order by order_term asc';
                    }
                    $sSQL .= " limit $iLimit";

                    if (CONST_Debug) var_dump($sSQL);

                    $aClassPlaceIDs = array_merge($aClassPlaceIDs, chksql($oDB->getCol($sSQL)));
                } else {
                    if ($this->oNearPoint) {
                        $fRange = $this->oNearPoint->radius();
                    }

                    $sOrderBySQL = '';
                    if ($this->oNearPoint) {
                        $sOrderBySQL = $this->oNearPoint->distanceSQL('l.geometry');
                    } else {
                        $sOrderBySQL = "ST_Distance(l.geometry, f.geometry)";
                    }

                    $sSQL = 'SELECT distinct l.place_id';
                    if ($sOrderBySQL) {
                        $sSQL .= ','.$sOrderBySQL.' as orderterm';
                    }
                    $sSQL .= ' FROM placex as l, placex as f';
                    $sSQL .= " WHERE f.place_id in ($sPlaceIDs)";
                    $sSQL .= "  AND ST_DWithin(l.geometry, f.centroid, $fRange)";
                    $sSQL .= "  AND l.class='".$this->sClass."'";
                    $sSQL .= "  AND l.type='".$this->sType."'";
                    if ($sExcludeSQL) {
                        $sSQL .= " AND l.place_id not in (".$sExcludeSQL.")";
                    }
                    if ($sOrderBySQL) {
                        $sSQL .= "ORDER BY orderterm ASC";
                    }
                    $sSQL .= " limit $iLimit";

                    if (CONST_Debug) var_dump($sSQL);

                    $aClassPlaceIDs = array_merge($aClassPlaceIDs, chksql($oDB->getCol($sSQL)));
                }
            }
        }

        return $aClassPlaceIDs;
    }


    /////////// Sort functions

    static function bySearchRank($a, $b)
    {
        if ($a->iSearchRank == $b->iSearchRank) {
            return $a->iOperator + strlen($a->sHouseNumber)
                     - $b->iOperator - strlen($b->sHouseNumber);
        }

        return $a->iSearchRank < $b->iSearchRank ? -1 : 1;
    }

    //////////// Debugging functions

    function dumpAsHtmlTableRow(&$aWordIDs)
    {
        $kf = function($k) use (&$aWordIDs) { return $aWordIDs[$k]; };

        echo "<tr>";
        echo "<td>$this->iSearchRank</td>";
        echo "<td>".join(', ', array_map($kf, $this->aName))."</td>";
        echo "<td>".join(', ', array_map($kf, $this->aNameNonSearch))."</td>";
        echo "<td>".join(', ', array_map($kf, $this->aAddress))."</td>";
        echo "<td>".join(', ', array_map($kf, $this->aAddressNonSearch))."</td>";
        echo "<td>".$this->sCountryCode."</td>";
        echo "<td>".Operator::toString($this->iOperator)."</td>";
        echo "<td>".$this->sClass."</td>";
        echo "<td>".$this->sType."</td>";
        echo "<td>".$this->sPostcode."</td>";
        echo "<td>".$this->sHouseNumber."</td>";

        if ($this->oNearPoint) {
            echo "<td>".$this->oNearPoint->lat()."</td>";
            echo "<td>".$this->oNearPoint->lon()."</td>";
            echo "<td>".$this->oNearPoint->radius()."</td>";
        } else {
            echo "<td></td><td></td><td></td>";
        }

        echo "</tr>";
    }
};
