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

require_once(CONST_LibDir.'/SpecialSearchOperator.php');
require_once(CONST_LibDir.'/SearchContext.php');
require_once(CONST_LibDir.'/Result.php');

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
    /// True if the name is rare enough to force index use on name.
    private $bRareName = false;
    /// True if the name requires to be accompanied by address terms.
    private $bNameNeedsAddress = false;
    /// List of word ids making up the address of the object.
    private $aAddress = array();
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
    /// Global search constraints.
    private $oContext;

    // Temporary values used while creating the search description.

    /// Index of phrase currently processed.
    private $iNamePhrase = -1;

    /**
     * Create an empty search description.
     *
     * @param object $oContext Global context to use. Will be inherited by
     *                         all derived search objects.
     */
    public function __construct($oContext)
    {
        $this->oContext = $oContext;
    }

    /**
     * Get current search rank.
     *
     * The higher the search rank the lower the likelihood that the
     * search is a correct interpretation of the search query.
     *
     * @return integer Search rank.
     */
    public function getRank()
    {
        return $this->iSearchRank;
    }

    /**
     * Extract key/value pairs from a query.
     *
     * Key/value pairs are recognised if they are of the form [<key>=<value>].
     * If multiple terms of this kind are found then all terms are removed
     * but only the first is used for search.
     *
     * @param string $sQuery Original query string.
     *
     * @return string The query string with the special search patterns removed.
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

    /**
     * Check if the combination of parameters is sensible.
     *
     * @return bool True, if the search looks valid.
     */
    public function isValidSearch()
    {
        if (empty($this->aName)) {
            if ($this->sHouseNumber) {
                return false;
            }
            if (!$this->sClass && !$this->sCountryCode) {
                return false;
            }
        }
        if ($this->bNameNeedsAddress && empty($this->aAddress)) {
            return false;
        }

        return true;
    }

    /////////// Search building functions

    /**
     * Create a copy of this search description adding to search rank.
     *
     * @param integer $iTermCost  Cost to add to the current search rank.
     *
     * @return object Cloned search description.
     */
    public function clone($iTermCost)
    {
        $oSearch = clone $this;
        $oSearch->iSearchRank += $iTermCost;

        return $oSearch;
    }

    /**
     * Check if the search currently includes a name.
     *
     * @param bool bIncludeNonNames  If true stop-word tokens are taken into
     *                               account, too.
     *
     * @return bool True, if search has a name.
     */
    public function hasName($bIncludeNonNames = false)
    {
        return !empty($this->aName)
               || (!empty($this->aNameNonSearch) && $bIncludeNonNames);
    }

    /**
     * Check if the search currently includes an address term.
     *
     * @return bool True, if any address term is included, including stop-word
     *              terms.
     */
    public function hasAddress()
    {
        return !empty($this->aAddress) || !empty($this->aAddressNonSearch);
    }

    /**
     * Check if a country restriction is currently included in the search.
     *
     * @return bool True, if a country restriction is set.
     */
    public function hasCountry()
    {
        return $this->sCountryCode !== '';
    }

    /**
     * Check if a postcode is currently included in the search.
     *
     * @return bool True, if a postcode is set.
     */
    public function hasPostcode()
    {
        return $this->sPostcode !== '';
    }

    /**
     * Check if a house number is set for the search.
     *
     * @return bool True, if a house number is set.
     */
    public function hasHousenumber()
    {
        return $this->sHouseNumber !== '';
    }

    /**
     * Check if a special type of place is requested.
     *
     * param integer iOperator  When set, check for the particular
     *                          operator used for the special type.
     *
     * @return bool True, if speial type is requested or, if requested,
     *              a special type with the given operator.
     */
    public function hasOperator($iOperator = null)
    {
        return $iOperator === null ? $this->iOperator != Operator::NONE : $this->iOperator == $iOperator;
    }

    /**
     * Add the given token to the list of terms to search for in the address.
     *
     * @param integer iID       ID of term to add.
     * @param bool bSearchable  Term should be used to search for result
     *                          (i.e. term is not a stop word).
     */
    public function addAddressToken($iId, $bSearchable = true)
    {
        if ($bSearchable) {
            $this->aAddress[$iId] = $iId;
        } else {
            $this->aAddressNonSearch[$iId] = $iId;
        }
    }

    /**
     * Add the given full-word token to the list of terms to search for in the
     * name.
     *
     * @param interger iId    ID of term to add.
     * @param bool bRareName  True if the term is infrequent enough to not
     *                        require other constraints for efficient search.
     */
    public function addNameToken($iId, $bRareName)
    {
        $this->aName[$iId] = $iId;
        $this->bRareName = $bRareName;
        $this->bNameNeedsAddress = false;
    }

    /**
     * Add the given partial token to the list of terms to search for in
     * the name.
     *
     * @param integer iID            ID of term to add.
     * @param bool bSearchable       Term should be used to search for result
     *                               (i.e. term is not a stop word).
     * @param bool bNeedsAddress     True if the term is too unspecific to be used
     *                               in a stand-alone search without an address
     *                               to narrow down the search.
     * @param integer iPhraseNumber  Index of phrase, where the partial term
     *                               appears.
     */
    public function addPartialNameToken($iId, $bSearchable, $bNeedsAddress, $iPhraseNumber)
    {
        if (empty($this->aName)) {
            $this->bNameNeedsAddress = $bNeedsAddress;
        } elseif ($bSearchable && count($this->aName) >= 2) {
            $this->bNameNeedsAddress = false;
        } else {
            $this->bNameNeedsAddress &= $bNeedsAddress;
        }
        if ($bSearchable) {
            $this->aName[$iId] = $iId;
        } else {
            $this->aNameNonSearch[$iId] = $iId;
        }
        $this->iNamePhrase = $iPhraseNumber;
    }

    /**
     * Set country restriction for the search.
     *
     * @param string sCountryCode  Country code of country to restrict search to.
     */
    public function setCountry($sCountryCode)
    {
        $this->sCountryCode = $sCountryCode;
        $this->iNamePhrase = -1;
    }

    /**
     * Set postcode search constraint.
     *
     * @param string sPostcode  Postcode the result should have.
     */
    public function setPostcode($sPostcode)
    {
        $this->sPostcode = $sPostcode;
        $this->iNamePhrase = -1;
    }

    /**
     * Make this search a search for a postcode object.
     *
     * @param integer iId       Token Id for the postcode.
     * @param string sPostcode  Postcode to look for.
     */
    public function setPostcodeAsName($iId, $sPostcode)
    {
        $this->iOperator = Operator::POSTCODE;
        $this->aAddress = array_merge($this->aAddress, $this->aName);
        $this->aName = array($iId => $sPostcode);
        $this->bRareName = true;
        $this->iNamePhrase = -1;
    }

    /**
     * Set house number search cnstraint.
     *
     * @param string sNumber  House number the result should have.
     */
    public function setHousenumber($sNumber)
    {
        $this->sHouseNumber = $sNumber;
        $this->iNamePhrase = -1;
    }

    /**
     * Make this search a search for a house number.
     *
     * @param integer iId  Token Id for the house number.
     */
    public function setHousenumberAsName($iId)
    {
        $this->aAddress = array_merge($this->aAddress, $this->aName);
        $this->bRareName = false;
        $this->bNameNeedsAddress = true;
        $this->aName = array($iId => $iId);
        $this->iNamePhrase = -1;
    }

    /**
     * Make this search a POI search.
     *
     * In a POI search, objects are not (only) searched by their name
     * but also by the primary OSM key/value pair (class and type in Nominatim).
     *
     * @param integer $iOperator Type of POI search
     * @param string  $sClass    Class (or OSM tag key) of POI.
     * @param string  $sType     Type (or OSM tag value) of POI.
     *
     * @return void
     */
    public function setPoiSearch($iOperator, $sClass, $sType)
    {
        $this->iOperator = $iOperator;
        $this->sClass = $sClass;
        $this->sType = $sType;
        $this->iNamePhrase = -1;
    }

    public function getNamePhrase()
    {
        return $this->iNamePhrase;
    }

    /**
     * Get the global search context.
     *
     * @return object  Objects of global search constraints.
     */
    public function getContext()
    {
        return $this->oContext;
    }

    /////////// Query functions


    /**
     * Query database for places that match this search.
     *
     * @param object  $oDB      Nominatim::DB instance to use.
     * @param integer $iMinRank Minimum address rank to restrict search to.
     * @param integer $iMaxRank Maximum address rank to restrict search to.
     * @param integer $iLimit   Maximum number of results.
     *
     * @return mixed[] An array with two fields: IDs contains the list of
     *                 matching place IDs and houseNumber the houseNumber
     *                 if appicable or -1 if not.
     */
    public function query(&$oDB, $iMinRank, $iMaxRank, $iLimit)
    {
        $aResults = array();

        if ($this->sCountryCode
            && empty($this->aName)
            && !$this->iOperator
            && !$this->sClass
            && !$this->oContext->hasNearPoint()
        ) {
            // Just looking for a country - look it up
            if (4 >= $iMinRank && 4 <= $iMaxRank) {
                $aResults = $this->queryCountry($oDB);
            }
        } elseif (empty($this->aName) && empty($this->aAddress)) {
            // Neither name nor address? Then we must be
            // looking for a POI in a geographic area.
            if ($this->oContext->isBoundedSearch()) {
                $aResults = $this->queryNearbyPoi($oDB, $iLimit);
            }
        } elseif ($this->iOperator == Operator::POSTCODE) {
            // looking for postcode
            $aResults = $this->queryPostcode($oDB, $iLimit);
        } else {
            // Ordinary search:
            // First search for places according to name and address.
            $aResults = $this->queryNamedPlace(
                $oDB,
                $iMinRank,
                $iMaxRank,
                $iLimit
            );

            // finally get POIs if requested
            if ($this->sClass && !empty($aResults)) {
                $aResults = $this->queryPoiByOperator($oDB, $aResults, $iLimit);
            }
        }

        Debug::printDebugTable('Place IDs', $aResults);

        if (!empty($aResults) && $this->sPostcode) {
            $sPlaceIds = Result::joinIdsByTable($aResults, Result::TABLE_PLACEX);
            if ($sPlaceIds) {
                $sSQL = 'SELECT place_id FROM placex';
                $sSQL .= ' WHERE place_id in ('.$sPlaceIds.')';
                $sSQL .= " AND postcode != '".$this->sPostcode."'";
                Debug::printSQL($sSQL);
                $aFilteredPlaceIDs = $oDB->getCol($sSQL);
                if ($aFilteredPlaceIDs) {
                    foreach ($aFilteredPlaceIDs as $iPlaceId) {
                        $aResults[$iPlaceId]->iResultRank++;
                    }
                }
            }
        }

        return $aResults;
    }


    private function queryCountry(&$oDB)
    {
        $sSQL = 'SELECT place_id FROM placex ';
        $sSQL .= "WHERE country_code='".$this->sCountryCode."'";
        $sSQL .= ' AND rank_search = 4';
        if ($this->oContext->bViewboxBounded) {
            $sSQL .= ' AND ST_Intersects('.$this->oContext->sqlViewboxSmall.', geometry)';
        }
        $sSQL .= ' ORDER BY st_area(geometry) DESC LIMIT 1';

        Debug::printSQL($sSQL);

        $iPlaceId = $oDB->getOne($sSQL);

        $aResults = array();
        if ($iPlaceId) {
            $aResults[$iPlaceId] = new Result($iPlaceId);
        }

        return $aResults;
    }

    private function queryNearbyPoi(&$oDB, $iLimit)
    {
        if (!$this->sClass) {
            return array();
        }

        $aDBResults = array();
        $sPoiTable = $this->poiTable();

        if ($oDB->tableExists($sPoiTable)) {
            $sSQL = 'SELECT place_id FROM '.$sPoiTable.' ct';
            if ($this->oContext->sqlCountryList) {
                $sSQL .= ' JOIN placex USING (place_id)';
            }
            if ($this->oContext->hasNearPoint()) {
                $sSQL .= ' WHERE '.$this->oContext->withinSQL('ct.centroid');
            } elseif ($this->oContext->bViewboxBounded) {
                $sSQL .= ' WHERE ST_Contains('.$this->oContext->sqlViewboxSmall.', ct.centroid)';
            }
            if ($this->oContext->sqlCountryList) {
                $sSQL .= ' AND country_code in '.$this->oContext->sqlCountryList;
            }
            $sSQL .= $this->oContext->excludeSQL(' AND place_id');
            if ($this->oContext->sqlViewboxCentre) {
                $sSQL .= ' ORDER BY ST_Distance(';
                $sSQL .= $this->oContext->sqlViewboxCentre.', ct.centroid) ASC';
            } elseif ($this->oContext->hasNearPoint()) {
                $sSQL .= ' ORDER BY '.$this->oContext->distanceSQL('ct.centroid').' ASC';
            }
            $sSQL .= " LIMIT $iLimit";
            Debug::printSQL($sSQL);
            $aDBResults = $oDB->getCol($sSQL);
        }

        if ($this->oContext->hasNearPoint()) {
            $sSQL = 'SELECT place_id FROM placex WHERE ';
            $sSQL .= 'class = :class and type = :type';
            $sSQL .= ' AND '.$this->oContext->withinSQL('geometry');
            $sSQL .= ' AND linked_place_id is null';
            if ($this->oContext->sqlCountryList) {
                $sSQL .= ' AND country_code in '.$this->oContext->sqlCountryList;
            }
            $sSQL .= ' ORDER BY '.$this->oContext->distanceSQL('centroid').' ASC';
            $sSQL .= " LIMIT $iLimit";
            Debug::printSQL($sSQL);
            $aDBResults = $oDB->getCol(
                $sSQL,
                array(':class' => $this->sClass, ':type' => $this->sType)
            );
        }

        $aResults = array();
        foreach ($aDBResults as $iPlaceId) {
            $aResults[$iPlaceId] = new Result($iPlaceId);
        }

        return $aResults;
    }

    private function queryPostcode(&$oDB, $iLimit)
    {
        $sSQL = 'SELECT p.place_id FROM location_postcode p ';

        if (!empty($this->aAddress)) {
            $sSQL .= ', search_name s ';
            $sSQL .= 'WHERE s.place_id = p.parent_place_id ';
            $sSQL .= 'AND array_cat(s.nameaddress_vector, s.name_vector)';
            $sSQL .= '      @> '.$oDB->getArraySQL($this->aAddress).' AND ';
        } else {
            $sSQL .= 'WHERE ';
        }

        $sSQL .= "p.postcode = '".reset($this->aName)."'";
        $sSQL .= $this->countryCodeSQL(' AND p.country_code');
        if ($this->oContext->bViewboxBounded) {
            $sSQL .= ' AND ST_Intersects('.$this->oContext->sqlViewboxSmall.', geometry)';
        }
        $sSQL .= $this->oContext->excludeSQL(' AND p.place_id');
        $sSQL .= " LIMIT $iLimit";

        Debug::printSQL($sSQL);

        $aResults = array();
        foreach ($oDB->getCol($sSQL) as $iPlaceId) {
            $aResults[$iPlaceId] = new Result($iPlaceId, Result::TABLE_POSTCODE);
        }

        return $aResults;
    }

    private function queryNamedPlace(&$oDB, $iMinAddressRank, $iMaxAddressRank, $iLimit)
    {
        $aTerms = array();
        $aOrder = array();

        if (!empty($this->aName)) {
            $aTerms[] = 'name_vector @> '.$oDB->getArraySQL($this->aName);
        }
        if (!empty($this->aAddress)) {
            // For infrequent name terms disable index usage for address
            if ($this->bRareName) {
                $aTerms[] = 'array_cat(nameaddress_vector,ARRAY[]::integer[]) @> '.$oDB->getArraySQL($this->aAddress);
            } else {
                $aTerms[] = 'nameaddress_vector @> '.$oDB->getArraySQL($this->aAddress);
            }
        }

        $sCountryTerm = $this->countryCodeSQL('country_code');
        if ($sCountryTerm) {
            $aTerms[] = $sCountryTerm;
        }

        if ($this->sHouseNumber) {
            $aTerms[] = 'address_rank between 16 and 30';
        } elseif (!$this->sClass || $this->iOperator == Operator::NAME) {
            if ($iMinAddressRank > 0) {
                $aTerms[] = "((address_rank between $iMinAddressRank and $iMaxAddressRank) or (search_rank between $iMinAddressRank and $iMaxAddressRank))";
            }
        }

        if ($this->oContext->hasNearPoint()) {
            $aTerms[] = $this->oContext->withinSQL('centroid');
            $aOrder[] = $this->oContext->distanceSQL('centroid');
        } elseif ($this->sPostcode) {
            if (empty($this->aAddress)) {
                $aTerms[] = "EXISTS(SELECT place_id FROM location_postcode p WHERE p.postcode = '".$this->sPostcode."' AND ST_DWithin(search_name.centroid, p.geometry, 0.12))";
            } else {
                $aOrder[] = "(SELECT min(ST_Distance(search_name.centroid, p.geometry)) FROM location_postcode p WHERE p.postcode = '".$this->sPostcode."')";
            }
        }

        $sExcludeSQL = $this->oContext->excludeSQL('place_id');
        if ($sExcludeSQL) {
            $aTerms[] = $sExcludeSQL;
        }

        if ($this->oContext->bViewboxBounded) {
            $aTerms[] = 'centroid && '.$this->oContext->sqlViewboxSmall;
        }

        if ($this->sHouseNumber) {
            $sImportanceSQL = '- abs(26 - address_rank) + 3';
        } else {
            $sImportanceSQL = '(CASE WHEN importance = 0 OR importance IS NULL THEN 0.75001-(search_rank::float/40) ELSE importance END)';
        }
        $sImportanceSQL .= $this->oContext->viewboxImportanceSQL('centroid');
        $aOrder[] = "$sImportanceSQL DESC";

        $aFullNameAddress = $this->oContext->getFullNameTerms();
        if (!empty($aFullNameAddress)) {
            $sExactMatchSQL = ' ( ';
            $sExactMatchSQL .= ' SELECT count(*) FROM ( ';
            $sExactMatchSQL .= '  SELECT unnest('.$oDB->getArraySQL($aFullNameAddress).')';
            $sExactMatchSQL .= '    INTERSECT ';
            $sExactMatchSQL .= '  SELECT unnest(nameaddress_vector)';
            $sExactMatchSQL .= ' ) s';
            $sExactMatchSQL .= ') as exactmatch';
            $aOrder[] = 'exactmatch DESC';
        } else {
            $sExactMatchSQL = '0::int as exactmatch';
        }

        if (empty($aTerms)) {
            return array();
        }

        if ($this->hasHousenumber()) {
            $sHouseNumberRegex = $oDB->getDBQuoted('\\\\m'.$this->sHouseNumber.'\\\\M');

            // Housenumbers on streets and places.
            $sPlacexSql = 'SELECT array_agg(place_id) FROM placex';
            $sPlacexSql .= ' WHERE parent_place_id = sin.place_id AND sin.address_rank < 30';
            $sPlacexSql .= $this->oContext->excludeSQL(' AND place_id');
            $sPlacexSql .= '       and housenumber ~* E'.$sHouseNumberRegex;

            // Interpolations on streets and places.
            $sInterpolSql = 'null';
            $sTigerSql = 'null';
            if (preg_match('/^[0-9]+$/', $this->sHouseNumber)) {
                $sIpolHnr = 'WHERE parent_place_id = sin.place_id ';
                $sIpolHnr .= '  AND startnumber is not NULL AND sin.address_rank < 30';
                $sIpolHnr .= '  AND '.$this->sHouseNumber.' between startnumber and endnumber';
                $sIpolHnr .= '  AND ('.$this->sHouseNumber.' - startnumber) % step = 0';

                $sInterpolSql = 'SELECT array_agg(place_id) FROM location_property_osmline '.$sIpolHnr;
                if (CONST_Use_US_Tiger_Data) {
                    $sTigerSql = 'SELECT array_agg(place_id) FROM location_property_tiger '.$sIpolHnr;
                    $sTigerSql .= "      and sin.country_code = 'us'";
                }
            }

            if ($this->sClass) {
                $iLimit = 40;
            }

            $sSelfHnr = 'SELECT * FROM placex WHERE place_id = search_name.place_id';
            $sSelfHnr .= '    AND housenumber ~* E'.$sHouseNumberRegex;

            $aTerms[] = '(address_rank < 30 or exists('.$sSelfHnr.'))';


            $sSQL = 'SELECT sin.*, ';
            $sSQL .=        '('.$sPlacexSql.') as placex_hnr, ';
            $sSQL .=        '('.$sInterpolSql.') as interpol_hnr, ';
            $sSQL .=        '('.$sTigerSql.') as tiger_hnr ';
            $sSQL .= ' FROM (';
            $sSQL .= '    SELECT place_id, address_rank, country_code,'.$sExactMatchSQL.',';
            $sSQL .= '            CASE WHEN importance = 0 OR importance IS NULL';
            $sSQL .= '               THEN 0.75001-(search_rank::float/40) ELSE importance END as importance';
            $sSQL .= '     FROM search_name';
            $sSQL .= '     WHERE '.join(' and ', $aTerms);
            $sSQL .= '     ORDER BY '.join(', ', $aOrder);
            $sSQL .= '     LIMIT 40000';
            $sSQL .= ') as sin';
            $sSQL .= ' ORDER BY address_rank = 30 desc, placex_hnr, interpol_hnr, tiger_hnr,';
            $sSQL .= '          importance';
            $sSQL .= ' LIMIT '.$iLimit;
        } else {
            if ($this->sClass) {
                $iLimit = 40;
            }

            $sSQL = 'SELECT place_id, address_rank, '.$sExactMatchSQL;
            $sSQL .= ' FROM search_name';
            $sSQL .= ' WHERE '.join(' and ', $aTerms);
            $sSQL .= ' ORDER BY '.join(', ', $aOrder);
            $sSQL .= ' LIMIT '.$iLimit;
        }

        Debug::printSQL($sSQL);

        $aDBResults = $oDB->getAll($sSQL, null, 'Could not get places for search terms.');

        $aResults = array();

        foreach ($aDBResults as $aResult) {
            $oResult = new Result($aResult['place_id']);
            $oResult->iExactMatches = $aResult['exactmatch'];
            $oResult->iAddressRank = $aResult['address_rank'];

            $bNeedResult = true;
            if ($this->hasHousenumber() && $aResult['address_rank'] < 30) {
                if ($aResult['placex_hnr']) {
                    foreach (explode(',', substr($aResult['placex_hnr'], 1, -1)) as $sPlaceID) {
                        $iPlaceID = intval($sPlaceID);
                        $oHnrResult = new Result($iPlaceID);
                        $oHnrResult->iExactMatches = $aResult['exactmatch'];
                        $oHnrResult->iAddressRank = 30;
                        $aResults[$iPlaceID] = $oHnrResult;
                        $bNeedResult = false;
                    }
                }
                if ($aResult['interpol_hnr']) {
                    foreach (explode(',', substr($aResult['interpol_hnr'], 1, -1)) as $sPlaceID) {
                        $iPlaceID = intval($sPlaceID);
                        $oHnrResult = new Result($iPlaceID, Result::TABLE_OSMLINE);
                        $oHnrResult->iExactMatches = $aResult['exactmatch'];
                        $oHnrResult->iAddressRank = 30;
                        $oHnrResult->iHouseNumber = intval($this->sHouseNumber);
                        $aResults[$iPlaceID] = $oHnrResult;
                        $bNeedResult = false;
                    }
                }
                if ($aResult['tiger_hnr']) {
                    foreach (explode(',', substr($aResult['tiger_hnr'], 1, -1)) as $sPlaceID) {
                        $iPlaceID = intval($sPlaceID);
                        $oHnrResult = new Result($iPlaceID, Result::TABLE_TIGER);
                        $oHnrResult->iExactMatches = $aResult['exactmatch'];
                        $oHnrResult->iAddressRank = 30;
                        $oHnrResult->iHouseNumber = intval($this->sHouseNumber);
                        $aResults[$iPlaceID] = $oHnrResult;
                        $bNeedResult = false;
                    }
                }

                if ($aResult['address_rank'] < 26) {
                    $oResult->iResultRank += 2;
                } else {
                    $oResult->iResultRank++;
                }
            }

            if ($bNeedResult) {
                $aResults[$aResult['place_id']] = $oResult;
            }
        }

        return $aResults;
    }


    private function queryPoiByOperator(&$oDB, $aParentIDs, $iLimit)
    {
        $aResults = array();
        $sPlaceIDs = Result::joinIdsByTable($aParentIDs, Result::TABLE_PLACEX);

        if (!$sPlaceIDs) {
            return $aResults;
        }

        if ($this->iOperator == Operator::TYPE || $this->iOperator == Operator::NAME) {
            // If they were searching for a named class (i.e. 'Kings Head pub')
            // then we might have an extra match
            $sSQL = 'SELECT place_id FROM placex ';
            $sSQL .= " WHERE place_id in ($sPlaceIDs)";
            $sSQL .= "   AND class='".$this->sClass."' ";
            $sSQL .= "   AND type='".$this->sType."'";
            $sSQL .= '   AND linked_place_id is null';
            $sSQL .= $this->oContext->excludeSQL(' AND place_id');
            $sSQL .= ' ORDER BY rank_search ASC ';
            $sSQL .= " LIMIT $iLimit";

            Debug::printSQL($sSQL);

            foreach ($oDB->getCol($sSQL) as $iPlaceId) {
                $aResults[$iPlaceId] = new Result($iPlaceId);
            }
        }

        // NEAR and IN are handled the same
        if ($this->iOperator == Operator::TYPE || $this->iOperator == Operator::NEAR) {
            $sClassTable = $this->poiTable();
            $bCacheTable = $oDB->tableExists($sClassTable);

            $sSQL = "SELECT min(rank_search) FROM placex WHERE place_id in ($sPlaceIDs)";
            Debug::printSQL($sSQL);
            $iMaxRank = (int) $oDB->getOne($sSQL);

            // For state / country level searches the normal radius search doesn't work very well
            $sPlaceGeom = false;
            if ($iMaxRank < 9 && $bCacheTable) {
                // Try and get a polygon to search in instead
                $sSQL = 'SELECT geometry FROM placex';
                $sSQL .= " WHERE place_id in ($sPlaceIDs)";
                $sSQL .= "   AND rank_search < $iMaxRank + 5";
                $sSQL .= "   AND ST_GeometryType(geometry) in ('ST_Polygon','ST_MultiPolygon')";
                $sSQL .= ' ORDER BY rank_search ASC ';
                $sSQL .= ' LIMIT 1';
                Debug::printSQL($sSQL);
                $sPlaceGeom = $oDB->getOne($sSQL);
            }

            if ($sPlaceGeom) {
                $sPlaceIDs = false;
            } else {
                $iMaxRank += 5;
                $sSQL = 'SELECT place_id FROM placex';
                $sSQL .= " WHERE place_id in ($sPlaceIDs) and rank_search < $iMaxRank";
                Debug::printSQL($sSQL);
                $aPlaceIDs = $oDB->getCol($sSQL);
                $sPlaceIDs = join(',', $aPlaceIDs);
            }

            if ($sPlaceIDs || $sPlaceGeom) {
                $fRange = 0.01;
                if ($bCacheTable) {
                    // More efficient - can make the range bigger
                    $fRange = 0.05;

                    $sOrderBySQL = '';
                    if ($this->oContext->hasNearPoint()) {
                        $sOrderBySQL = $this->oContext->distanceSQL('l.centroid');
                    } elseif ($sPlaceIDs) {
                        $sOrderBySQL = 'ST_Distance(l.centroid, f.geometry)';
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
                        $sSQL .= ',placex as f WHERE ';
                        $sSQL .= "f.place_id in ($sPlaceIDs) ";
                        $sSQL .= " AND ST_DWithin(l.centroid, f.centroid, $fRange)";
                    } elseif ($sPlaceGeom) {
                        $sSQL .= " WHERE ST_Contains('$sPlaceGeom', l.centroid)";
                    }

                    $sSQL .= $this->oContext->excludeSQL(' AND l.place_id');
                    $sSQL .= 'limit 300) i ';
                    if ($sOrderBySQL) {
                        $sSQL .= 'order by order_term asc';
                    }
                    $sSQL .= " limit $iLimit";

                    Debug::printSQL($sSQL);

                    foreach ($oDB->getCol($sSQL) as $iPlaceId) {
                        $aResults[$iPlaceId] = new Result($iPlaceId);
                    }
                } else {
                    if ($this->oContext->hasNearPoint()) {
                        $fRange = $this->oContext->nearRadius();
                    }

                    $sOrderBySQL = '';
                    if ($this->oContext->hasNearPoint()) {
                        $sOrderBySQL = $this->oContext->distanceSQL('l.geometry');
                    } else {
                        $sOrderBySQL = 'ST_Distance(l.geometry, f.geometry)';
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
                    $sSQL .= $this->oContext->excludeSQL(' AND l.place_id');
                    if ($sOrderBySQL) {
                        $sSQL .= 'ORDER BY orderterm ASC';
                    }
                    $sSQL .= " limit $iLimit";

                    Debug::printSQL($sSQL);

                    foreach ($oDB->getCol($sSQL) as $iPlaceId) {
                        $aResults[$iPlaceId] = new Result($iPlaceId);
                    }
                }
            }
        }

        return $aResults;
    }

    private function poiTable()
    {
        return 'place_classtype_'.$this->sClass.'_'.$this->sType;
    }

    private function countryCodeSQL($sVar)
    {
        if ($this->sCountryCode) {
            return $sVar.' = \''.$this->sCountryCode."'";
        }
        if ($this->oContext->sqlCountryList) {
            return $sVar.' in '.$this->oContext->sqlCountryList;
        }

        return '';
    }

    /////////// Sort functions


    public static function bySearchRank($a, $b)
    {
        if ($a->iSearchRank == $b->iSearchRank) {
            return $a->iOperator + strlen($a->sHouseNumber)
                     - $b->iOperator - strlen($b->sHouseNumber);
        }

        return $a->iSearchRank < $b->iSearchRank ? -1 : 1;
    }

    //////////// Debugging functions


    public function debugInfo()
    {
        return array(
                'Search rank' => $this->iSearchRank,
                'Country code' => $this->sCountryCode,
                'Name terms' => $this->aName,
                'Name terms (stop words)' => $this->aNameNonSearch,
                'Address terms' => $this->aAddress,
                'Address terms (stop words)' => $this->aAddressNonSearch,
                'Address terms (full words)' => $this->aFullNameAddress ?? '',
                'Special search' => $this->iOperator,
                'Class' => $this->sClass,
                'Type' => $this->sType,
                'House number' => $this->sHouseNumber,
                'Postcode' => $this->sPostcode
               );
    }

    public function dumpAsHtmlTableRow(&$aWordIDs)
    {
        $kf = function ($k) use (&$aWordIDs) {
            return $aWordIDs[$k] ?? '['.$k.']';
        };

        echo '<tr>';
        echo "<td>$this->iSearchRank</td>";
        echo '<td>'.join(', ', array_map($kf, $this->aName)).'</td>';
        echo '<td>'.join(', ', array_map($kf, $this->aNameNonSearch)).'</td>';
        echo '<td>'.join(', ', array_map($kf, $this->aAddress)).'</td>';
        echo '<td>'.join(', ', array_map($kf, $this->aAddressNonSearch)).'</td>';
        echo '<td>'.$this->sCountryCode.'</td>';
        echo '<td>'.Operator::toString($this->iOperator).'</td>';
        echo '<td>'.$this->sClass.'</td>';
        echo '<td>'.$this->sType.'</td>';
        echo '<td>'.$this->sPostcode.'</td>';
        echo '<td>'.$this->sHouseNumber.'</td>';

        echo '</tr>';
    }
}
