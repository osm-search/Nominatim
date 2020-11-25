<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/lib.php');


/**
 * Collection of search constraints that are independent of the
 * actual interpretation of the search query.
 *
 * The search context is shared between all SearchDescriptions. This
 * object mainly serves as context provider for the database queries.
 * Therefore most data is directly cached as SQL statements.
 */
class SearchContext
{
    /// Search radius around a given Near reference point.
    private $fNearRadius = false;
    /// True if search must be restricted to viewbox only.
    public $bViewboxBounded = false;

    /// Reference point for search (as SQL).
    public $sqlNear = '';
    /// Viewbox selected for search (as SQL).
    public $sqlViewboxSmall = '';
    /// Viewbox with a larger buffer around (as SQL).
    public $sqlViewboxLarge = '';
    /// Reference along a route (as SQL).
    public $sqlViewboxCentre = '';
    /// List of countries to restrict search to (as SQL).
    public $sqlCountryList = '';
    /// List of place IDs to exclude (as SQL).
    private $sqlExcludeList = '';
    /// Subset of word ids of full words in the query.
    private $aFullNameWords = array();

    public function setFullNameWords($aWordList)
    {
        $this->aFullNameWords = $aWordList;
    }

    public function getFullNameTerms()
    {
        return $this->aFullNameWords;
    }

    /**
     * Check if a reference point is defined.
     *
     * @return bool True if a reference point is defined.
     */
    public function hasNearPoint()
    {
        return $this->fNearRadius !== false;
    }

    /**
     * Get radius around reference point.
     *
     * @return float Search radius around reference point.
     */
    public function nearRadius()
    {
        return $this->fNearRadius;
    }

    /**
     * Set search reference point in WGS84.
     *
     * If set, then only places around this point will be taken into account.
     *
     * @param float $fLat    Latitude of point.
     * @param float $fLon    Longitude of point.
     * @param float $fRadius Search radius around point.
     *
     * @return void
     */
    public function setNearPoint($fLat, $fLon, $fRadius = 0.1)
    {
        $this->fNearRadius = $fRadius;
        $this->sqlNear = 'ST_SetSRID(ST_Point('.$fLon.','.$fLat.'),4326)';
    }

    /**
     * Check if the search is geographically restricted.
     *
     * Searches are restricted if a reference point is given or if
     * a bounded viewbox is set.
     *
     * @return bool True, if the search is geographically bounded.
     */
    public function isBoundedSearch()
    {
        return $this->hasNearPoint() || ($this->sqlViewboxSmall && $this->bViewboxBounded);
    }

    /**
     * Set rectangular viewbox.
     *
     * The viewbox may be bounded which means that no search results
     * must be outside the viewbox.
     *
     * @param float[4] $aViewBox Coordinates of the viewbox.
     * @param bool     $bBounded True if the viewbox is bounded.
     *
     * @return void
     */
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

        $fHeight = abs($aViewBox[0] - $aViewBox[2]);
        $fWidth = abs($aViewBox[1] - $aViewBox[3]);

        $this->sqlViewboxLarge = sprintf(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(%F,%F),ST_Point(%F,%F)),4326)',
            max($aViewBox[0], $aViewBox[2]) + $fHeight,
            max($aViewBox[1], $aViewBox[3]) + $fWidth,
            min($aViewBox[0], $aViewBox[2]) - $fHeight,
            min($aViewBox[1], $aViewBox[3]) - $fWidth
        );
    }

    /**
     * Set viewbox along a route.
     *
     * The viewbox may be bounded which means that no search results
     * must be outside the viewbox.
     *
     * @param object   $oDB          Nominatim::DB instance to use for computing the box.
     * @param string[] $aRoutePoints List of x,y coordinates along a route.
     * @param float    $fRouteWidth  Buffer around the route to use.
     * @param bool     $bBounded     True if the viewbox bounded.
     *
     * @return void
     */
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
        $sGeom = $oDB->getOne('select '.$sSQL, null, 'Could not get small viewbox');
        $this->sqlViewboxSmall = "'".$sGeom."'::geometry";

        $sSQL = 'ST_BUFFER('.$this->sqlViewboxCentre.','.($fRouteWidth/30).')';
        $sGeom = $oDB->getOne('select '.$sSQL, null, 'Could not get large viewbox');
        $this->sqlViewboxLarge = "'".$sGeom."'::geometry";
    }

    /**
     * Set list of excluded place IDs.
     *
     * @param integer[] $aExcluded List of IDs.
     *
     * @return void
     */
    public function setExcludeList($aExcluded)
    {
        $this->sqlExcludeList = ' not in ('.join(',', $aExcluded).')';
    }

    /**
     * Set list of countries to restrict search to.
     *
     * @param string[] $aCountries List of two-letter lower-case country codes.
     *
     * @return void
     */
    public function setCountryList($aCountries)
    {
        $this->sqlCountryList = '('.join(',', array_map('addQuotes', $aCountries)).')';
    }

    /**
     * Extract a reference point from a query string.
     *
     * @param string $sQuery Query to scan.
     *
     * @return string The remaining query string.
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

    /**
     * Get an SQL snippet for computing the distance from the reference point.
     *
     * @param string $sObj SQL variable name to compute the distance from.
     *
     * @return string An SQL string.
     */
    public function distanceSQL($sObj)
    {
        return 'ST_Distance('.$this->sqlNear.", $sObj)";
    }

    /**
     * Get an SQL snippet for checking if something is within range of the
     * reference point.
     *
     * @param string $sObj SQL variable name to compute if it is within range.
     *
     * @return string An SQL string.
     */
    public function withinSQL($sObj)
    {
        return sprintf('ST_DWithin(%s, %s, %F)', $sObj, $this->sqlNear, $this->fNearRadius);
    }

    /**
     * Get an SQL snippet of the importance factor of the viewbox.
     *
     * The importance factor is computed by checking if an object is within
     * the viewbox and/or the extended version of the viewbox.
     *
     * @param string $sObj SQL variable name of object to weight the importance
     *
     * @return string SQL snippet of the factor with a leading multiply sign.
     */
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

    /**
     * SQL snippet checking if a place ID should be excluded.
     *
     * @param string $sVariable SQL variable name of place ID to check,
     *                          potentially prefixed with more SQL.
     *
     * @return string SQL snippet.
     */
    public function excludeSQL($sVariable)
    {
        if ($this->sqlExcludeList) {
            return $sVariable.$this->sqlExcludeList;
        }

        return '';
    }

    public function debugInfo()
    {
        return array(
                'Near radius' => $this->fNearRadius,
                'Near point (SQL)' => $this->sqlNear,
                'Bounded viewbox' => $this->bViewboxBounded,
                'Viewbox (SQL, small)' => $this->sqlViewboxSmall,
                'Viewbox (SQL, large)' => $this->sqlViewboxLarge,
                'Viewbox (SQL, centre)' => $this->sqlViewboxCentre,
                'Countries (SQL)' => $this->sqlCountryList,
                'Excluded IDs (SQL)' => $this->sqlExcludeList
               );
    }
}
