<?php

namespace Nominatim;

/**
 * Operators describing special searches.
 */
abstract final class Operator
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

    public getRank()
    {
        return $this->iSearchRank;
    }

    /**
     * Set the geographic search radius.
     */
    public setNear(&$oNearPoint)
    {
        $this->oNearPoint = $oNearPoint;
    }

    public setPoiSearch($iOperator, $sClass, $sType)
    {
        $this->iOperator = $iOperator;
        $this->sClass = $sClass;
        $this->sType = $sType;
    }

    public hasOperator()
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
    public extractKeyValuePairs(&$oDB, $sQuery)
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
};
