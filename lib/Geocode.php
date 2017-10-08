<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/PlaceLookup.php');
require_once(CONST_BasePath.'/lib/ReverseGeocode.php');
require_once(CONST_BasePath.'/lib/SearchDescription.php');
require_once(CONST_BasePath.'/lib/SearchContext.php');

class Geocode
{
    protected $oDB;

    protected $aLangPrefOrder = array();

    protected $bIncludeAddressDetails = false;
    protected $bIncludeExtraTags = false;
    protected $bIncludeNameDetails = false;

    protected $bIncludePolygonAsPoints = false;
    protected $bIncludePolygonAsText = false;
    protected $bIncludePolygonAsGeoJSON = false;
    protected $bIncludePolygonAsKML = false;
    protected $bIncludePolygonAsSVG = false;
    protected $fPolygonSimplificationThreshold = 0.0;

    protected $aExcludePlaceIDs = array();
    protected $bDeDupe = true;
    protected $bReverseInPlan = false;

    protected $iLimit = 20;
    protected $iFinalLimit = 10;
    protected $iOffset = 0;
    protected $bFallback = false;

    protected $aCountryCodes = false;

    protected $bBoundedSearch = false;
    protected $aViewBox = false;
    protected $sViewboxCentreSQL = false;
    protected $sViewboxSmallSQL = false;
    protected $sViewboxLargeSQL = false;

    protected $iMaxRank = 20;
    protected $iMinAddressRank = 0;
    protected $iMaxAddressRank = 30;
    protected $aAddressRankList = array();
    protected $exactMatchCache = array();

    protected $sAllowedTypesSQLList = false;

    protected $sQuery = false;
    protected $aStructuredQuery = false;

    protected $oNormalizer = null;


    public function __construct(&$oDB)
    {
        $this->oDB =& $oDB;
        $this->oNormalizer = \Transliterator::createFromRules(CONST_Term_Normalization_Rules);
    }

    private function normTerm($sTerm)
    {
        if ($this->oNormalizer === null) {
            return $sTerm;
        }

        return $this->oNormalizer->transliterate($sTerm);
    }

    public function setReverseInPlan($bReverse)
    {
        $this->bReverseInPlan = $bReverse;
    }

    public function setLanguagePreference($aLangPref)
    {
        $this->aLangPrefOrder = $aLangPref;
    }

    public function getMoreUrlParams()
    {
        if ($this->aStructuredQuery) {
            $aParams = $this->aStructuredQuery;
        } else {
            $aParams = array('q' => $this->sQuery);
        }

        if ($this->aExcludePlaceIDs) {
            $aParams['exclude_place_ids'] = implode(',', $this->aExcludePlaceIDs);
        }

        if ($this->bIncludeAddressDetails) $aParams['addressdetails'] = '1';
        if ($this->bIncludeExtraTags) $aParams['extratags'] = '1';
        if ($this->bIncludeNameDetails) $aParams['namedetails'] = '1';

        if ($this->bIncludePolygonAsPoints) $aParams['polygon'] = '1';
        if ($this->bIncludePolygonAsText) $aParams['polygon_text'] = '1';
        if ($this->bIncludePolygonAsGeoJSON) $aParams['polygon_geojson'] = '1';
        if ($this->bIncludePolygonAsKML) $aParams['polygon_kml'] = '1';
        if ($this->bIncludePolygonAsSVG) $aParams['polygon_svg'] = '1';

        if ($this->fPolygonSimplificationThreshold > 0.0) {
            $aParams['polygon_threshold'] = $this->fPolygonSimplificationThreshold;
        }

        if ($this->bBoundedSearch) $aParams['bounded'] = '1';
        if (!$this->bDeDupe) $aParams['dedupe'] = '0';

        if ($this->aCountryCodes) {
            $aParams['countrycodes'] = implode(',', $this->aCountryCodes);
        }

        if ($this->aViewBox) {
            $aParams['viewbox'] = $this->aViewBox[0].','.$this->aViewBox[3]
                                  .','.$this->aViewBox[2].','.$this->aViewBox[1];
        }

        return $aParams;
    }

    public function setIncludePolygonAsPoints($b = true)
    {
        $this->bIncludePolygonAsPoints = $b;
    }

    public function setIncludePolygonAsText($b = true)
    {
        $this->bIncludePolygonAsText = $b;
    }

    public function setIncludePolygonAsGeoJSON($b = true)
    {
        $this->bIncludePolygonAsGeoJSON = $b;
    }

    public function setIncludePolygonAsKML($b = true)
    {
        $this->bIncludePolygonAsKML = $b;
    }

    public function setIncludePolygonAsSVG($b = true)
    {
        $this->bIncludePolygonAsSVG = $b;
    }

    public function setPolygonSimplificationThreshold($f)
    {
        $this->fPolygonSimplificationThreshold = $f;
    }

    public function setLimit($iLimit = 10)
    {
        if ($iLimit > 50) $iLimit = 50;
        if ($iLimit < 1) $iLimit = 1;

        $this->iFinalLimit = $iLimit;
        $this->iLimit = $iLimit + min($iLimit, 10);
    }

    public function setFeatureType($sFeatureType)
    {
        switch ($sFeatureType) {
            case 'country':
                $this->setRankRange(4, 4);
                break;
            case 'state':
                $this->setRankRange(8, 8);
                break;
            case 'city':
                $this->setRankRange(14, 16);
                break;
            case 'settlement':
                $this->setRankRange(8, 20);
                break;
        }
    }

    public function setRankRange($iMin, $iMax)
    {
        $this->iMinAddressRank = $iMin;
        $this->iMaxAddressRank = $iMax;
    }

    public function setRoute($aRoutePoints, $fRouteWidth)
    {
        $this->aViewBox = false;

        $this->sViewboxCentreSQL = "ST_SetSRID('LINESTRING(";
        $sSep = '';
        foreach ($aRoutePoints as $aPoint) {
            $fPoint = (float)$aPoint;
            $this->sViewboxCentreSQL .= $sSep.$fPoint;
            $sSep = ($sSep == ' ') ? ',' : ' ';
        }
        $this->sViewboxCentreSQL .= ")'::geometry,4326)";

        $this->sViewboxSmallSQL = 'ST_BUFFER('.$this->sViewboxCentreSQL;
        $this->sViewboxSmallSQL .= ','.($fRouteWidth/69).')';

        $this->sViewboxLargeSQL = 'ST_BUFFER('.$this->sViewboxCentreSQL;
        $this->sViewboxLargeSQL .= ','.($fRouteWidth/30).')';
    }

    public function setViewbox($aViewbox)
    {
        $this->aViewBox = array_map('floatval', $aViewbox);

        $this->aViewBox[0] = max(-180.0, min(180, $this->aViewBox[0]));
        $this->aViewBox[1] = max(-90.0, min(90, $this->aViewBox[1]));
        $this->aViewBox[2] = max(-180.0, min(180, $this->aViewBox[2]));
        $this->aViewBox[3] = max(-90.0, min(90, $this->aViewBox[3]));

        if (abs($this->aViewBox[0] - $this->aViewBox[2]) < 0.000000001
            || abs($this->aViewBox[1] - $this->aViewBox[3]) < 0.000000001
        ) {
            userError("Bad parameter 'viewbox'. Not a box.");
        }

        $fHeight = $this->aViewBox[0] - $this->aViewBox[2];
        $fWidth = $this->aViewBox[1] - $this->aViewBox[3];
        $aBigViewBox[0] = $this->aViewBox[0] + $fHeight;
        $aBigViewBox[2] = $this->aViewBox[2] - $fHeight;
        $aBigViewBox[1] = $this->aViewBox[1] + $fWidth;
        $aBigViewBox[3] = $this->aViewBox[3] - $fWidth;

        $this->sViewboxCentreSQL = false;
        $this->sViewboxSmallSQL = sprintf(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(%F,%F),ST_Point(%F,%F)),4326)',
            $this->aViewBox[0],
            $this->aViewBox[1],
            $this->aViewBox[2],
            $this->aViewBox[3]
        );
        $this->sViewboxLargeSQL = sprintf(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(%F,%F),ST_Point(%F,%F)),4326)',
            $aBigViewBox[0],
            $aBigViewBox[1],
            $aBigViewBox[2],
            $aBigViewBox[3]
        );
    }

    public function setQuery($sQueryString)
    {
        $this->sQuery = $sQueryString;
        $this->aStructuredQuery = false;
    }

    public function getQueryString()
    {
        return $this->sQuery;
    }


    public function loadParamArray($oParams)
    {
        $this->bIncludeAddressDetails
         = $oParams->getBool('addressdetails', $this->bIncludeAddressDetails);
        $this->bIncludeExtraTags
         = $oParams->getBool('extratags', $this->bIncludeExtraTags);
        $this->bIncludeNameDetails
         = $oParams->getBool('namedetails', $this->bIncludeNameDetails);

        $this->bBoundedSearch = $oParams->getBool('bounded', $this->bBoundedSearch);
        $this->bDeDupe = $oParams->getBool('dedupe', $this->bDeDupe);

        $this->setLimit($oParams->getInt('limit', $this->iFinalLimit));
        $this->iOffset = $oParams->getInt('offset', $this->iOffset);

        $this->bFallback = $oParams->getBool('fallback', $this->bFallback);

        // List of excluded Place IDs - used for more acurate pageing
        $sExcluded = $oParams->getStringList('exclude_place_ids');
        if ($sExcluded) {
            foreach ($sExcluded as $iExcludedPlaceID) {
                $iExcludedPlaceID = (int)$iExcludedPlaceID;
                if ($iExcludedPlaceID)
                    $aExcludePlaceIDs[$iExcludedPlaceID] = $iExcludedPlaceID;
            }

            if (isset($aExcludePlaceIDs))
                $this->aExcludePlaceIDs = $aExcludePlaceIDs;
        }

        // Only certain ranks of feature
        $sFeatureType = $oParams->getString('featureType');
        if (!$sFeatureType) $sFeatureType = $oParams->getString('featuretype');
        if ($sFeatureType) $this->setFeatureType($sFeatureType);

        // Country code list
        $sCountries = $oParams->getStringList('countrycodes');
        if ($sCountries) {
            foreach ($sCountries as $sCountryCode) {
                if (preg_match('/^[a-zA-Z][a-zA-Z]$/', $sCountryCode)) {
                    $aCountries[] = strtolower($sCountryCode);
                }
            }
            if (isset($aCountries))
                $this->aCountryCodes = $aCountries;
        }

        $aViewbox = $oParams->getStringList('viewboxlbrt');
        if ($aViewbox) {
            if (count($aViewbox) != 4) {
                userError("Bad parmater 'viewboxlbrt'. Expected 4 coordinates.");
            }
            $this->setViewbox($aViewbox);
        } else {
            $aViewbox = $oParams->getStringList('viewbox');
            if ($aViewbox) {
                if (count($aViewbox) != 4) {
                    userError("Bad parmater 'viewbox'. Expected 4 coordinates.");
                }
                $this->setViewBox($aViewbox);
            } else {
                $aRoute = $oParams->getStringList('route');
                $fRouteWidth = $oParams->getFloat('routewidth');
                if ($aRoute && $fRouteWidth) {
                    $this->setRoute($aRoute, $fRouteWidth);
                }
            }
        }
    }

    public function setQueryFromParams($oParams)
    {
        // Search query
        $sQuery = $oParams->getString('q');
        if (!$sQuery) {
            $this->setStructuredQuery(
                $oParams->getString('amenity'),
                $oParams->getString('street'),
                $oParams->getString('city'),
                $oParams->getString('county'),
                $oParams->getString('state'),
                $oParams->getString('country'),
                $oParams->getString('postalcode')
            );
            $this->setReverseInPlan(false);
        } else {
            $this->setQuery($sQuery);
        }
    }

    public function loadStructuredAddressElement($sValue, $sKey, $iNewMinAddressRank, $iNewMaxAddressRank, $aItemListValues)
    {
        $sValue = trim($sValue);
        if (!$sValue) return false;
        $this->aStructuredQuery[$sKey] = $sValue;
        if ($this->iMinAddressRank == 0 && $this->iMaxAddressRank == 30) {
            $this->iMinAddressRank = $iNewMinAddressRank;
            $this->iMaxAddressRank = $iNewMaxAddressRank;
        }
        if ($aItemListValues) $this->aAddressRankList = array_merge($this->aAddressRankList, $aItemListValues);
        return true;
    }

    public function setStructuredQuery($sAmenity = false, $sStreet = false, $sCity = false, $sCounty = false, $sState = false, $sCountry = false, $sPostalCode = false)
    {
        $this->sQuery = false;

        // Reset
        $this->iMinAddressRank = 0;
        $this->iMaxAddressRank = 30;
        $this->aAddressRankList = array();

        $this->aStructuredQuery = array();
        $this->sAllowedTypesSQLList = false;

        $this->loadStructuredAddressElement($sAmenity, 'amenity', 26, 30, false);
        $this->loadStructuredAddressElement($sStreet, 'street', 26, 30, false);
        $this->loadStructuredAddressElement($sCity, 'city', 14, 24, false);
        $this->loadStructuredAddressElement($sCounty, 'county', 9, 13, false);
        $this->loadStructuredAddressElement($sState, 'state', 8, 8, false);
        $this->loadStructuredAddressElement($sPostalCode, 'postalcode', 5, 11, array(5, 11));
        $this->loadStructuredAddressElement($sCountry, 'country', 4, 4, false);

        if (sizeof($this->aStructuredQuery) > 0) {
            $this->sQuery = join(', ', $this->aStructuredQuery);
            if ($this->iMaxAddressRank < 30) {
                $this->sAllowedTypesSQLList = '(\'place\',\'boundary\')';
            }
        }
    }

    public function fallbackStructuredQuery()
    {
        if (!$this->aStructuredQuery) return false;

        $aParams = $this->aStructuredQuery;

        if (sizeof($aParams) == 1) return false;

        $aOrderToFallback = array('postalcode', 'street', 'city', 'county', 'state');

        foreach ($aOrderToFallback as $sType) {
            if (isset($aParams[$sType])) {
                unset($aParams[$sType]);
                $this->setStructuredQuery(@$aParams['amenity'], @$aParams['street'], @$aParams['city'], @$aParams['county'], @$aParams['state'], @$aParams['country'], @$aParams['postalcode']);
                return true;
            }
        }

        return false;
    }

    public function getDetails($aPlaceIDs)
    {
        //$aPlaceIDs is an array with key: placeID and value: tiger-housenumber, if found, else -1
        if (sizeof($aPlaceIDs) == 0) return array();

        $sLanguagePrefArraySQL = getArraySQL(
            array_map("getDBQuoted", $this->aLangPrefOrder)
        );

        // Get the details for display (is this a redundant extra step?)
        $sPlaceIDs = join(',', array_keys($aPlaceIDs));

        $sImportanceSQL = '';
        $sImportanceSQLGeom = '';
        if ($this->sViewboxSmallSQL) {
            $sImportanceSQL .= " CASE WHEN ST_Contains($this->sViewboxSmallSQL, ST_Collect(centroid)) THEN 1 ELSE 0.75 END * ";
            $sImportanceSQLGeom .= " CASE WHEN ST_Contains($this->sViewboxSmallSQL, geometry) THEN 1 ELSE 0.75 END * ";
        }
        if ($this->sViewboxLargeSQL) {
            $sImportanceSQL .= " CASE WHEN ST_Contains($this->sViewboxLargeSQL, ST_Collect(centroid)) THEN 1 ELSE 0.75 END * ";
            $sImportanceSQLGeom .= " CASE WHEN ST_Contains($this->sViewboxLargeSQL, geometry) THEN 1 ELSE 0.75 END * ";
        }

        $sSQL  = "SELECT ";
        $sSQL .= "    osm_type,";
        $sSQL .= "    osm_id,";
        $sSQL .= "    class,";
        $sSQL .= "    type,";
        $sSQL .= "    admin_level,";
        $sSQL .= "    rank_search,";
        $sSQL .= "    rank_address,";
        $sSQL .= "    min(place_id) AS place_id, ";
        $sSQL .= "    min(parent_place_id) AS parent_place_id, ";
        $sSQL .= "    country_code, ";
        $sSQL .= "    get_address_by_language(place_id, -1, $sLanguagePrefArraySQL) AS langaddress,";
        $sSQL .= "    get_name_by_language(name, $sLanguagePrefArraySQL) AS placename,";
        $sSQL .= "    get_name_by_language(name, ARRAY['ref']) AS ref,";
        if ($this->bIncludeExtraTags) $sSQL .= "hstore_to_json(extratags)::text AS extra,";
        if ($this->bIncludeNameDetails) $sSQL .= "hstore_to_json(name)::text AS names,";
        $sSQL .= "    avg(ST_X(centroid)) AS lon, ";
        $sSQL .= "    avg(ST_Y(centroid)) AS lat, ";
        $sSQL .= "    ".$sImportanceSQL."COALESCE(importance,0.75-(rank_search::float/40)) AS importance, ";
        $sSQL .= "    ( ";
        $sSQL .= "       SELECT max(p.importance*(p.rank_address+2))";
        $sSQL .= "       FROM ";
        $sSQL .= "         place_addressline s, ";
        $sSQL .= "         placex p";
        $sSQL .= "       WHERE s.place_id = min(CASE WHEN placex.rank_search < 28 THEN placex.place_id ELSE placex.parent_place_id END)";
        $sSQL .= "         AND p.place_id = s.address_place_id ";
        $sSQL .= "         AND s.isaddress ";
        $sSQL .= "         AND p.importance is not null ";
        $sSQL .= "    ) AS addressimportance, ";
        $sSQL .= "    (extratags->'place') AS extra_place ";
        $sSQL .= " FROM placex";
        $sSQL .= " WHERE place_id in ($sPlaceIDs) ";
        $sSQL .= "   AND (";
        $sSQL .= "            placex.rank_address between $this->iMinAddressRank and $this->iMaxAddressRank ";
        if (14 >= $this->iMinAddressRank && 14 <= $this->iMaxAddressRank) {
            $sSQL .= "        OR (extratags->'place') = 'city'";
        }
        if ($this->aAddressRankList) {
            $sSQL .= "        OR placex.rank_address in (".join(',', $this->aAddressRankList).")";
        }
        $sSQL .= "       ) ";
        if ($this->sAllowedTypesSQLList) {
            $sSQL .= "AND placex.class in $this->sAllowedTypesSQLList ";
        }
        $sSQL .= "    AND linked_place_id is null ";
        $sSQL .= " GROUP BY ";
        $sSQL .= "     osm_type, ";
        $sSQL .= "     osm_id, ";
        $sSQL .= "     class, ";
        $sSQL .= "     type, ";
        $sSQL .= "     admin_level, ";
        $sSQL .= "     rank_search, ";
        $sSQL .= "     rank_address, ";
        $sSQL .= "     country_code, ";
        $sSQL .= "     importance, ";
        if (!$this->bDeDupe) $sSQL .= "place_id,";
        $sSQL .= "     langaddress, ";
        $sSQL .= "     placename, ";
        $sSQL .= "     ref, ";
        if ($this->bIncludeExtraTags) $sSQL .= "extratags, ";
        if ($this->bIncludeNameDetails) $sSQL .= "name, ";
        $sSQL .= "     extratags->'place' ";

        // postcode table
        $sSQL .= "UNION ";
        $sSQL .= "SELECT";
        $sSQL .= "  'P' as osm_type,";
        $sSQL .= "  (SELECT osm_id from placex p WHERE p.place_id = lp.parent_place_id) as osm_id,";
        $sSQL .= "  'place' as class, 'postcode' as type,";
        $sSQL .= "  null as admin_level, rank_search, rank_address,";
        $sSQL .= "  place_id, parent_place_id, country_code,";
        $sSQL .= "  get_address_by_language(place_id, -1, $sLanguagePrefArraySQL) AS langaddress,";
        $sSQL .= "  postcode as placename,";
        $sSQL .= "  postcode as ref,";
        if ($this->bIncludeExtraTags) $sSQL .= "null AS extra,";
        if ($this->bIncludeNameDetails) $sSQL .= "null AS names,";
        $sSQL .= "  ST_x(st_centroid(geometry)) AS lon, ST_y(st_centroid(geometry)) AS lat,";
        $sSQL .=    $sImportanceSQLGeom."(0.75-(rank_search::float/40)) AS importance, ";
        $sSQL .= "  (";
        $sSQL .= "     SELECT max(p.importance*(p.rank_address+2))";
        $sSQL .= "     FROM ";
        $sSQL .= "       place_addressline s, ";
        $sSQL .= "       placex p";
        $sSQL .= "     WHERE s.place_id = lp.parent_place_id";
        $sSQL .= "       AND p.place_id = s.address_place_id ";
        $sSQL .= "       AND s.isaddress";
        $sSQL .= "       AND p.importance is not null";
        $sSQL .= "  ) AS addressimportance, ";
        $sSQL .= "  null AS extra_place ";
        $sSQL .= "FROM location_postcode lp";
        $sSQL .= " WHERE place_id in ($sPlaceIDs) ";

        if (30 >= $this->iMinAddressRank && 30 <= $this->iMaxAddressRank) {
            // only Tiger housenumbers and interpolation lines need to be interpolated, because they are saved as lines
            // with start- and endnumber, the common osm housenumbers are usually saved as points
            $sHousenumbers = "";
            $i = 0;
            $length = count($aPlaceIDs);
            foreach ($aPlaceIDs as $placeID => $housenumber) {
                $i++;
                $sHousenumbers .= "(".$placeID.", ".$housenumber.")";
                if ($i<$length) $sHousenumbers .= ", ";
            }

            if (CONST_Use_US_Tiger_Data) {
                // Tiger search only if a housenumber was searched and if it was found (i.e. aPlaceIDs[placeID] = housenumber != -1) (realized through a join)
                $sSQL .= " union";
                $sSQL .= " SELECT ";
                $sSQL .= "     'T' AS osm_type, ";
                $sSQL .= "     (SELECT osm_id from placex p WHERE p.place_id=min(blub.parent_place_id)) as osm_id, ";
                $sSQL .= "     'place' AS class, ";
                $sSQL .= "     'house' AS type, ";
                $sSQL .= "     null AS admin_level, ";
                $sSQL .= "     30 AS rank_search, ";
                $sSQL .= "     30 AS rank_address, ";
                $sSQL .= "     min(place_id) AS place_id, ";
                $sSQL .= "     min(parent_place_id) AS parent_place_id, ";
                $sSQL .= "     'us' AS country_code, ";
                $sSQL .= "     get_address_by_language(place_id, housenumber_for_place, $sLanguagePrefArraySQL) AS langaddress,";
                $sSQL .= "     null AS placename, ";
                $sSQL .= "     null AS ref, ";
                if ($this->bIncludeExtraTags) $sSQL .= "null AS extra,";
                if ($this->bIncludeNameDetails) $sSQL .= "null AS names,";
                $sSQL .= "     avg(st_x(centroid)) AS lon, ";
                $sSQL .= "     avg(st_y(centroid)) AS lat,";
                $sSQL .= "     ".$sImportanceSQL."-1.15 AS importance, ";
                $sSQL .= "     (";
                $sSQL .= "        SELECT max(p.importance*(p.rank_address+2))";
                $sSQL .= "        FROM ";
                $sSQL .= "          place_addressline s, ";
                $sSQL .= "          placex p";
                $sSQL .= "        WHERE s.place_id = min(blub.parent_place_id)";
                $sSQL .= "          AND p.place_id = s.address_place_id ";
                $sSQL .= "          AND s.isaddress";
                $sSQL .= "          AND p.importance is not null";
                $sSQL .= "     ) AS addressimportance, ";
                $sSQL .= "     null AS extra_place ";
                $sSQL .= " FROM (";
                $sSQL .= "     SELECT place_id, ";    // interpolate the Tiger housenumbers here
                $sSQL .= "         ST_LineInterpolatePoint(linegeo, (housenumber_for_place-startnumber::float)/(endnumber-startnumber)::float) AS centroid, ";
                $sSQL .= "         parent_place_id, ";
                $sSQL .= "         housenumber_for_place";
                $sSQL .= "     FROM (";
                $sSQL .= "            location_property_tiger ";
                $sSQL .= "            JOIN (values ".$sHousenumbers.") AS housenumbers(place_id, housenumber_for_place) USING(place_id)) ";
                $sSQL .= "     WHERE ";
                $sSQL .= "         housenumber_for_place>=0";
                $sSQL .= "         AND 30 between $this->iMinAddressRank AND $this->iMaxAddressRank";
                $sSQL .= " ) AS blub"; //postgres wants an alias here
                $sSQL .= " GROUP BY";
                $sSQL .= "      place_id, ";
                $sSQL .= "      housenumber_for_place"; //is this group by really needed?, place_id + housenumber (in combination) are unique
                if (!$this->bDeDupe) $sSQL .= ", place_id ";
            }
            // osmline
            // interpolation line search only if a housenumber was searched and if it was found (i.e. aPlaceIDs[placeID] = housenumber != -1) (realized through a join)
            $sSQL .= " UNION ";
            $sSQL .= "SELECT ";
            $sSQL .= "  'W' AS osm_type, ";
            $sSQL .= "  osm_id, ";
            $sSQL .= "  'place' AS class, ";
            $sSQL .= "  'house' AS type, ";
            $sSQL .= "  null AS admin_level, ";
            $sSQL .= "  30 AS rank_search, ";
            $sSQL .= "  30 AS rank_address, ";
            $sSQL .= "  min(place_id) as place_id, ";
            $sSQL .= "  min(parent_place_id) AS parent_place_id, ";
            $sSQL .= "  country_code, ";
            $sSQL .= "  get_address_by_language(place_id, housenumber_for_place, $sLanguagePrefArraySQL) AS langaddress, ";
            $sSQL .= "  null AS placename, ";
            $sSQL .= "  null AS ref, ";
            if ($this->bIncludeExtraTags) $sSQL .= "null AS extra, ";
            if ($this->bIncludeNameDetails) $sSQL .= "null AS names, ";
            $sSQL .= "  AVG(st_x(centroid)) AS lon, ";
            $sSQL .= "  AVG(st_y(centroid)) AS lat, ";
            $sSQL .= "  ".$sImportanceSQL."-0.1 AS importance, ";  // slightly smaller than the importance for normal houses with rank 30, which is 0
            $sSQL .= "  (";
            $sSQL .= "     SELECT ";
            $sSQL .= "       MAX(p.importance*(p.rank_address+2)) ";
            $sSQL .= "     FROM";
            $sSQL .= "       place_addressline s, ";
            $sSQL .= "       placex p";
            $sSQL .= "     WHERE s.place_id = min(blub.parent_place_id) ";
            $sSQL .= "       AND p.place_id = s.address_place_id ";
            $sSQL .= "       AND s.isaddress ";
            $sSQL .= "       AND p.importance is not null";
            $sSQL .= "  ) AS addressimportance,";
            $sSQL .= "  null AS extra_place ";
            $sSQL .= "  FROM (";
            $sSQL .= "     SELECT ";
            $sSQL .= "         osm_id, ";
            $sSQL .= "         place_id, ";
            $sSQL .= "         country_code, ";
            $sSQL .= "         CASE ";             // interpolate the housenumbers here
            $sSQL .= "           WHEN startnumber != endnumber ";
            $sSQL .= "           THEN ST_LineInterpolatePoint(linegeo, (housenumber_for_place-startnumber::float)/(endnumber-startnumber)::float) ";
            $sSQL .= "           ELSE ST_LineInterpolatePoint(linegeo, 0.5) ";
            $sSQL .= "         END as centroid, ";
            $sSQL .= "         parent_place_id, ";
            $sSQL .= "         housenumber_for_place ";
            $sSQL .= "     FROM (";
            $sSQL .= "            location_property_osmline ";
            $sSQL .= "            JOIN (values ".$sHousenumbers.") AS housenumbers(place_id, housenumber_for_place) USING(place_id)";
            $sSQL .= "          ) ";
            $sSQL .= "     WHERE housenumber_for_place>=0 ";
            $sSQL .= "       AND 30 between $this->iMinAddressRank AND $this->iMaxAddressRank";
            $sSQL .= "  ) as blub"; //postgres wants an alias here
            $sSQL .= "  GROUP BY ";
            $sSQL .= "    osm_id, ";
            $sSQL .= "    place_id, ";
            $sSQL .= "    housenumber_for_place, ";
            $sSQL .= "    country_code "; //is this group by really needed?, place_id + housenumber (in combination) are unique
            if (!$this->bDeDupe) $sSQL .= ", place_id ";

            if (CONST_Use_Aux_Location_data) {
                $sSQL .= " UNION ";
                $sSQL .= "  SELECT ";
                $sSQL .= "     'L' AS osm_type, ";
                $sSQL .= "     place_id AS osm_id, ";
                $sSQL .= "     'place' AS class,";
                $sSQL .= "     'house' AS type, ";
                $sSQL .= "     null AS admin_level, ";
                $sSQL .= "     0 AS rank_search,";
                $sSQL .= "     0 AS rank_address, ";
                $sSQL .= "     min(place_id) AS place_id,";
                $sSQL .= "     min(parent_place_id) AS parent_place_id, ";
                $sSQL .= "     'us' AS country_code, ";
                $sSQL .= "     get_address_by_language(place_id, -1, $sLanguagePrefArraySQL) AS langaddress, ";
                $sSQL .= "     null AS placename, ";
                $sSQL .= "     null AS ref, ";
                if ($this->bIncludeExtraTags) $sSQL .= "null AS extra, ";
                if ($this->bIncludeNameDetails) $sSQL .= "null AS names, ";
                $sSQL .= "     avg(ST_X(centroid)) AS lon, ";
                $sSQL .= "     avg(ST_Y(centroid)) AS lat, ";
                $sSQL .= "     ".$sImportanceSQL."-1.10 AS importance, ";
                $sSQL .= "     ( ";
                $sSQL .= "       SELECT max(p.importance*(p.rank_address+2))";
                $sSQL .= "       FROM ";
                $sSQL .= "          place_addressline s, ";
                $sSQL .= "          placex p";
                $sSQL .= "       WHERE s.place_id = min(location_property_aux.parent_place_id)";
                $sSQL .= "         AND p.place_id = s.address_place_id ";
                $sSQL .= "         AND s.isaddress";
                $sSQL .= "         AND p.importance is not null";
                $sSQL .= "     ) AS addressimportance, ";
                $sSQL .= "     null AS extra_place ";
                $sSQL .= "  FROM location_property_aux ";
                $sSQL .= "  WHERE place_id in ($sPlaceIDs) ";
                $sSQL .= "    AND 30 between $this->iMinAddressRank and $this->iMaxAddressRank ";
                $sSQL .= "  GROUP BY ";
                $sSQL .= "     place_id, ";
                if (!$this->bDeDupe) $sSQL .= "place_id, ";
                $sSQL .= "     get_address_by_language(place_id, -1, $sLanguagePrefArraySQL) ";
            }
        }

        $sSQL .= " order by importance desc";
        if (CONST_Debug) {
            echo "<hr>";
            var_dump($sSQL);
        }
        $aSearchResults = chksql(
            $this->oDB->getAll($sSQL),
            "Could not get details for place."
        );

        return $aSearchResults;
    }

    public function getGroupedSearches($aSearches, $aPhraseTypes, $aPhrases, $aValidTokens, $aWordFrequencyScores, $bStructuredPhrases, $sNormQuery)
    {
        /*
             Calculate all searches using aValidTokens i.e.
             'Wodsworth Road, Sheffield' =>

             Phrase Wordset
             0      0       (wodsworth road)
             0      1       (wodsworth)(road)
             1      0       (sheffield)

             Score how good the search is so they can be ordered
         */
        $iGlobalRank = 0;

        foreach ($aPhrases as $iPhrase => $aPhrase) {
            $aNewPhraseSearches = array();
            if ($bStructuredPhrases) {
                $sPhraseType = $aPhraseTypes[$iPhrase];
            } else {
                $sPhraseType = '';
            }

            foreach ($aPhrase['wordsets'] as $iWordSet => $aWordset) {
                // Too many permutations - too expensive
                if ($iWordSet > 120) break;

                $aWordsetSearches = $aSearches;

                // Add all words from this wordset
                foreach ($aWordset as $iToken => $sToken) {
                    //echo "<br><b>$sToken</b>";
                    $aNewWordsetSearches = array();

                    foreach ($aWordsetSearches as $oCurrentSearch) {
                        //echo "<i>";
                        //var_dump($oCurrentSearch);
                        //echo "</i>";

                        // If the token is valid
                        if (isset($aValidTokens[' '.$sToken])) {
                            foreach ($aValidTokens[' '.$sToken] as $aSearchTerm) {
                                // Recheck if the original word shows up in the query.
                                $bWordInQuery = false;
                                if (isset($aSearchTerm['word']) && $aSearchTerm['word']) {
                                    $bWordInQuery = strpos(
                                        $sNormQuery,
                                        $this->normTerm($aSearchTerm['word'])
                                    ) !== false;
                                }
                                $aNewSearches = $oCurrentSearch->extendWithFullTerm(
                                    $aSearchTerm,
                                    $bWordInQuery,
                                    isset($aValidTokens[$sToken])
                                      && strpos($sToken, ' ') === false,
                                    $sPhraseType,
                                    $iToken == 0 && $iPhrase == 0,
                                    $iPhrase == 0,
                                    $iToken + 1 == sizeof($aWordset)
                                      && $iPhrase + 1 == sizeof($aPhrases),
                                    $iGlobalRank
                                );

                                foreach ($aNewSearches as $oSearch) {
                                    if ($oSearch->getRank() < $this->iMaxRank) {
                                        $aNewWordsetSearches[] = $oSearch;
                                    }
                                }
                            }
                        }
                        // Look for partial matches.
                        // Note that there is no point in adding country terms here
                        // because country is omitted in the address.
                        if (isset($aValidTokens[$sToken]) && $sPhraseType != 'country') {
                            // Allow searching for a word - but at extra cost
                            foreach ($aValidTokens[$sToken] as $aSearchTerm) {
                                $aNewSearches = $oCurrentSearch->extendWithPartialTerm(
                                    $aSearchTerm,
                                    $bStructuredPhrases,
                                    $iPhrase,
                                    $aWordFrequencyScores,
                                    isset($aValidTokens[' '.$sToken]) ? $aValidTokens[' '.$sToken] : array()
                                );

                                foreach ($aNewSearches as $oSearch) {
                                    if ($oSearch->getRank() < $this->iMaxRank) {
                                        $aNewWordsetSearches[] = $oSearch;
                                    }
                                }
                            }
                        }
                    }
                    // Sort and cut
                    usort($aNewWordsetSearches, array('Nominatim\SearchDescription', 'bySearchRank'));
                    $aWordsetSearches = array_slice($aNewWordsetSearches, 0, 50);
                }
                //var_Dump('<hr>',sizeof($aWordsetSearches)); exit;

                $aNewPhraseSearches = array_merge($aNewPhraseSearches, $aNewWordsetSearches);
                usort($aNewPhraseSearches, array('Nominatim\SearchDescription', 'bySearchRank'));

                $aSearchHash = array();
                foreach ($aNewPhraseSearches as $iSearch => $aSearch) {
                    $sHash = serialize($aSearch);
                    if (isset($aSearchHash[$sHash])) unset($aNewPhraseSearches[$iSearch]);
                    else $aSearchHash[$sHash] = 1;
                }

                $aNewPhraseSearches = array_slice($aNewPhraseSearches, 0, 50);
            }

            // Re-group the searches by their score, junk anything over 20 as just not worth trying
            $aGroupedSearches = array();
            foreach ($aNewPhraseSearches as $aSearch) {
                $iRank = $aSearch->getRank();
                if ($iRank < $this->iMaxRank) {
                    if (!isset($aGroupedSearches[$iRank])) {
                        $aGroupedSearches[$iRank] = array();
                    }
                    $aGroupedSearches[$iRank][] = $aSearch;
                }
            }
            ksort($aGroupedSearches);

            $iSearchCount = 0;
            $aSearches = array();
            foreach ($aGroupedSearches as $iScore => $aNewSearches) {
                $iSearchCount += sizeof($aNewSearches);
                $aSearches = array_merge($aSearches, $aNewSearches);
                if ($iSearchCount > 50) break;
            }

            //if (CONST_Debug) _debugDumpGroupedSearches($aGroupedSearches, $aValidTokens);
        }

        // Revisit searches, drop bad searches and give penalty to unlikely combinations.
        $aGroupedSearches = array();
        foreach ($aSearches as $oSearch) {
            if (!$oSearch->isValidSearch($this->aCountryCodes)) {
                continue;
            }

            $iRank = $oSearch->addToRank($iGlobalRank);
            if (!isset($aGroupedSearches[$iRank])) {
                $aGroupedSearches[$iRank] = array();
            }
            $aGroupedSearches[$iRank][] = $oSearch;
        }
        ksort($aGroupedSearches);

        return $aGroupedSearches;
    }

    /* Perform the actual query lookup.

        Returns an ordered list of results, each with the following fields:
            osm_type: type of corresponding OSM object
                        N - node
                        W - way
                        R - relation
                        P - postcode (internally computed)
            osm_id: id of corresponding OSM object
            class: general object class (corresponds to tag key of primary OSM tag)
            type: subclass of object (corresponds to tag value of primary OSM tag)
            admin_level: see http://wiki.openstreetmap.org/wiki/Admin_level
            rank_search: rank in search hierarchy
                        (see also http://wiki.openstreetmap.org/wiki/Nominatim/Development_overview#Country_to_street_level)
            rank_address: rank in address hierarchy (determines orer in address)
            place_id: internal key (may differ between different instances)
            country_code: ISO country code
            langaddress: localized full address
            placename: localized name of object
            ref: content of ref tag (if available)
            lon: longitude
            lat: latitude
            importance: importance of place based on Wikipedia link count
            addressimportance: cumulated importance of address elements
            extra_place: type of place (for admin boundaries, if there is a place tag)
            aBoundingBox: bounding Box
            label: short description of the object class/type (English only)
            name: full name (currently the same as langaddress)
            foundorder: secondary ordering for places with same importance
    */


    public function lookup()
    {
        if (!$this->sQuery && !$this->aStructuredQuery) return array();

        $oCtx = new SearchContext();

        $sNormQuery = $this->normTerm($this->sQuery);
        $sLanguagePrefArraySQL = getArraySQL(
            array_map("getDBQuoted", $this->aLangPrefOrder)
        );
        $sCountryCodesSQL = false;
        if ($this->aCountryCodes) {
            $sCountryCodesSQL = join(',', array_map('addQuotes', $this->aCountryCodes));
        }

        $sQuery = $this->sQuery;
        if (!preg_match('//u', $sQuery)) {
            userError("Query string is not UTF-8 encoded.");
        }

        // Conflicts between US state abreviations and various words for 'the' in different languages
        if (isset($this->aLangPrefOrder['name:en'])) {
            $sQuery = preg_replace('/(^|,)\s*il\s*(,|$)/', '\1illinois\2', $sQuery);
            $sQuery = preg_replace('/(^|,)\s*al\s*(,|$)/', '\1alabama\2', $sQuery);
            $sQuery = preg_replace('/(^|,)\s*la\s*(,|$)/', '\1louisiana\2', $sQuery);
        }

        $bBoundingBoxSearch = $this->bBoundedSearch && $this->sViewboxSmallSQL;
        if ($this->sViewboxCentreSQL) {
            // For complex viewboxes (routes) precompute the bounding geometry
            $sGeom = chksql(
                $this->oDB->getOne("select ".$this->sViewboxSmallSQL),
                "Could not get small viewbox"
            );
            $this->sViewboxSmallSQL = "'".$sGeom."'::geometry";

            $sGeom = chksql(
                $this->oDB->getOne("select ".$this->sViewboxLargeSQL),
                "Could not get large viewbox"
            );
            $this->sViewboxLargeSQL = "'".$sGeom."'::geometry";
        }

        // Do we have anything that looks like a lat/lon pair?
        $sQuery = $oCtx->setNearPointFromQuery($sQuery);

        $aSearchResults = array();
        if ($sQuery || $this->aStructuredQuery) {
            // Start with a single blank search
            $aSearches = array(new SearchDescription($oCtx));

            if ($sQuery) {
                $sQuery = $aSearches[0]->extractKeyValuePairs($sQuery);
            }

            $sSpecialTerm = '';
            if ($sQuery) {
                preg_match_all(
                    '/\\[([\\w ]*)\\]/u',
                    $sQuery,
                    $aSpecialTermsRaw,
                    PREG_SET_ORDER
                );
                foreach ($aSpecialTermsRaw as $aSpecialTerm) {
                    $sQuery = str_replace($aSpecialTerm[0], ' ', $sQuery);
                    if (!$sSpecialTerm) {
                        $sSpecialTerm = $aSpecialTerm[1];
                    }
                }
            }
            if (!$sSpecialTerm && $this->aStructuredQuery
                && isset($this->aStructuredQuery['amenity'])) {
                $sSpecialTerm = $this->aStructuredQuery['amenity'];
                unset($this->aStructuredQuery['amenity']);
            }

            if ($sSpecialTerm && !$aSearches[0]->hasOperator()) {
                $sSpecialTerm = pg_escape_string($sSpecialTerm);
                $sToken = chksql(
                    $this->oDB->getOne("SELECT make_standard_name('$sSpecialTerm')"),
                    "Cannot decode query. Wrong encoding?"
                );
                $sSQL = 'SELECT class, type FROM word ';
                $sSQL .= '   WHERE word_token in (\' '.$sToken.'\')';
                $sSQL .= '   AND class is not null AND class not in (\'place\')';
                if (CONST_Debug) var_Dump($sSQL);
                $aSearchWords = chksql($this->oDB->getAll($sSQL));
                $aNewSearches = array();
                foreach ($aSearches as $oSearch) {
                    foreach ($aSearchWords as $aSearchTerm) {
                        $oNewSearch = clone $oSearch;
                        $oNewSearch->setPoiSearch(
                            Operator::TYPE,
                            $aSearchTerm['class'],
                            $aSearchTerm['type']
                        );
                        $aNewSearches[] = $oNewSearch;
                    }
                }
                $aSearches = $aNewSearches;
            }

            // Split query into phrases
            // Commas are used to reduce the search space by indicating where phrases split
            if ($this->aStructuredQuery) {
                $aPhrases = $this->aStructuredQuery;
                $bStructuredPhrases = true;
            } else {
                $aPhrases = explode(',', $sQuery);
                $bStructuredPhrases = false;
            }

            // Convert each phrase to standard form
            // Create a list of standard words
            // Get all 'sets' of words
            // Generate a complete list of all
            $aTokens = array();
            foreach ($aPhrases as $iPhrase => $sPhrase) {
                $aPhrase = chksql(
                    $this->oDB->getRow("SELECT make_standard_name('".pg_escape_string($sPhrase)."') as string"),
                    "Cannot normalize query string (is it a UTF-8 string?)"
                );
                if (trim($aPhrase['string'])) {
                    $aPhrases[$iPhrase] = $aPhrase;
                    $aPhrases[$iPhrase]['words'] = explode(' ', $aPhrases[$iPhrase]['string']);
                    $aPhrases[$iPhrase]['wordsets'] = getWordSets($aPhrases[$iPhrase]['words'], 0);
                    $aTokens = array_merge($aTokens, getTokensFromSets($aPhrases[$iPhrase]['wordsets']));
                } else {
                    unset($aPhrases[$iPhrase]);
                }
            }

            // Reindex phrases - we make assumptions later on that they are numerically keyed in order
            $aPhraseTypes = array_keys($aPhrases);
            $aPhrases = array_values($aPhrases);

            if (sizeof($aTokens)) {
                // Check which tokens we have, get the ID numbers
                $sSQL = 'SELECT word_id, word_token, word, class, type, country_code, operator, search_name_count';
                $sSQL .= ' FROM word ';
                $sSQL .= ' WHERE word_token in ('.join(',', array_map("getDBQuoted", $aTokens)).')';

                if (CONST_Debug) var_Dump($sSQL);

                $aValidTokens = array();
                $aDatabaseWords = chksql(
                    $this->oDB->getAll($sSQL),
                    "Could not get word tokens."
                );
                $aPossibleMainWordIDs = array();
                $aWordFrequencyScores = array();
                foreach ($aDatabaseWords as $aToken) {
                    // Very special case - require 2 letter country param to match the country code found
                    if ($bStructuredPhrases && $aToken['country_code'] && !empty($this->aStructuredQuery['country'])
                        && strlen($this->aStructuredQuery['country']) == 2 && strtolower($this->aStructuredQuery['country']) != $aToken['country_code']
                    ) {
                        continue;
                    }

                    if (isset($aValidTokens[$aToken['word_token']])) {
                        $aValidTokens[$aToken['word_token']][] = $aToken;
                    } else {
                        $aValidTokens[$aToken['word_token']] = array($aToken);
                    }
                    if (!$aToken['class'] && !$aToken['country_code']) $aPossibleMainWordIDs[$aToken['word_id']] = 1;
                    $aWordFrequencyScores[$aToken['word_id']] = $aToken['search_name_count'] + 1;
                }
                if (CONST_Debug) var_Dump($aPhrases, $aValidTokens);

                // US ZIP+4 codes - if there is no token, merge in the 5-digit ZIP code
                foreach ($aTokens as $sToken) {
                    if (!isset($aValidTokens[$sToken]) && preg_match('/^([0-9]{5}) [0-9]{4}$/', $sToken, $aData)) {
                        if (isset($aValidTokens[$aData[1]])) {
                            foreach ($aValidTokens[$aData[1]] as $aToken) {
                                if (!$aToken['class']) {
                                    if (isset($aValidTokens[$sToken])) {
                                        $aValidTokens[$sToken][] = $aToken;
                                    } else {
                                        $aValidTokens[$sToken] = array($aToken);
                                    }
                                }
                            }
                        }
                    }
                }

                foreach ($aTokens as $sToken) {
                    // Unknown single word token with a number - assume it is a house number
                    if (!isset($aValidTokens[' '.$sToken]) && strpos($sToken, ' ') === false && preg_match('/^[0-9]+$/', $sToken)) {
                        $aValidTokens[' '.$sToken] = array(array('class' => 'place', 'type' => 'house', 'word_token' => ' '.$sToken));
                    }
                }

                // Any words that have failed completely?
                // TODO: suggestions

                // Start the search process
                // array with: placeid => -1 | tiger-housenumber
                $aResultPlaceIDs = array();

                $aGroupedSearches = $this->getGroupedSearches($aSearches, $aPhraseTypes, $aPhrases, $aValidTokens, $aWordFrequencyScores, $bStructuredPhrases, $sNormQuery);

                if ($this->bReverseInPlan) {
                    // Reverse phrase array and also reverse the order of the wordsets in
                    // the first and final phrase. Don't bother about phrases in the middle
                    // because order in the address doesn't matter.
                    $aPhrases = array_reverse($aPhrases);
                    $aPhrases[0]['wordsets'] = getInverseWordSets($aPhrases[0]['words'], 0);
                    if (sizeof($aPhrases) > 1) {
                        $aFinalPhrase = end($aPhrases);
                        $aPhrases[sizeof($aPhrases)-1]['wordsets'] = getInverseWordSets($aFinalPhrase['words'], 0);
                    }
                    $aReverseGroupedSearches = $this->getGroupedSearches($aSearches, null, $aPhrases, $aValidTokens, $aWordFrequencyScores, false, $sNormQuery);

                    foreach ($aGroupedSearches as $aSearches) {
                        foreach ($aSearches as $aSearch) {
                            if (!isset($aReverseGroupedSearches[$aSearch->getRank()])) {
                                $aReverseGroupedSearches[$aSearch->getRank()] = array();
                            }
                            $aReverseGroupedSearches[$aSearch->getRank()][] = $aSearch;
                        }
                    }

                    $aGroupedSearches = $aReverseGroupedSearches;
                    ksort($aGroupedSearches);
                }
            } else {
                // Re-group the searches by their score, junk anything over 20 as just not worth trying
                $aGroupedSearches = array();
                foreach ($aSearches as $aSearch) {
                    if ($aSearch->getRank() < $this->iMaxRank) {
                        if (!isset($aGroupedSearches[$aSearch->getRank()])) $aGroupedSearches[$aSearch->getRank()] = array();
                        $aGroupedSearches[$aSearch->getRank()][] = $aSearch;
                    }
                }
                ksort($aGroupedSearches);
            }

            // Filter out duplicate searches
            $aSearchHash = array();
            foreach ($aGroupedSearches as $iGroup => $aSearches) {
                foreach ($aSearches as $iSearch => $aSearch) {
                    $sHash = serialize($aSearch);
                    if (isset($aSearchHash[$sHash])) {
                        unset($aGroupedSearches[$iGroup][$iSearch]);
                        if (sizeof($aGroupedSearches[$iGroup]) == 0) unset($aGroupedSearches[$iGroup]);
                    } else {
                        $aSearchHash[$sHash] = 1;
                    }
                }
            }

            if (CONST_Debug) _debugDumpGroupedSearches($aGroupedSearches, $aValidTokens);

            $iGroupLoop = 0;
            $iQueryLoop = 0;
            foreach ($aGroupedSearches as $iGroupedRank => $aSearches) {
                $iGroupLoop++;
                foreach ($aSearches as $oSearch) {
                    $iQueryLoop++;
                    $searchedHousenumber = -1;

                    if (CONST_Debug) echo "<hr><b>Search Loop, group $iGroupLoop, loop $iQueryLoop</b>";
                    if (CONST_Debug) _debugDumpGroupedSearches(array($iGroupedRank => array($oSearch)), $aValidTokens);

                    $aPlaceIDs = array();
                    if ($oSearch->isCountrySearch()) {
                        // Just looking for a country - look it up
                        if (4 >= $this->iMinAddressRank && 4 <= $this->iMaxAddressRank) {
                            $aPlaceIDs = $oSearch->queryCountry(
                                $this->oDB,
                                $bBoundingBoxSearch ? $this->sViewboxSmallSQL : ''
                            );
                        }
                    } elseif (!$oSearch->isNamedSearch()) {
                        // looking for a POI in a geographic area
                        if (!$bBoundingBoxSearch && !$oCtx->hasNearPoint()) {
                            continue;
                        }

                        $aPlaceIDs = $oSearch->queryNearbyPoi(
                            $this->oDB,
                            $sCountryCodesSQL,
                            $bBoundingBoxSearch ? $this->sViewboxSmallSQL : '',
                            $this->sViewboxCentreSQL,
                            $this->aExcludePlaceIDs ? join(',', $this->aExcludePlaceIDs) : '',
                            $this->iLimit
                        );
                    } elseif ($oSearch->isOperator(Operator::POSTCODE)) {
                        $aPlaceIDs = $oSearch->queryPostcode(
                            $this->oDB,
                            $sCountryCodesSQL,
                            $this->iLimit
                        );
                    } else {
                        // Ordinary search:
                        // First search for places according to name and address.
                        $aNamedPlaceIDs = $oSearch->queryNamedPlace(
                            $this->oDB,
                            $aWordFrequencyScores,
                            $sCountryCodesSQL,
                            $this->iMinAddressRank,
                            $this->iMaxAddressRank,
                            $this->aExcludePlaceIDs ? join(',', $this->aExcludePlaceIDs) : '',
                            $bBoundingBoxSearch ? $this->sViewboxSmallSQL : '',
                            $bBoundingBoxSearch ? $this->sViewboxLargeSQL : '',
                            $this->iLimit
                        );

                        if (sizeof($aNamedPlaceIDs)) {
                            foreach ($aNamedPlaceIDs as $aRow) {
                                $aPlaceIDs[] = $aRow['place_id'];
                                $this->exactMatchCache[$aRow['place_id']] = $aRow['exactmatch'];
                            }
                        }

                        //now search for housenumber, if housenumber provided
                        if ($oSearch->hasHouseNumber() && sizeof($aPlaceIDs)) {
                            $aResult = $oSearch->queryHouseNumber(
                                $this->oDB,
                                $aPlaceIDs,
                                $this->aExcludePlaceIDs ? join(',', $this->aExcludePlaceIDs) : '',
                                $this->iLimit
                            );

                            if (sizeof($aResult)) {
                                $searchedHousenumber = $aResult['iHouseNumber'];
                                $aPlaceIDs = $aResult['aPlaceIDs'];
                            } elseif (!$oSearch->looksLikeFullAddress()) {
                                $aPlaceIDs = array();
                            }
                        }

                        // finally get POIs if requested
                        if ($oSearch->isPoiSearch() && sizeof($aPlaceIDs)) {
                            $aPlaceIDs = $oSearch->queryPoiByOperator(
                                $this->oDB,
                                $aPlaceIDs,
                                $this->aExcludePlaceIDs ? join(',', $this->aExcludePlaceIDs) : '',
                                $this->iLimit
                            );
                        }
                    }

                    if (CONST_Debug) {
                        echo "<br><b>Place IDs:</b> ";
                        var_Dump($aPlaceIDs);
                    }

                    if (sizeof($aPlaceIDs) && $oSearch->getPostcode()) {
                        $sSQL = 'SELECT place_id FROM placex';
                        $sSQL .= ' WHERE place_id in ('.join(',', $aPlaceIDs).')';
                        $sSQL .= " AND postcode = '".$oSearch->getPostcode()."'";
                        if (CONST_Debug) var_dump($sSQL);
                        $aFilteredPlaceIDs = chksql($this->oDB->getCol($sSQL));
                        if ($aFilteredPlaceIDs) {
                            $aPlaceIDs = $aFilteredPlaceIDs;
                            if (CONST_Debug) {
                                echo "<br><b>Place IDs after postcode filtering:</b> ";
                                var_Dump($aPlaceIDs);
                            }
                        }
                    }

                    foreach ($aPlaceIDs as $iPlaceID) {
                        // array for placeID => -1 | Tiger housenumber
                        $aResultPlaceIDs[$iPlaceID] = $searchedHousenumber;
                    }
                    if ($iQueryLoop > 20) break;
                }

                if (isset($aResultPlaceIDs) && sizeof($aResultPlaceIDs) && ($this->iMinAddressRank != 0 || $this->iMaxAddressRank != 30)) {
                    // Need to verify passes rank limits before dropping out of the loop (yuk!)
                    // reduces the number of place ids, like a filter
                    // rank_address is 30 for interpolated housenumbers
                    $sWherePlaceId = 'WHERE place_id in (';
                    $sWherePlaceId .= join(',', array_keys($aResultPlaceIDs)).') ';

                    $sSQL = "SELECT place_id ";
                    $sSQL .= "FROM placex ".$sWherePlaceId;
                    $sSQL .= "  AND (";
                    $sSQL .= "         placex.rank_address between $this->iMinAddressRank and $this->iMaxAddressRank ";
                    if (14 >= $this->iMinAddressRank && 14 <= $this->iMaxAddressRank) {
                        $sSQL .= "     OR (extratags->'place') = 'city'";
                    }
                    if ($this->aAddressRankList) {
                        $sSQL .= "     OR placex.rank_address in (".join(',', $this->aAddressRankList).")";
                    }
                    $sSQL .= "  ) UNION ";
                    $sSQL .= " SELECT place_id FROM location_postcode lp ".$sWherePlaceId;
                    $sSQL .= "  AND (lp.rank_address between $this->iMinAddressRank and $this->iMaxAddressRank ";
                    if ($this->aAddressRankList) {
                        $sSQL .= "     OR lp.rank_address in (".join(',', $this->aAddressRankList).")";
                    }
                    $sSQL .= ") ";
                    if (CONST_Use_US_Tiger_Data && $this->iMaxAddressRank == 30) {
                        $sSQL .= "UNION ";
                        $sSQL .= "  SELECT place_id ";
                        $sSQL .= "  FROM location_property_tiger ".$sWherePlaceId;
                    }
                    if ($this->iMaxAddressRank == 30) {
                        $sSQL .= "UNION ";
                        $sSQL .= "  SELECT place_id ";
                        $sSQL .= "  FROM location_property_osmline ".$sWherePlaceId;
                    }
                    if (CONST_Debug) var_dump($sSQL);
                    $aFilteredPlaceIDs = chksql($this->oDB->getCol($sSQL));
                    $tempIDs = array();
                    foreach ($aFilteredPlaceIDs as $placeID) {
                        $tempIDs[$placeID] = $aResultPlaceIDs[$placeID];  //assign housenumber to placeID
                    }
                    $aResultPlaceIDs = $tempIDs;
                }

                //exit;
                if (isset($aResultPlaceIDs) && sizeof($aResultPlaceIDs)) break;
                if ($iGroupLoop > 4) break;
                if ($iQueryLoop > 30) break;
            }

            // Did we find anything?
            if (isset($aResultPlaceIDs) && sizeof($aResultPlaceIDs)) {
                $aSearchResults = $this->getDetails($aResultPlaceIDs);
            }
        } else {
            // Just interpret as a reverse geocode
            $oReverse = new ReverseGeocode($this->oDB);
            $oReverse->setZoom(18);

            $aLookup = $oReverse->lookupPoint($oCtx->sqlNear, false);

            if (CONST_Debug) var_dump("Reverse search", $aLookup);

            if ($aLookup['place_id']) {
                $aSearchResults = $this->getDetails(array($aLookup['place_id'] => -1));
                $aResultPlaceIDs[$aLookup['place_id']] = -1;
            } else {
                $aSearchResults = array();
            }
        }

        // No results? Done
        if (!sizeof($aSearchResults)) {
            if ($this->bFallback) {
                if ($this->fallbackStructuredQuery()) {
                    return $this->lookup();
                }
            }

            return array();
        }

        $aClassType = getClassTypesWithImportance();
        $aRecheckWords = preg_split('/\b[\s,\\-]*/u', $sQuery);
        foreach ($aRecheckWords as $i => $sWord) {
            if (!preg_match('/[\pL\pN]/', $sWord)) unset($aRecheckWords[$i]);
        }

        if (CONST_Debug) {
            echo '<i>Recheck words:<\i>';
            var_dump($aRecheckWords);
        }

        $oPlaceLookup = new PlaceLookup($this->oDB);
        $oPlaceLookup->setIncludePolygonAsPoints($this->bIncludePolygonAsPoints);
        $oPlaceLookup->setIncludePolygonAsText($this->bIncludePolygonAsText);
        $oPlaceLookup->setIncludePolygonAsGeoJSON($this->bIncludePolygonAsGeoJSON);
        $oPlaceLookup->setIncludePolygonAsKML($this->bIncludePolygonAsKML);
        $oPlaceLookup->setIncludePolygonAsSVG($this->bIncludePolygonAsSVG);
        $oPlaceLookup->setPolygonSimplificationThreshold($this->fPolygonSimplificationThreshold);

        foreach ($aSearchResults as $iResNum => $aResult) {
            // Default
            $fDiameter = getResultDiameter($aResult);

            $aOutlineResult = $oPlaceLookup->getOutlines($aResult['place_id'], $aResult['lon'], $aResult['lat'], $fDiameter/2);
            if ($aOutlineResult) {
                $aResult = array_merge($aResult, $aOutlineResult);
            }
            
            if ($aResult['extra_place'] == 'city') {
                $aResult['class'] = 'place';
                $aResult['type'] = 'city';
                $aResult['rank_search'] = 16;
            }

            // Is there an icon set for this type of result?
            if (isset($aClassType[$aResult['class'].':'.$aResult['type']]['icon'])
                && $aClassType[$aResult['class'].':'.$aResult['type']]['icon']
            ) {
                $aResult['icon'] = CONST_Website_BaseURL.'images/mapicons/'.$aClassType[$aResult['class'].':'.$aResult['type']]['icon'].'.p.20.png';
            }

            if (isset($aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['label'])
                && $aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['label']
            ) {
                $aResult['label'] = $aClassType[$aResult['class'].':'.$aResult['type'].':'.$aResult['admin_level']]['label'];
            } elseif (isset($aClassType[$aResult['class'].':'.$aResult['type']]['label'])
                && $aClassType[$aResult['class'].':'.$aResult['type']]['label']
            ) {
                $aResult['label'] = $aClassType[$aResult['class'].':'.$aResult['type']]['label'];
            }
            // if tag '&addressdetails=1' is set in query
            if ($this->bIncludeAddressDetails) {
                // getAddressDetails() is defined in lib.php and uses the SQL function get_addressdata in functions.sql
                $aResult['address'] = getAddressDetails($this->oDB, $sLanguagePrefArraySQL, $aResult['place_id'], $aResult['country_code'], $aResultPlaceIDs[$aResult['place_id']]);
                if ($aResult['extra_place'] == 'city' && !isset($aResult['address']['city'])) {
                    $aResult['address'] = array_merge(array('city' => array_values($aResult['address'])[0]), $aResult['address']);
                }
            }

            if ($this->bIncludeExtraTags) {
                if ($aResult['extra']) {
                    $aResult['sExtraTags'] = json_decode($aResult['extra']);
                } else {
                    $aResult['sExtraTags'] = (object) array();
                }
            }

            if ($this->bIncludeNameDetails) {
                if ($aResult['names']) {
                    $aResult['sNameDetails'] = json_decode($aResult['names']);
                } else {
                    $aResult['sNameDetails'] = (object) array();
                }
            }

            // Adjust importance for the number of exact string matches in the result
            $aResult['importance'] = max(0.001, $aResult['importance']);
            $iCountWords = 0;
            $sAddress = $aResult['langaddress'];
            foreach ($aRecheckWords as $i => $sWord) {
                if (stripos($sAddress, $sWord)!==false) {
                    $iCountWords++;
                    if (preg_match("/(^|,)\s*".preg_quote($sWord, '/')."\s*(,|$)/", $sAddress)) $iCountWords += 0.1;
                }
            }

            $aResult['importance'] = $aResult['importance'] + ($iCountWords*0.1); // 0.1 is a completely arbitrary number but something in the range 0.1 to 0.5 would seem right

            $aResult['name'] = $aResult['langaddress'];
            // secondary ordering (for results with same importance (the smaller the better):
            // - approximate importance of address parts
            $aResult['foundorder'] = -$aResult['addressimportance']/10;
            // - number of exact matches from the query
            if (isset($this->exactMatchCache[$aResult['place_id']])) {
                $aResult['foundorder'] -= $this->exactMatchCache[$aResult['place_id']];
            } elseif (isset($this->exactMatchCache[$aResult['parent_place_id']])) {
                $aResult['foundorder'] -= $this->exactMatchCache[$aResult['parent_place_id']];
            }
            // - importance of the class/type
            if (isset($aClassType[$aResult['class'].':'.$aResult['type']]['importance'])
                && $aClassType[$aResult['class'].':'.$aResult['type']]['importance']
            ) {
                $aResult['foundorder'] += 0.0001 * $aClassType[$aResult['class'].':'.$aResult['type']]['importance'];
            } else {
                $aResult['foundorder'] += 0.01;
            }
            if (CONST_Debug) var_dump($aResult);
            $aSearchResults[$iResNum] = $aResult;
        }
        uasort($aSearchResults, 'byImportance');

        $aOSMIDDone = array();
        $aClassTypeNameDone = array();
        $aToFilter = $aSearchResults;
        $aSearchResults = array();

        $bFirst = true;
        foreach ($aToFilter as $iResNum => $aResult) {
            $this->aExcludePlaceIDs[$aResult['place_id']] = $aResult['place_id'];
            if ($bFirst) {
                $fLat = $aResult['lat'];
                $fLon = $aResult['lon'];
                if (isset($aResult['zoom'])) $iZoom = $aResult['zoom'];
                $bFirst = false;
            }
            if (!$this->bDeDupe || (!isset($aOSMIDDone[$aResult['osm_type'].$aResult['osm_id']])
                && !isset($aClassTypeNameDone[$aResult['osm_type'].$aResult['class'].$aResult['type'].$aResult['name'].$aResult['admin_level']]))
            ) {
                $aOSMIDDone[$aResult['osm_type'].$aResult['osm_id']] = true;
                $aClassTypeNameDone[$aResult['osm_type'].$aResult['class'].$aResult['type'].$aResult['name'].$aResult['admin_level']] = true;
                $aSearchResults[] = $aResult;
            }

            // Absolute limit on number of results
            if (sizeof($aSearchResults) >= $this->iFinalLimit) break;
        }

        return $aSearchResults;
    } // end lookup()
} // end class
