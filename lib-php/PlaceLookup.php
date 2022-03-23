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

require_once(CONST_LibDir.'/AddressDetails.php');
require_once(CONST_LibDir.'/Result.php');

class PlaceLookup
{
    protected $oDB;

    protected $aLangPrefOrderSql = "''";

    protected $bAddressDetails = false;
    protected $bExtraTags = false;
    protected $bNameDetails = false;

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

    public function setIncludeAddressDetails($b)
    {
        $this->bAddressDetails = $b;
    }

    public function loadParamArray($oParams, $sGeomType = null)
    {
        $aLangs = $oParams->getPreferredLanguages();
        $this->aLangPrefOrderSql =
            'ARRAY['.join(',', $this->oDB->getDBQuotedList($aLangs)).']';

        $this->bExtraTags = $oParams->getBool('extratags', false);
        $this->bNameDetails = $oParams->getBool('namedetails', false);

        $this->bDeDupe = $oParams->getBool('dedupe', $this->bDeDupe);

        if ($sGeomType === null || $sGeomType == 'geojson') {
            $this->bIncludePolygonAsGeoJSON = $oParams->getBool('polygon_geojson');
        }

        if ($oParams->getString('format', '') !== 'geojson') {
            if ($sGeomType === null || $sGeomType == 'text') {
                $this->bIncludePolygonAsText = $oParams->getBool('polygon_text');
            }
            if ($sGeomType === null || $sGeomType == 'kml') {
                $this->bIncludePolygonAsKML = $oParams->getBool('polygon_kml');
            }
            if ($sGeomType === null || $sGeomType == 'svg') {
                $this->bIncludePolygonAsSVG = $oParams->getBool('polygon_svg');
            }
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

        if ($this->bAddressDetails) {
            $aParams['addressdetails'] = '1';
        }
        if ($this->bExtraTags) {
            $aParams['extratags'] = '1';
        }
        if ($this->bNameDetails) {
            $aParams['namedetails'] = '1';
        }

        if ($this->bIncludePolygonAsText) {
            $aParams['polygon_text'] = '1';
        }
        if ($this->bIncludePolygonAsGeoJSON) {
            $aParams['polygon_geojson'] = '1';
        }
        if ($this->bIncludePolygonAsKML) {
            $aParams['polygon_kml'] = '1';
        }
        if ($this->bIncludePolygonAsSVG) {
            $aParams['polygon_svg'] = '1';
        }

        if ($this->fPolygonSimplificationThreshold > 0.0) {
            $aParams['polygon_threshold'] = $this->fPolygonSimplificationThreshold;
        }

        if (!$this->bDeDupe) {
            $aParams['dedupe'] = '0';
        }

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
        $this->aLangPrefOrderSql = $this->oDB->getArraySQL(
            $this->oDB->getDBQuotedList($aLangPrefOrder)
        );
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
        if ($this->bAddressDetails) {
            return ''; // langaddress will be computed from address details
        }

        return 'get_address_by_language(place_id,'.$sHousenumber.','.$this->aLangPrefOrderSql.') AS langaddress,';
    }

    public function lookupOSMID($sType, $iID)
    {
        $sSQL = 'select place_id from placex where osm_type = :type and osm_id = :id';
        $iPlaceID = $this->oDB->getOne($sSQL, array(':type' => $sType, ':id' => $iID));

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
            $sSQL .= "    COALESCE(extratags->'place', extratags->'linked_place') AS extra_place ";
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
            if (!$this->bDeDupe) {
                $sSQL .= 'place_id,';
            }
            if (!$this->bAddressDetails) {
                $sSQL .= 'langaddress, ';
            }
            $sSQL .= '     placename, ';
            $sSQL .= '     ref, ';
            if ($this->bExtraTags) {
                $sSQL .= 'extratags, ';
            }
            if ($this->bNameDetails) {
                $sSQL .= 'name, ';
            }
            $sSQL .= '     extra_place ';

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
            $sSQL .= '  null::smallint as admin_level, rank_search, rank_address,';
            $sSQL .= '  place_id, parent_place_id,';
            $sSQL .= '  -1 as housenumber,';
            $sSQL .= '  country_code,';
            $sSQL .= $this->langAddressSql('-1');
            $sSQL .= '  postcode as placename,';
            $sSQL .= '  postcode as ref,';
            if ($this->bExtraTags) {
                $sSQL .= 'null::text AS extra,';
            }
            if ($this->bNameDetails) {
                $sSQL .= 'null::text AS names,';
            }
            $sSQL .= '  ST_x(geometry) AS lon, ST_y(geometry) AS lat,';
            $sSQL .= '  (0.75-(rank_search::float/40)) AS importance, ';
            $sSQL .= $this->addressImportanceSql('geometry', 'lp.parent_place_id');
            $sSQL .= '  null::text AS extra_place ';
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
                    $sSQL .= '     null::smallint AS admin_level, ';
                    $sSQL .= '     30 AS rank_search, ';
                    $sSQL .= '     30 AS rank_address, ';
                    $sSQL .= '     place_id, ';
                    $sSQL .= '     parent_place_id, ';
                    $sSQL .= '     housenumber_for_place as housenumber,';
                    $sSQL .= "     'us' AS country_code, ";
                    $sSQL .= $this->langAddressSql('housenumber_for_place');
                    $sSQL .= '     null::text AS placename, ';
                    $sSQL .= '     null::text AS ref, ';
                    if ($this->bExtraTags) {
                        $sSQL .= 'null::text AS extra,';
                    }
                    if ($this->bNameDetails) {
                        $sSQL .= 'null::text AS names,';
                    }
                    $sSQL .= '     st_x(centroid) AS lon, ';
                    $sSQL .= '     st_y(centroid) AS lat,';
                    $sSQL .= '     -1.15 AS importance, ';
                    $sSQL .= $this->addressImportanceSql('centroid', 'blub.parent_place_id');
                    $sSQL .= '     null::text AS extra_place ';
                    $sSQL .= ' FROM (';
                    $sSQL .= '     SELECT place_id, ';    // interpolate the Tiger housenumbers here
                    $sSQL .= '         CASE WHEN startnumber != endnumber';
                    $sSQL .= '              THEN ST_LineInterpolatePoint(linegeo, (housenumber_for_place-startnumber::float)/(endnumber-startnumber)::float)';
                    $sSQL .= '              ELSE ST_LineInterpolatePoint(linegeo, 0.5) END AS centroid, ';
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
                $sSQL .= '  null::smallint AS admin_level, ';
                $sSQL .= '  30 AS rank_search, ';
                $sSQL .= '  30 AS rank_address, ';
                $sSQL .= '  place_id, ';
                $sSQL .= '  parent_place_id, ';
                $sSQL .= '  housenumber_for_place as housenumber,';
                $sSQL .= '  country_code, ';
                $sSQL .= $this->langAddressSql('housenumber_for_place');
                $sSQL .= '  null::text AS placename, ';
                $sSQL .= '  null::text AS ref, ';
                if ($this->bExtraTags) {
                    $sSQL .= 'null::text AS extra, ';
                }
                if ($this->bNameDetails) {
                    $sSQL .= 'null::text AS names, ';
                }
                $sSQL .= '  st_x(centroid) AS lon, ';
                $sSQL .= '  st_y(centroid) AS lat, ';
                // slightly smaller than the importance for normal houses
                $sSQL .= '  -0.1 AS importance, ';
                $sSQL .= $this->addressImportanceSql('centroid', 'blub.parent_place_id');
                $sSQL .= '  null::text AS extra_place ';
                $sSQL .= '  FROM (';
                $sSQL .= '     SELECT ';
                $sSQL .= '         osm_id, ';
                $sSQL .= '         place_id, ';
                $sSQL .= '         country_code, ';
                $sSQL .= '         CASE ';             // interpolate the housenumbers here
                $sSQL .= '           WHEN startnumber != endnumber ';
                $sSQL .= '           THEN ST_LineInterpolatePoint(linegeo, (housenumber_for_place-startnumber::float)/(endnumber-startnumber)::float) ';
                $sSQL .= '           ELSE linegeo ';
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
        }

        if (empty($aSubSelects)) {
            return array();
        }

        $sSQL = join(' UNION ', $aSubSelects);
        Debug::printSQL($sSQL);
        $aPlaces = $this->oDB->getAll($sSQL, null, 'Could not lookup place');

        foreach ($aPlaces as &$aPlace) {
            $aPlace['importance'] = (float) $aPlace['importance'];
            if ($this->bAddressDetails) {
                // to get addressdetails for tiger data, the housenumber is needed
                $aPlace['address'] = new AddressDetails(
                    $this->oDB,
                    $aPlace['place_id'],
                    $aPlace['housenumber'],
                    $this->aLangPrefOrderSql
                );
                $aPlace['langaddress'] = $aPlace['address']->getLocaleAddress();
            }

            if ($this->bExtraTags) {
                if ($aPlace['extra']) {
                    $aPlace['sExtraTags'] = json_decode($aPlace['extra']);
                } else {
                    $aPlace['sExtraTags'] = (object) array();
                }
            }

            if ($this->bNameDetails) {
                $aPlace['sNameDetails'] = $this->extractNames($aPlace['names']);
            }

            $aPlace['addresstype'] = ClassTypes\getLabelTag(
                $aPlace,
                $aPlace['country_code']
            );

            $aResults[$aPlace['place_id']] = $aPlace;
        }

        $aResults = array_filter(
            $aResults,
            function ($v) {
                return !($v instanceof Result);
            }
        );

        Debug::printVar('Places', $aResults);

        return $aResults;
    }


    private function extractNames($sNames)
    {
        if (!$sNames) {
            return (object) array();
        }

        $aFullNames = json_decode($sNames);
        $aNames = array();

        foreach ($aFullNames as $sKey => $sValue) {
            if (strpos($sKey, '_place_') === 0) {
                $sSubKey = substr($sKey, 7);
                if (array_key_exists($sSubKey, $aFullNames)) {
                    $aNames[$sKey] = $sValue;
                } else {
                    $aNames[$sSubKey] = $sValue;
                }
            } else {
                $aNames[$sKey] = $sValue;
            }
        }

        return $aNames;
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
        if (!$iPlaceID) {
            return $aOutlineResult;
        }

        // Get the bounding box and outline polygon
        $sSQL = 'select place_id,0 as numfeatures,st_area(geometry) as area,';
        if ($fLonReverse != null && $fLatReverse != null) {
            $sSQL .= ' ST_Y(closest_point) as centrelat,';
            $sSQL .= ' ST_X(closest_point) as centrelon,';
        } else {
            $sSQL .= ' ST_Y(centroid) as centrelat, ST_X(centroid) as centrelon,';
        }
        $sSQL .= ' ST_YMin(geometry) as minlat,ST_YMax(geometry) as maxlat,';
        $sSQL .= ' ST_XMin(geometry) as minlon,ST_XMax(geometry) as maxlon';
        if ($this->bIncludePolygonAsGeoJSON) {
            $sSQL .= ',ST_AsGeoJSON(geometry) as asgeojson';
        }
        if ($this->bIncludePolygonAsKML) {
            $sSQL .= ',ST_AsKML(geometry) as askml';
        }
        if ($this->bIncludePolygonAsSVG) {
            $sSQL .= ',ST_AsSVG(geometry) as assvg';
        }
        if ($this->bIncludePolygonAsText) {
            $sSQL .= ',ST_AsText(geometry) as astext';
        }
        if ($fLonReverse != null && $fLatReverse != null) {
            $sFrom = ' from (SELECT * , CASE WHEN (class = \'highway\') AND (ST_GeometryType(geometry) = \'ST_LineString\') THEN ';
            $sFrom .=' ST_ClosestPoint(geometry, ST_SetSRID(ST_Point('.$fLatReverse.','.$fLonReverse.'),4326))';
            $sFrom .=' ELSE centroid END AS closest_point';
            $sFrom .= ' from placex where place_id = '.$iPlaceID.') as plx';
        } else {
            $sFrom = ' from placex where place_id = '.$iPlaceID;
        }
        if ($this->fPolygonSimplificationThreshold > 0) {
            $sSQL .= ' from (select place_id,centroid,ST_SimplifyPreserveTopology(geometry,'.$this->fPolygonSimplificationThreshold.') as geometry'.$sFrom.') as plx';
        } else {
            $sSQL .= $sFrom;
        }

        $aPointPolygon = $this->oDB->getRow($sSQL, null, 'Could not get outline');

        if ($aPointPolygon && $aPointPolygon['place_id']) {
            if ($aPointPolygon['centrelon'] !== null && $aPointPolygon['centrelat'] !== null) {
                $aOutlineResult['lat'] = $aPointPolygon['centrelat'];
                $aOutlineResult['lon'] = $aPointPolygon['centrelon'];
            }

            if ($this->bIncludePolygonAsGeoJSON) {
                $aOutlineResult['asgeojson'] = $aPointPolygon['asgeojson'];
            }
            if ($this->bIncludePolygonAsKML) {
                $aOutlineResult['askml'] = $aPointPolygon['askml'];
            }
            if ($this->bIncludePolygonAsSVG) {
                $aOutlineResult['assvg'] = $aPointPolygon['assvg'];
            }
            if ($this->bIncludePolygonAsText) {
                $aOutlineResult['astext'] = $aPointPolygon['astext'];
            }

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

        // as a fallback we generate a bounding box without knowing the size of the geometry
        if ((!isset($aOutlineResult['aBoundingBox'])) && isset($fLon)) {
            $aBounds = array(
                        'minlat' => $fLat - $fRadius,
                        'maxlat' => $fLat + $fRadius,
                        'minlon' => $fLon - $fRadius,
                        'maxlon' => $fLon + $fRadius
                       );

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
