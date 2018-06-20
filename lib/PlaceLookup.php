<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/Result.php');

class PlaceLookup
{
    protected $oDB;

    protected $aLangPrefOrderSql = "''";

    protected $bAddressDetails = false;
    protected $bExtraTags = false;
    protected $bNameDetails = false;

    protected $bIncludePolygonAsPoints = false;
    protected $bIncludePolygonAsText = false;
    protected $bIncludePolygonAsGeoJSON = false;
    protected $bIncludePolygonAsKML = false;
    protected $bIncludePolygonAsSVG = false;
    protected $fPolygonSimplificationThreshold = 0.0;

    protected $sAnchorSql = null;
    protected $sAddressRankListSql = null;
    protected $sAllowedTypesSQLList = null;
    protected $bDeDupe = true;


    public function __construct(&$oDB)
    {
        $this->oDB =& $oDB;
    }

    public function doDeDupe()
    {
        return $this->bDeDupe;
    }

    public function setIncludePolygonAsPoints($b = true)
    {
        $this->bIncludePolygonAsPoints = $b;
    }

    public function loadParamArray($oParams, $sGeomType = null)
    {
        $aLangs = $oParams->getPreferredLanguages();
        $this->aLangPrefOrderSql =
            'ARRAY['.join(',', array_map('getDBQuoted', $aLangs)).']';

        $this->bAddressDetails = $oParams->getBool('addressdetails', true);
        $this->bExtraTags = $oParams->getBool('extratags', false);
        $this->bNameDetails = $oParams->getBool('namedetails', false);

        $this->bDeDupe = $oParams->getBool('dedupe', $this->bDeDupe);

        if ($sGeomType === null || $sGeomType == 'text') {
            $this->bIncludePolygonAsText = $oParams->getBool('polygon_text');
        }
        if ($sGeomType === null || $sGeomType == 'geojson') {
            $this->bIncludePolygonAsGeoJSON = $oParams->getBool('polygon_geojson');
        }
        if ($sGeomType === null || $sGeomType == 'kml') {
            $this->bIncludePolygonAsKML = $oParams->getBool('polygon_kml');
        }
        if ($sGeomType === null || $sGeomType == 'svg') {
            $this->bIncludePolygonAsSVG = $oParams->getBool('polygon_svg');
        }
        $this->fPolygonSimplificationThreshold
            = $oParams->getFloat('polygon_threshold', 0.0);

        $iWantedTypes =
            ($this->bIncludePolygonAsText ? 1 : 0) +
            ($this->bIncludePolygonAsGeoJSON ? 1 : 0) +
            ($this->bIncludePolygonAsKML ? 1 : 0) +
            ($this->bIncludePolygonAsSVG ? 1 : 0);
        if ($iWantedTypes > CONST_PolygonOutput_MaximumTypes) {
            if (CONST_PolygonOutput_MaximumTypes) {
                userError('Select only '.CONST_PolygonOutput_MaximumTypes.' polgyon output option');
            } else {
                userError('Polygon output is disabled');
            }
        }
    }

    public function getMoreUrlParams()
    {
        $aParams = array();

        if ($this->bAddressDetails) $aParams['addressdetails'] = '1';
        if ($this->bExtraTags) $aParams['extratags'] = '1';
        if ($this->bNameDetails) $aParams['namedetails'] = '1';

        if ($this->bIncludePolygonAsPoints) $aParams['polygon'] = '1';
        if ($this->bIncludePolygonAsText) $aParams['polygon_text'] = '1';
        if ($this->bIncludePolygonAsGeoJSON) $aParams['polygon_geojson'] = '1';
        if ($this->bIncludePolygonAsKML) $aParams['polygon_kml'] = '1';
        if ($this->bIncludePolygonAsSVG) $aParams['polygon_svg'] = '1';

        if ($this->fPolygonSimplificationThreshold > 0.0) {
            $aParams['polygon_threshold'] = $this->fPolygonSimplificationThreshold;
        }

        if (!$this->bDeDupe) $aParams['dedupe'] = '0';

        return $aParams;
    }

    public function setAnchorSql($sPoint)
    {
        $this->sAnchorSql = $sPoint;
    }

    public function setAddressRankList($aList)
    {
        $this->sAddressRankListSql = '('.join(',', $aList).')';
    }

    public function setAllowedTypesSQLList($sSql)
    {
        $this->sAllowedTypesSQLList = $sSql;
    }

    public function setLanguagePreference($aLangPrefOrder)
    {
        $this->aLangPrefOrderSql =
            'ARRAY['.join(',', array_map('getDBQuoted', $aLangPrefOrder)).']';
    }

    public function setIncludeAddressDetails($bAddressDetails = true)
    {
        $this->bAddressDetails = $bAddressDetails;
    }

    private function addressImportanceSql($sGeometry, $sPlaceId)
    {
        if ($this->sAnchorSql) {
            $sSQL = 'ST_Distance('.$this->sAnchorSql.','.$sGeometry.')';
        } else {
            $sSQL = '(SELECT max(ai_p.importance * (ai_p.rank_address + 2))';
            $sSQL .= '   FROM place_addressline ai_s, placex ai_p';
            $sSQL .= '   WHERE ai_s.place_id = '.$sPlaceId;
            $sSQL .= '     AND ai_p.place_id = ai_s.address_place_id ';
            $sSQL .= '     AND ai_s.isaddress ';
            $sSQL .= '     AND ai_p.importance is not null)';
        }

        return $sSQL.' AS addressimportance,';
    }

    private function langAddressSql($sHousenumber)
    {
        return 'get_address_by_language(place_id,'.$sHousenumber.','.$this->aLangPrefOrderSql.') AS langaddress,';
    }

    public function lookupOSMID($sType, $iID)
    {
        $sSQL = "select place_id from placex where osm_type = '".$sType."' and osm_id = ".$iID;
        $iPlaceID = chksql($this->oDB->getOne($sSQL));

        if (!$iPlaceID) {
            return null;
        }

        $aResults = $this->lookup(array($iPlaceID => new Result($iPlaceID)));

        return empty($aResults) ? null : reset($aResults);
    }

    public function lookup($aResults, $iMinRank = 0, $iMaxRank = 30)
    {
        Debug::newFunction('Place lookup');

        if (empty($aResults)) {
            return array();
        }
        $aSubSelects = array();

        $sPlaceIDs = Result::joinIdsByTable($aResults, Result::TABLE_PLACEX);
        if ($sPlaceIDs) {
            Debug::printVar('Ids from placex', $sPlaceIDs);
            $sSQL  = 'SELECT ';
            $sSQL .= '    osm_type,';
            $sSQL .= '    osm_id,';
            $sSQL .= '    class,';
            $sSQL .= '    type,';
            $sSQL .= '    admin_level,';
            $sSQL .= '    rank_search,';
            $sSQL .= '    rank_address,';
            $sSQL .= '    min(place_id) AS place_id,';
            $sSQL .= '    min(parent_place_id) AS parent_place_id,';
            $sSQL .= '    -1 as housenumber,';
            $sSQL .= '    country_code,';
            $sSQL .= $this->langAddressSql('-1');
            $sSQL .= '    get_name_by_language(name,'.$this->aLangPrefOrderSql.') AS placename,';
            $sSQL .= "    get_name_by_language(name, ARRAY['ref']) AS ref,";
            if ($this->bExtraTags) {
                $sSQL .= 'hstore_to_json(extratags)::text AS extra,';
            }
            if ($this->bNameDetails) {
                $sSQL .= 'hstore_to_json(name)::text AS names,';
            }
            $sSQL .= '    avg(ST_X(centroid)) AS lon, ';
            $sSQL .= '    avg(ST_Y(centroid)) AS lat, ';
            $sSQL .= '    COALESCE(importance,0.75-(rank_search::float/40)) AS importance, ';
            $sSQL .= $this->addressImportanceSql(
                'ST_Collect(centroid)',
                'min(CASE WHEN placex.rank_search < 28 THEN placex.place_id ELSE placex.parent_place_id END)'
            );
            $sSQL .= "    (extratags->'place') AS extra_place ";
            $sSQL .= ' FROM placex';
            $sSQL .= " WHERE place_id in ($sPlaceIDs) ";
            $sSQL .= '   AND (';
            $sSQL .= "        placex.rank_address between $iMinRank and $iMaxRank ";
            if (14 >= $iMinRank && 14 <= $iMaxRank) {
                $sSQL .= "    OR (extratags->'place') = 'city'";
            }
            if ($this->sAddressRankListSql) {
                $sSQL .= '    OR placex.rank_address in '.$this->sAddressRankListSql;
            }
            $sSQL .= '       ) ';
            if ($this->sAllowedTypesSQLList) {
                $sSQL .= 'AND placex.class in '.$this->sAllowedTypesSQLList;
            }
            $sSQL .= '    AND linked_place_id is null ';
            $sSQL .= ' GROUP BY ';
            $sSQL .= '     osm_type, ';
            $sSQL .= '     osm_id, ';
            $sSQL .= '     class, ';
            $sSQL .= '     type, ';
            $sSQL .= '     admin_level, ';
            $sSQL .= '     rank_search, ';
            $sSQL .= '     rank_address, ';
            $sSQL .= '     housenumber,';
            $sSQL .= '     country_code, ';
            $sSQL .= '     importance, ';
            if (!$this->bDeDupe) $sSQL .= 'place_id,';
            $sSQL .= '     langaddress, ';
            $sSQL .= '     placename, ';
            $sSQL .= '     ref, ';
            if ($this->bExtraTags) $sSQL .= 'extratags, ';
            if ($this->bNameDetails) $sSQL .= 'name, ';
            $sSQL .= "     extratags->'place' ";

            $aSubSelects[] = $sSQL;
        }

        // postcode table
        $sPlaceIDs = Result::joinIdsByTable($aResults, Result::TABLE_POSTCODE);
        if ($sPlaceIDs) {
            Debug::printVar('Ids from location_postcode', $sPlaceIDs);
            $sSQL = 'SELECT';
            $sSQL .= "  'P' as osm_type,";
            $sSQL .= '  (SELECT osm_id from placex p WHERE p.place_id = lp.parent_place_id) as osm_id,';
            $sSQL .= "  'place' as class, 'postcode' as type,";
            $sSQL .= '  null as admin_level, rank_search, rank_address,';
            $sSQL .= '  place_id, parent_place_id,';
            $sSQL .= '  null as housenumber,';
            $sSQL .= '  country_code,';
            $sSQL .= $this->langAddressSql('-1');
            $sSQL .= '  postcode as placename,';
            $sSQL .= '  postcode as ref,';
            if ($this->bExtraTags) $sSQL .= 'null AS extra,';
            if ($this->bNameDetails) $sSQL .= 'null AS names,';
            $sSQL .= '  ST_x(geometry) AS lon, ST_y(geometry) AS lat,';
            $sSQL .= '  (0.75-(rank_search::float/40)) AS importance, ';
            $sSQL .= $this->addressImportanceSql('geometry', 'lp.parent_place_id');
            $sSQL .= '  null AS extra_place ';
            $sSQL .= 'FROM location_postcode lp';
            $sSQL .= " WHERE place_id in ($sPlaceIDs) ";
            $sSQL .= "   AND lp.rank_address between $iMinRank and $iMaxRank";

            $aSubSelects[] = $sSQL;
        }

        // All other tables are rank 30 only.
        if ($iMaxRank == 30) {
            // TIGER table
            if (CONST_Use_US_Tiger_Data) {
                $sPlaceIDs = Result::joinIdsByTable($aResults, Result::TABLE_TIGER);
                if ($sPlaceIDs) {
                    Debug::printVar('Ids from Tiger table', $sPlaceIDs);
                    $sHousenumbers = Result::sqlHouseNumberTable($aResults, Result::TABLE_TIGER);
                    // Tiger search only if a housenumber was searched and if it was found
                    // (realized through a join)
                    $sSQL = ' SELECT ';
                    $sSQL .= "     'T' AS osm_type, ";
                    $sSQL .= '     (SELECT osm_id from placex p WHERE p.place_id=blub.parent_place_id) as osm_id, ';
                    $sSQL .= "     'place' AS class, ";
                    $sSQL .= "     'house' AS type, ";
                    $sSQL .= '     null AS admin_level, ';
                    $sSQL .= '     30 AS rank_search, ';
                    $sSQL .= '     30 AS rank_address, ';
                    $sSQL .= '     place_id, ';
                    $sSQL .= '     parent_place_id, ';
                    $sSQL .= '     housenumber_for_place as housenumber,';
                    $sSQL .= "     'us' AS country_code, ";
                    $sSQL .= $this->langAddressSql('housenumber_for_place');
                    $sSQL .= '     null AS placename, ';
                    $sSQL .= '     null AS ref, ';
                    if ($this->bExtraTags) $sSQL .= 'null AS extra,';
                    if ($this->bNameDetails) $sSQL .= 'null AS names,';
                    $sSQL .= '     st_x(centroid) AS lon, ';
                    $sSQL .= '     st_y(centroid) AS lat,';
                    $sSQL .= '     -1.15 AS importance, ';
                    $sSQL .= $this->addressImportanceSql('centroid', 'blub.parent_place_id');
                    $sSQL .= '     null AS extra_place ';
                    $sSQL .= ' FROM (';
                    $sSQL .= '     SELECT place_id, ';    // interpolate the Tiger housenumbers here
                    $sSQL .= '         ST_LineInterpolatePoint(linegeo, (housenumber_for_place-startnumber::float)/(endnumber-startnumber)::float) AS centroid, ';
                    $sSQL .= '         parent_place_id, ';
                    $sSQL .= '         housenumber_for_place';
                    $sSQL .= '     FROM (';
                    $sSQL .= '            location_property_tiger ';
                    $sSQL .= '            JOIN (values '.$sHousenumbers.') AS housenumbers(place_id, housenumber_for_place) USING(place_id)) ';
                    $sSQL .= '     WHERE ';
                    $sSQL .= '         housenumber_for_place >= startnumber';
                    $sSQL .= '         AND housenumber_for_place <= endnumber';
                    $sSQL .= ' ) AS blub'; //postgres wants an alias here

                    $aSubSelects[] = $sSQL;
                }
            }

            // osmline - interpolated housenumbers
            $sPlaceIDs = Result::joinIdsByTable($aResults, Result::TABLE_OSMLINE);
            if ($sPlaceIDs) {
                Debug::printVar('Ids from interpolation', $sPlaceIDs);
                $sHousenumbers = Result::sqlHouseNumberTable($aResults, Result::TABLE_OSMLINE);
                // interpolation line search only if a housenumber was searched
                // (realized through a join)
                $sSQL = 'SELECT ';
                $sSQL .= "  'W' AS osm_type, ";
                $sSQL .= '  osm_id, ';
                $sSQL .= "  'place' AS class, ";
                $sSQL .= "  'house' AS type, ";
                $sSQL .= '  15 AS admin_level, ';
                $sSQL .= '  30 AS rank_search, ';
                $sSQL .= '  30 AS rank_address, ';
                $sSQL .= '  place_id, ';
                $sSQL .= '  parent_place_id, ';
                $sSQL .= '  housenumber_for_place as housenumber,';
                $sSQL .= '  country_code, ';
                $sSQL .= $this->langAddressSql('housenumber_for_place');
                $sSQL .= '  null AS placename, ';
                $sSQL .= '  null AS ref, ';
                if ($this->bExtraTags) $sSQL .= 'null AS extra, ';
                if ($this->bNameDetails) $sSQL .= 'null AS names, ';
                $sSQL .= '  st_x(centroid) AS lon, ';
                $sSQL .= '  st_y(centroid) AS lat, ';
                // slightly smaller than the importance for normal houses
                $sSQL .= '  -0.1 AS importance, ';
                $sSQL .= $this->addressImportanceSql('centroid', 'blub.parent_place_id');
                $sSQL .= '  null AS extra_place ';
                $sSQL .= '  FROM (';
                $sSQL .= '     SELECT ';
                $sSQL .= '         osm_id, ';
                $sSQL .= '         place_id, ';
                $sSQL .= '         country_code, ';
                $sSQL .= '         CASE ';             // interpolate the housenumbers here
                $sSQL .= '           WHEN startnumber != endnumber ';
                $sSQL .= '           THEN ST_LineInterpolatePoint(linegeo, (housenumber_for_place-startnumber::float)/(endnumber-startnumber)::float) ';
                $sSQL .= '           ELSE ST_LineInterpolatePoint(linegeo, 0.5) ';
                $sSQL .= '         END as centroid, ';
                $sSQL .= '         parent_place_id, ';
                $sSQL .= '         housenumber_for_place ';
                $sSQL .= '     FROM (';
                $sSQL .= '            location_property_osmline ';
                $sSQL .= '            JOIN (values '.$sHousenumbers.') AS housenumbers(place_id, housenumber_for_place) USING(place_id)';
                $sSQL .= '          ) ';
                $sSQL .= '     WHERE housenumber_for_place >= 0 ';
                $sSQL .= '  ) as blub'; //postgres wants an alias here

                $aSubSelects[] = $sSQL;
            }

            if (CONST_Use_Aux_Location_data) {
                $sPlaceIDs = Result::joinIdsByTable($aResults, Result::TABLE_AUX);
                if ($sPlaceIDs) {
                    $sHousenumbers = Result::sqlHouseNumberTable($aResults, Result::TABLE_AUX);
                    $sSQL = '  SELECT ';
                    $sSQL .= "     'L' AS osm_type, ";
                    $sSQL .= '     place_id AS osm_id, ';
                    $sSQL .= "     'place' AS class,";
                    $sSQL .= "     'house' AS type, ";
                    $sSQL .= '     null AS admin_level, ';
                    $sSQL .= '     30 AS rank_search,';
                    $sSQL .= '     30 AS rank_address, ';
                    $sSQL .= '     place_id,';
                    $sSQL .= '     parent_place_id, ';
                    $sSQL .= '     housenumber,';
                    $sSQL .= "     'us' AS country_code, ";
                    $sSQL .= $this->langAddressSql('-1');
                    $sSQL .= '     null AS placename, ';
                    $sSQL .= '     null AS ref, ';
                    if ($this->bExtraTags) $sSQL .= 'null AS extra, ';
                    if ($this->bNameDetails) $sSQL .= 'null AS names, ';
                    $sSQL .= '     ST_X(centroid) AS lon, ';
                    $sSQL .= '     ST_Y(centroid) AS lat, ';
                    $sSQL .= '     -1.10 AS importance, ';
                    $sSQL .= $this->addressImportanceSql(
                        'centroid',
                        'location_property_aux.parent_place_id'
                    );
                    $sSQL .= '     null AS extra_place ';
                    $sSQL .= '  FROM location_property_aux ';
                    $sSQL .= "  WHERE place_id in ($sPlaceIDs) ";

                    $aSubSelects[] = $sSQL;
                }
            }
        }

        if (empty($aSubSelects)) {
            return array();
        }

        $sSQL = join(' UNION ', $aSubSelects);
        Debug::printSQL($sSQL);
        $aPlaces = chksql($this->oDB->getAll($sSQL), 'Could not lookup place');

        $aClassType = getClassTypes();
        foreach ($aPlaces as &$aPlace) {
            if ($this->bAddressDetails) {
                // to get addressdetails for tiger data, the housenumber is needed
                $aPlace['aAddress'] = $this->getAddressNames(
                    $aPlace['place_id'],
                    $aPlace['housenumber']
                );
            }

            if ($this->bExtraTags) {
                if ($aPlace['extra']) {
                    $aPlace['sExtraTags'] = json_decode($aPlace['extra']);
                } else {
                    $aPlace['sExtraTags'] = (object) array();
                }
            }

            if ($this->bNameDetails) {
                if ($aPlace['names']) {
                    $aPlace['sNameDetails'] = json_decode($aPlace['names']);
                } else {
                    $aPlace['sNameDetails'] = (object) array();
                }
            }

            $sAddressType = '';
            $sClassType = $aPlace['class'].':'.$aPlace['type'].':'.$aPlace['admin_level'];
            if (isset($aClassType[$sClassType]) && isset($aClassType[$sClassType]['simplelabel'])) {
                $sAddressType = $aClassType[$aClassType]['simplelabel'];
            } else {
                $sClassType = $aPlace['class'].':'.$aPlace['type'];
                if (isset($aClassType[$sClassType]) && isset($aClassType[$sClassType]['simplelabel']))
                    $sAddressType = $aClassType[$sClassType]['simplelabel'];
                else $sAddressType = $aPlace['class'];
            }

            $aPlace['addresstype'] = $sAddressType;
        }

        Debug::printVar('Places', $aPlaces);

        return $aPlaces;
    }

    public function getAddressDetails($iPlaceID, $bAll = false, $sHousenumber = -1)
    {
        $sSQL = 'SELECT *,';
        $sSQL .= '  get_name_by_language(name,'.$this->aLangPrefOrderSql.') as localname';
        $sSQL .= ' FROM get_addressdata('.$iPlaceID.','.$sHousenumber.')';
        if (!$bAll) {
            $sSQL .= " WHERE isaddress OR type = 'country_code'";
        }
        $sSQL .= ' ORDER BY rank_address desc,isaddress DESC';

        return chksql($this->oDB->getAll($sSQL));
    }

    public function getAddressNames($iPlaceID, $sHousenumber = null)
    {
        $aAddressLines = $this->getAddressDetails(
            $iPlaceID,
            false,
            $sHousenumber === null ? -1 : $sHousenumber
        );

        $aAddress = array();
        $aFallback = array();
        $aClassType = getClassTypes();
        foreach ($aAddressLines as $aLine) {
            $bFallback = false;
            $aTypeLabel = false;
            if (isset($aClassType[$aLine['class'].':'.$aLine['type'].':'.$aLine['admin_level']])) {
                $aTypeLabel = $aClassType[$aLine['class'].':'.$aLine['type'].':'.$aLine['admin_level']];
            } elseif (isset($aClassType[$aLine['class'].':'.$aLine['type']])) {
                $aTypeLabel = $aClassType[$aLine['class'].':'.$aLine['type']];
            } elseif (isset($aClassType['boundary:administrative:'.((int)($aLine['rank_address']/2))])) {
                $aTypeLabel = $aClassType['boundary:administrative:'.((int)($aLine['rank_address']/2))];
                $bFallback = true;
            } else {
                $aTypeLabel = array('simplelabel' => 'address'.$aLine['rank_address']);
                $bFallback = true;
            }
            if ($aTypeLabel && ((isset($aLine['localname']) && $aLine['localname']) || (isset($aLine['housenumber']) && $aLine['housenumber']))) {
                $sTypeLabel = strtolower(isset($aTypeLabel['simplelabel'])?$aTypeLabel['simplelabel']:$aTypeLabel['label']);
                $sTypeLabel = str_replace(' ', '_', $sTypeLabel);
                if (!isset($aAddress[$sTypeLabel]) || (isset($aFallback[$sTypeLabel]) && $aFallback[$sTypeLabel]) || $aLine['class'] == 'place') {
                    $aAddress[$sTypeLabel] = $aLine['localname']?$aLine['localname']:$aLine['housenumber'];
                }
                $aFallback[$sTypeLabel] = $bFallback;
            }
        }
        return $aAddress;
    }



    /* returns an array which will contain the keys
     *   aBoundingBox
     * and may also contain one or more of the keys
     *   asgeojson
     *   askml
     *   assvg
     *   astext
     *   lat
     *   lon
     */


    public function getOutlines($iPlaceID, $fLon = null, $fLat = null, $fRadius = null, $fLonReverse = null, $fLatReverse = null)
    {

        $aOutlineResult = array();
        if (!$iPlaceID) return $aOutlineResult;

        if (CONST_Search_AreaPolygons) {
            // Get the bounding box and outline polygon
            $sSQL = 'select place_id,0 as numfeatures,st_area(geometry) as area,';
            if ($fLonReverse != null && $fLatReverse != null) {
                $sSQL .= ' CASE WHEN (class = \'highway\') AND (ST_GeometryType(geometry) = \'ST_LineString\') THEN';
                $sSQL .= ' ST_Y(closest_point)';
                $sSQL .= ' ELSE ST_Y(centroid) ';
                $sSQL .= ' END as centrelat, ';
                $sSQL .= ' CASE WHEN (class = \'highway\') AND (ST_GeometryType(geometry) = \'ST_LineString\') THEN';
                $sSQL .= ' ST_X(closest_point)';
                $sSQL .= ' ELSE ST_X(centroid) ';
                $sSQL .= ' END as centrelon, ';
            } else {
                $sSQL .= ' ST_Y(centroid) as centrelat, ST_X(centroid) as centrelon,';
            }
            $sSQL .= ' ST_YMin(geometry) as minlat,ST_YMax(geometry) as maxlat,';
            $sSQL .= ' ST_XMin(geometry) as minlon,ST_XMax(geometry) as maxlon';
            if ($this->bIncludePolygonAsGeoJSON) $sSQL .= ',ST_AsGeoJSON(geometry) as asgeojson';
            if ($this->bIncludePolygonAsKML) $sSQL .= ',ST_AsKML(geometry) as askml';
            if ($this->bIncludePolygonAsSVG) $sSQL .= ',ST_AsSVG(geometry) as assvg';
            if ($this->bIncludePolygonAsText || $this->bIncludePolygonAsPoints) $sSQL .= ',ST_AsText(geometry) as astext';
            if ($fLonReverse != null && $fLatReverse != null) {
                $sFrom = ' from (SELECT * , ST_ClosestPoint(geometry, ST_SetSRID(ST_Point('.$fLatReverse.','.$fLonReverse.'),4326)) AS closest_point';
                $sFrom .= ' from placex where place_id = '.$iPlaceID.') as plx';
            } else {
                $sFrom = ' from placex where place_id = '.$iPlaceID;
            }
            if ($this->fPolygonSimplificationThreshold > 0) {
                $sSQL .= ' from (select place_id,centroid,ST_SimplifyPreserveTopology(geometry,'.$this->fPolygonSimplificationThreshold.') as geometry'.$sFrom.') as plx';
            } else {
                $sSQL .= $sFrom;
            }

            $aPointPolygon = chksql($this->oDB->getRow($sSQL), 'Could not get outline');

            if ($aPointPolygon['place_id']) {
                if ($aPointPolygon['centrelon'] !== null && $aPointPolygon['centrelat'] !== null) {
                    $aOutlineResult['lat'] = $aPointPolygon['centrelat'];
                    $aOutlineResult['lon'] = $aPointPolygon['centrelon'];
                }

                if ($this->bIncludePolygonAsGeoJSON) $aOutlineResult['asgeojson'] = $aPointPolygon['asgeojson'];
                if ($this->bIncludePolygonAsKML) $aOutlineResult['askml'] = $aPointPolygon['askml'];
                if ($this->bIncludePolygonAsSVG) $aOutlineResult['assvg'] = $aPointPolygon['assvg'];
                if ($this->bIncludePolygonAsText) $aOutlineResult['astext'] = $aPointPolygon['astext'];
                if ($this->bIncludePolygonAsPoints) $aOutlineResult['aPolyPoints'] = geometryText2Points($aPointPolygon['astext'], $fRadius);


                if (abs($aPointPolygon['minlat'] - $aPointPolygon['maxlat']) < 0.0000001) {
                    $aPointPolygon['minlat'] = $aPointPolygon['minlat'] - $fRadius;
                    $aPointPolygon['maxlat'] = $aPointPolygon['maxlat'] + $fRadius;
                }

                if (abs($aPointPolygon['minlon'] - $aPointPolygon['maxlon']) < 0.0000001) {
                    $aPointPolygon['minlon'] = $aPointPolygon['minlon'] - $fRadius;
                    $aPointPolygon['maxlon'] = $aPointPolygon['maxlon'] + $fRadius;
                }

                $aOutlineResult['aBoundingBox'] = array(
                                                   (string)$aPointPolygon['minlat'],
                                                   (string)$aPointPolygon['maxlat'],
                                                   (string)$aPointPolygon['minlon'],
                                                   (string)$aPointPolygon['maxlon']
                                                  );
            }
        }

        // as a fallback we generate a bounding box without knowing the size of the geometry
        if ((!isset($aOutlineResult['aBoundingBox'])) && isset($fLon)) {
            //
            if ($this->bIncludePolygonAsPoints) {
                $sGeometryText = 'POINT('.$fLon.','.$fLat.')';
                $aOutlineResult['aPolyPoints'] = geometryText2Points($sGeometryText, $fRadius);
            }

            $aBounds = array();
            $aBounds['minlat'] = $fLat - $fRadius;
            $aBounds['maxlat'] = $fLat + $fRadius;
            $aBounds['minlon'] = $fLon - $fRadius;
            $aBounds['maxlon'] = $fLon + $fRadius;

            $aOutlineResult['aBoundingBox'] = array(
                                               (string)$aBounds['minlat'],
                                               (string)$aBounds['maxlat'],
                                               (string)$aBounds['minlon'],
                                               (string)$aBounds['maxlon']
                                              );
        }
        return $aOutlineResult;
    }
}
