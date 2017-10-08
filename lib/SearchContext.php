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
    public $bViewboxBounded = false;

    public $sqlNear = '';
    public $sqlViewboxSmall = '';
    public $sqlViewboxLarge = '';
    public $sqlViewboxCentre = '';
    public $sqlCountryList = '';
    private $sqlExcludeList = '';

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

    public function isBoundedSearch()
    {
        return $this->hasNearPoint() || ($this->sqlViewboxSmall && $this->bViewboxBounded);

    }

    public function setViewboxFromBox(&$aViewBox, $bBounded)
    {
        $this->bViewboxBounded = $bBounded;
        $this->sqlViewboxCentre = '';

        $this->sqlViewboxSmall = sprintf(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(%F,%F),ST_Point(%F,%F)),4326)',
            $aViewBox[0],
            $aViewBox[1],
            $aViewBox[2],
            $aViewBox[3]
        );

        $fHeight = $aViewBox[0] - $aViewBox[2];
        $fWidth = $aViewBox[1] - $aViewBox[3];

        $this->sqlViewboxLarge = sprintf(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(%F,%F),ST_Point(%F,%F)),4326)',
            max($aViewBox[0], $aViewBox[2]) + $fHeight,
            max($aViewBox[1], $aViewBox[3]) + $fWidth,
            min($aViewBox[0], $aViewBox[2]) - $fHeight,
            min($aViewBox[1], $aViewBox[3]) - $fWidth
        );
    }

    public function setViewboxFromRoute(&$oDB, $aRoutePoints, $fRouteWidth, $bBounded)
    {
        $this->bViewboxBounded = $bBounded;
        $this->sqlViewboxCentre = "ST_SetSRID('LINESTRING(";
        $sSep = '';
        foreach ($aRoutePoints as $aPoint) {
            $fPoint = (float)$aPoint;
            $this->sqlViewboxCentre .= $sSep.$fPoint;
            $sSep = ($sSep == ' ') ? ',' : ' ';
        }
        $this->sqlViewboxCentre .= ")'::geometry,4326)";

        $sSQL = 'ST_BUFFER('.$this->sqlViewboxCentre.','.($fRouteWidth/69).')';
        $sGeom = chksql($oDB->getOne("select ".$sSQL), "Could not get small viewbox");
        $this->sqlViewboxSmall = "'".$sGeom."'::geometry";

        $sSQL = 'ST_BUFFER('.$this->sqlViewboxCentre.','.($fRouteWidth/30).')';
        $sGeom = chksql($oDB->getOne("select ".$sSQL), "Could not get large viewbox");
        $this->sqlViewboxLarge = "'".$sGeom."'::geometry";
    }

    public function setExcludeList($aExcluded)
    {
        $this->sqlExcludeList = ' not in ('.join(',', $aExcluded).')';
    }

    public function setCountryList($aCountries)
    {
        $this->sqlCountryList = '('.join(',', array_map('addQuotes', $aCountries)).')';
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

    public function viewboxImportanceSQL($sObj)
    {
        $sSQL = '';

        if ($this->sqlViewboxSmall) {
            $sSQL = " * CASE WHEN ST_Contains($this->sqlViewboxSmall, $sObj) THEN 1 ELSE 0.5 END";
        }
        if ($this->sqlViewboxLarge) {
            $sSQL = " * CASE WHEN ST_Contains($this->sqlViewboxLarge, $sObj) THEN 1 ELSE 0.5 END";
        }

        return $sSQL;
    }

    public function excludeSQL($sVariable)
    {
        if ($this->sqlExcludeList) {
            return $sVariable.$this->sqlExcludeList;
        }

        return '';
    }
}
