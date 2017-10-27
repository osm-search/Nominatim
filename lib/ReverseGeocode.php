<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/Result.php');

class ReverseGeocode
{
    protected $oDB;
    protected $iMaxRank = 28;


    public function __construct(&$oDB)
    {
        $this->oDB =& $oDB;
    }


    public function setZoom($iZoom)
    {
        // Zoom to rank, this could probably be calculated but a lookup gives fine control
        $aZoomRank = array(
                      0 => 2, // Continent / Sea
                      1 => 2,
                      2 => 2,
                      3 => 4, // Country
                      4 => 4,
                      5 => 8, // State
                      6 => 10, // Region
                      7 => 10,
                      8 => 12, // County
                      9 => 12,
                      10 => 17, // City
                      11 => 17,
                      12 => 18, // Town / Village
                      13 => 18,
                      14 => 22, // Suburb
                      15 => 22,
                      16 => 26, // Street, TODO: major street?
                      17 => 26,
                      18 => 30, // or >, Building
                      19 => 30, // or >, Building
                     );
        $this->iMaxRank = (isset($iZoom) && isset($aZoomRank[$iZoom]))?$aZoomRank[$iZoom]:28;
    }

    /**
     * Find the closest interpolation with the given search diameter.
     *
     * @param string $sPointSQL   Reverse geocoding point as SQL
     * @param float  $fSearchDiam Search diameter
     *
     * @return Record of the interpolation or null.
     */
    protected function lookupInterpolation($sPointSQL, $fSearchDiam)
    {
        $sSQL = 'SELECT place_id, parent_place_id, 30 as rank_search,';
        $sSQL .= '  ST_LineLocatePoint(linegeo,'.$sPointSQL.') as fraction,';
        $sSQL .= '  startnumber, endnumber, interpolationtype,';
        $sSQL .= '  ST_Distance(linegeo,'.$sPointSQL.') as distance';
        $sSQL .= ' FROM location_property_osmline';
        $sSQL .= ' WHERE ST_DWithin('.$sPointSQL.', linegeo, '.$fSearchDiam.')';
        $sSQL .= ' and indexed_status = 0 and startnumber is not NULL ';
        $sSQL .= ' ORDER BY distance ASC limit 1';

        return chksql(
            $this->oDB->getRow($sSQL),
            'Could not determine closest housenumber on an osm interpolation line.'
        );
    }

    public function lookup($fLat, $fLon, $bDoInterpolation = true)
    {
        return $this->lookupPoint(
            'ST_SetSRID(ST_Point('.$fLon.','.$fLat.'),4326)',
            $bDoInterpolation
        );
    }

    public function lookupPoint($sPointSQL, $bDoInterpolation = true)
    {
        $iMaxRank = $this->iMaxRank;

        // Find the nearest point
        $fSearchDiam = 0.0004;
        $oResult = null;
        $aPlace = null;
        $fMaxAreaDistance = 1;
        $bIsTigerStreet = false;
        while ($oResult === null && $fSearchDiam < $fMaxAreaDistance) {
            $fSearchDiam = $fSearchDiam * 2;

            // If we have to expand the search area by a large amount then we need a larger feature
            // then there is a limit to how small the feature should be
            if ($fSearchDiam > 2 && $iMaxRank > 4) $iMaxRank = 4;
            if ($fSearchDiam > 1 && $iMaxRank > 9) $iMaxRank = 8;
            if ($fSearchDiam > 0.8 && $iMaxRank > 10) $iMaxRank = 10;
            if ($fSearchDiam > 0.6 && $iMaxRank > 12) $iMaxRank = 12;
            if ($fSearchDiam > 0.2 && $iMaxRank > 17) $iMaxRank = 17;
            if ($fSearchDiam > 0.1 && $iMaxRank > 18) $iMaxRank = 18;
            if ($fSearchDiam > 0.008 && $iMaxRank > 22) $iMaxRank = 22;
            if ($fSearchDiam > 0.001 && $iMaxRank > 26) {
                // try with interpolations before continuing
                if ($bDoInterpolation) {
                    $aHouse = $this->lookupInterpolation($sPointSQL, $fSearchDiam/2);

                    if ($aHouse) {
                        $oResult = new Result($aHouse['place_id'], Result::TABLE_OSMLINE);
                        $oResult->iHouseNumber = closestHouseNumber($aHouse);

                        $aPlace = $aHouse;
                        $iParentPlaceID = $aHouse['parent_place_id']; // the street
                        $iMaxRank = 30;

                        break;
                    }
                }
                // no interpolation found, continue search
                $iMaxRank = 26;
            }

            $sSQL = 'select place_id,parent_place_id,rank_search,country_code,';
            $sSQL .= '  ST_distance('.$sPointSQL.', geometry) as distance';
            $sSQL .= ' FROM ';
            if ($fSearchDiam < 0.01) {
                $sSQL .= ' placex';
                $sSQL .= '   WHERE ST_DWithin('.$sPointSQL.', geometry, '.$fSearchDiam.')';
                $sSQL .= '   AND';
            } else {
                $sSQL .= ' (SELECT * FROM placex ';
                $sSQL .= '   WHERE ST_DWithin('.$sPointSQL.', geometry, '.$fSearchDiam.')';
                $sSQL .= '   LIMIT 1000) as p WHERE';
            }
            $sSQL .= ' rank_search != 28 and rank_search >= '.$iMaxRank;
            $sSQL .= ' and (name is not null or housenumber is not null';
            $sSQL .= '      or rank_search between 26 and 27)';
            $sSQL .= ' and class not in (\'waterway\',\'railway\',\'tunnel\',\'bridge\',\'man_made\')';
            $sSQL .= ' and indexed_status = 0 and linked_place_id is null';
            $sSQL .= ' and (ST_GeometryType(geometry) not in (\'ST_Polygon\',\'ST_MultiPolygon\') ';
            $sSQL .= ' OR ST_DWithin('.$sPointSQL.', centroid, '.$fSearchDiam.'))';
            $sSQL .= ' ORDER BY distance ASC limit 1';
            if (CONST_Debug) var_dump($sSQL);
            $aPlace = chksql(
                $this->oDB->getRow($sSQL),
                'Could not determine closest place.'
            );
            if ($aPlace) {
                $oResult = new Result($aPlace['place_id']);
                $iParentPlaceID = $aPlace['parent_place_id'];
                if ($bDoInterpolation) {
                    if ($aPlace['rank_search'] == 26 || $aPlace['rank_search'] == 27) {
                        $bIsTigerStreet = ($aPlace['country_code'] == 'us');
                    } elseif ($aPlace['rank_search'] == 30) {
                        // If a house was found, make sure there isn't an
                        // interpolation line that is closer.
                        $aHouse = $this->lookupInterpolation(
                            $sPointSQL,
                            $aPlace['distance']
                        );
                        if ($aHouse && $aPlace['distance'] < $aHouse['distance']) {
                            $oResult = new Result(
                                $aHouse['place_id'],
                                Result::TABLE_OSMLINE
                            );
                            $oResult->iHouseNumber = closestHouseNumber($aHouse);

                            $aPlace = $aHouse;
                            $iParentPlaceID = $aHouse['parent_place_id'];
                        }
                    }
                }
            }
        }

        // Only street found? In the US we can check TIGER data for nearest housenumber
        if (CONST_Use_US_Tiger_Data && $bIsTigerStreet && $this->iMaxRank >= 28) {
            $fSearchDiam = $aPlace['rank_search'] > 28 ? $aPlace['distance'] : 0.001;
            $sSQL = 'SELECT place_id,parent_place_id,30 as rank_search,';
            $sSQL .= 'ST_LineLocatePoint(linegeo,'.$sPointSQL.') as fraction,';
            $sSQL .= 'ST_distance('.$sPointSQL.', linegeo) as distance,';
            $sSQL .= 'startnumber,endnumber,interpolationtype';
            $sSQL .= ' FROM location_property_tiger WHERE parent_place_id = '.$oResult->iId;
            $sSQL .= ' AND ST_DWithin('.$sPointSQL.', linegeo, '.$fSearchDiam.')';
            $sSQL .= ' ORDER BY distance ASC limit 1';

            if (CONST_Debug) var_dump($sSQL);

            $aPlaceTiger = chksql(
                $this->oDB->getRow($sSQL),
                'Could not determine closest Tiger place.'
            );
            if ($aPlaceTiger) {
                if (CONST_Debug) var_dump('found Tiger housenumber', $aPlaceTiger);
                $aPlace = $aPlaceTiger;
                $oResult = new Result($aPlace['place_id'], Result::TABLE_TIGER);
                $oResult->iHouseNumber = closestHouseNumber($aPlaceTiger);
                $iParentPlaceID = $aPlace['parent_place_id'];
                $iMaxRank = 30;
            }
        }

        // The point we found might be too small - use the address to find what it is a child of
        if ($oResult !== null && $iMaxRank < 28) {
            if ($aPlace['rank_search'] > 28 && $iParentPlaceID) {
                $iPlaceID = $iParentPlaceID;
            } else {
                $iPlaceID = $oResult->iId;
            }
            $sSQL  = 'select coalesce(p.linked_place_id, a.address_place_id)';
            $sSQL .= ' FROM place_addressline a, placex p';
            $sSQL .= " WHERE a.place_id = $iPlaceID and a.place_id = p.place_id";
            $sSQL .= " ORDER BY abs(cached_rank_address - $iMaxRank) asc,cached_rank_address desc,isaddress desc,distance desc";
            $sSQL .= ' LIMIT 1';
            $iPlaceID = chksql($this->oDB->getOne($sSQL), 'Could not get parent for place.');
            if ($iPlaceID) {
                $oResult = new Result($iPlaceID);
            }
        }

        return $oResult;
    }
}
