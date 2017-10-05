<?php

namespace Nominatim;

/**
 * Operators describing special searches.
 */
abstract final class Operator
{
    /// No operator selected.
    const NONE = -1;
    /// Search for POIs near the given place.
    const NEAR = 0;
    /// Search for POIS in the given place.
    const IN = 1;
    /// Search for POIS named as given.
    const NAME = 3;
    /// Search for postcodes.
    const POSTCODE = 4;
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
};
