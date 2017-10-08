<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/lib.php');


/**
 * Collects search constraints that are independent of the
 * actual interpretation of the search query.
 *
 * The search context is shared between all SearchDescriptions. This
 * object mainly serves as context provider for the database queries.
 * Therefore most data is directly cached as SQL statements.
 */
class SearchContext
{
    private $fNearRadius = false;

    // cached SQL

    public $sqlNear = '';

    public function hasNearPoint()
    {
        return $this->fNearRadius !== false;
    }

    public function nearRadius()
    {
        return $this->fNearRadius;
    }

    public function setNearPoint($fLat, $fLon, $fRadius = 0.1)
    {
        $this->fNearRadius = $fRadius;
        $this->sqlNear = 'ST_SetSRID(ST_Point('.$fLon.','.$fLat.'),4326)';
    }

    /**
     * Extract a coordinate point from a query string.
     *
     * @param string $sQuery Query to scan.
     *
     * @return The remaining query string.
     */
    public function setNearPointFromQuery($sQuery)
    {
        $aResult = parseLatLon($sQuery);

        if ($aResult !== false
            && $aResult[1] <= 90.1
            && $aResult[1] >= -90.1
            && $aResult[2] <= 180.1
            && $aResult[2] >= -180.1
        ) {
            $this->setNearPoint($aResult[1], $aResult[2]);
            $sQuery = trim(str_replace($aResult[0], ' ', $sQuery));
        }

        return $sQuery;
    }

    public function distanceSQL($sObj)
    {
        return 'ST_Distance('.$this->sqlNear.", $sObj)";
    }

    public function withinSQL($sObj)
    {
        return sprintf('ST_DWithin(%s, %s, %F)', $sObj, $this->sqlNear, $this->fNearRadius);
    }
}
