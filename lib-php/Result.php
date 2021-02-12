<?php

namespace Nominatim;

/**
 * A single result of a search operation or a reverse lookup.
 *
 * This object only contains the id of the result. It does not yet
 * have any details needed to format the output document.
 */
class Result
{
    const TABLE_PLACEX = 0;
    const TABLE_POSTCODE = 1;
    const TABLE_OSMLINE = 2;
    const TABLE_AUX = 3;
    const TABLE_TIGER = 4;

    /// Database table that contains the result.
    public $iTable;
    /// Id of the result.
    public $iId;
    /// House number (only for interpolation results).
    public $iHouseNumber = -1;
    /// Number of exact matches in address (address searches only).
    public $iExactMatches = 0;
    /// Subranking within the results (the higher the worse).
    public $iResultRank = 0;

    public function debugInfo()
    {
        return array(
                'Table' => $this->iTable,
                'ID' => $this->iId,
                'House number' => $this->iHouseNumber,
                'Exact Matches' => $this->iExactMatches,
                'Result rank' => $this->iResultRank
               );
    }


    public function __construct($sId, $iTable = Result::TABLE_PLACEX)
    {
        $this->iTable = $iTable;
        $this->iId = (int) $sId;
    }

    public static function joinIdsByTable($aResults, $iTable)
    {
        return join(',', array_keys(array_filter(
            $aResults,
            function ($aValue) use ($iTable) {
                return $aValue->iTable == $iTable;
            }
        )));
    }
    public static function sqlHouseNumberTable($aResults, $iTable)
    {
        $sHousenumbers = '';
        $sSep = '';
        foreach ($aResults as $oResult) {
            if ($oResult->iTable == $iTable) {
                $sHousenumbers .= $sSep.'('.$oResult->iId.',';
                $sHousenumbers .= $oResult->iHouseNumber.')';
                $sSep = ',';
            }
        }

        return $sHousenumbers;
    }

    /**
     * Split a result array into highest ranked result and the rest
     *
     * @param object[] $aResults List of results to split.
     *
     * @return array[]
     */
    public static function splitResults($aResults)
    {
        $aHead = array();
        $aTail = array();
        $iMinRank = 10000;

        foreach ($aResults as $oRes) {
            if ($oRes->iResultRank < $iMinRank) {
                $aTail = array_merge($aTail, $aHead);
                $aHead = array($oRes->iId => $oRes);
                $iMinRank = $oRes->iResultRank;
            } elseif ($oRes->iResultRank == $iMinRank) {
                $aHead[$oRes->iId] = $oRes;
            } else {
                $aTail[$oRes->iId] = $oRes;
            }
        }

        return array('head' => $aHead, 'tail' => $aTail);
    }
}
