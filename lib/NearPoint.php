<?php

namespace Nominatim;

/**
 * A geographic point with a search radius.
 */
class NearPoint
{
    private $fLat;
    private $fLon;
    private $fRadius;

    private $sSQL;


    public function __construct($lat, $lon, $radius = 0.1)
    {
        $this->fLat = (float)$lat;
        $this->fLon = (float)$lon;
        $this->fRadius = (float)$radius;
        $this->sSQL = 'ST_SetSRID(ST_Point('.$this->fLon.','.$this->fLat.'),4326)';
    }

    public function lat()
    {
        return $this->fLat;
    }

    public function lon()
    {
        return $this->fLon;
    }

    public function radius()
    {
        return $this->fRadius;
    }

    public function distanceSQL($sObj)
    {
        return 'ST_Distance('.$this->sSQL.", $sObj)";
    }

    public function withinSQL($sObj)
    {
        return sprintf('ST_DWithin(%s, %s, %F)', $sObj, $this->sSQL, $this->fRadius);
    }

    /**
     * Check that the coordinates are valid WSG84 coordinates.
     *
     * @return bool True if the coordinates are correctly bounded.
     */
    public function isValid()
    {
        return ($this->fLat <= 90.1
                && $this->fLat >= -90.1
                && $this->fLon <= 180.1
                && $this->fLon >= -180.1);
    }

    /**
     * Extract a coordinate point from a query string.
     *
     * If a coordinate is found an array of a new NearPoint and the
     * remaining query is returned or false otherwise.
     *
     * @param string $sQuery Query to scan.
     *
     * @return array|false If a coordinate was found, an array with
     *                     `pt` as the NearPoint coordinates and `query`
     *                      with the remaining query string. False otherwiese.
     */
    public static function extractFromQuery($sQuery)
    {
        // Do we have anything that looks like a lat/lon pair?
        // returns array(lat,lon,query_with_lat_lon_removed)
        // or null
        $sFound    = null;
        $fQueryLat = null;
        $fQueryLon = null;

        if (preg_match('/\\b([NS])[ ]+([0-9]+[0-9.]*)[° ]+([0-9.]+)?[′\']*[, ]+([EW])[ ]+([0-9]+)[° ]+([0-9]+[0-9.]*)[′\']*?\\b/', $sQuery, $aData)) {
            /*              1         2                   3                  4         5            6
             * degrees decimal minutes
             * N 40 26.767, W 79 58.933
             * N 40°26.767′, W 79°58.933′
             */
            $sFound    = $aData[0];
            $fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2] + $aData[3]/60);
            $fQueryLon = ($aData[4]=='E'?1:-1) * ($aData[5] + $aData[6]/60);
        } elseif (preg_match('/\\b([0-9]+)[° ]+([0-9]+[0-9.]*)?[′\']*[ ]+([NS])[, ]+([0-9]+)[° ]+([0-9]+[0-9.]*)?[′\' ]+([EW])\\b/', $sQuery, $aData)) {
            /*                    1             2                      3          4            5                    6
             * degrees decimal minutes
             * 40 26.767 N, 79 58.933 W
             * 40° 26.767′ N 79° 58.933′ W
             */
            $sFound    = $aData[0];
            $fQueryLat = ($aData[3]=='N'?1:-1) * ($aData[1] + $aData[2]/60);
            $fQueryLon = ($aData[6]=='E'?1:-1) * ($aData[4] + $aData[5]/60);
        } elseif (preg_match('/\\b([NS])[ ]([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″"]*[, ]+([EW])[ ]([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″"]*\\b/', $sQuery, $aData)) {
            /*                    1        2            3            4                5        6            7            8
             * degrees decimal seconds
             * N 40 26 46 W 79 58 56
             * N 40° 26′ 46″, W 79° 58′ 56″
             */
            $sFound    = $aData[0];
            $fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2] + $aData[3]/60 + $aData[4]/3600);
            $fQueryLon = ($aData[5]=='E'?1:-1) * ($aData[6] + $aData[7]/60 + $aData[8]/3600);
        } elseif (preg_match('/\\b([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″" ]+([NS])[, ]+([0-9]+)[° ]+([0-9]+)[′\' ]+([0-9]+)[″" ]+([EW])\\b/', $sQuery, $aData)) {
            /*                    1            2            3            4          5            6            7            8
             * degrees decimal seconds
             * 40 26 46 N 79 58 56 W
             * 40° 26′ 46″ N, 79° 58′ 56″ W
             */
            $sFound    = $aData[0];
            $fQueryLat = ($aData[4]=='N'?1:-1) * ($aData[1] + $aData[2]/60 + $aData[3]/3600);
            $fQueryLon = ($aData[8]=='E'?1:-1) * ($aData[5] + $aData[6]/60 + $aData[7]/3600);
        } elseif (preg_match('/\\b([NS])[ ]([0-9]+[0-9]*\\.[0-9]+)[°]*[, ]+([EW])[ ]([0-9]+[0-9]*\\.[0-9]+)[°]*\\b/', $sQuery, $aData)) {
            /*                    1        2                               3        4
             * degrees decimal
             * N 40.446° W 79.982°
             */
            $sFound    = $aData[0];
            $fQueryLat = ($aData[1]=='N'?1:-1) * ($aData[2]);
            $fQueryLon = ($aData[3]=='E'?1:-1) * ($aData[4]);
        } elseif (preg_match('/\\b([0-9]+[0-9]*\\.[0-9]+)[° ]+([NS])[, ]+([0-9]+[0-9]*\\.[0-9]+)[° ]+([EW])\\b/', $sQuery, $aData)) {
            /*                    1                           2          3                           4
             * degrees decimal
             * 40.446° N 79.982° W
             */
            $sFound    = $aData[0];
            $fQueryLat = ($aData[2]=='N'?1:-1) * ($aData[1]);
            $fQueryLon = ($aData[4]=='E'?1:-1) * ($aData[3]);
        } elseif (preg_match('/(\\[|^|\\b)(-?[0-9]+[0-9]*\\.[0-9]+)[, ]+(-?[0-9]+[0-9]*\\.[0-9]+)(\\]|$|\\b)/', $sQuery, $aData)) {
            /*                 1          2                             3                        4
             * degrees decimal
             * 12.34, 56.78
             * [12.456,-78.90]
             */
            $sFound    = $aData[0];
            $fQueryLat = $aData[2];
            $fQueryLon = $aData[3];
        } else {
            return false;
        }

        $oPt = new NearPoint($fQueryLat, $fQueryLon);

        if (!$oPt->isValid()) return false;

        $sQuery = trim(str_replace($sFound, ' ', $sQuery));

        return array('pt' => $oPt, 'query' => $sQuery);
    }
}
