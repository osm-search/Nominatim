<?php

namespace Nominatim;

use Exception;
use PEAR;

class Status
{
    protected $oDB;


    public function __construct(&$oDB)
    {
        $this->oDB =& $oDB;
    }

    // return null on success
    public function status()
    {
        if (!$this->oDB || PEAR::isError($this->oDB)) {
            return 'No database';
        }

        $sStandardWord = $this->oDB->getOne("SELECT make_standard_name('a')");
        if (PEAR::isError($sStandardWord)) {
            return 'Module failed';
        }

        if ($sStandardWord != 'a') {
            return 'Module call failed';
        }

        $sSQL = 'SELECT word_id, word_token, word, class, type, country_code, ';
        $sSQL .= "operator, search_name_count FROM word WHERE word_token IN (' a')";
        $iWordID = $this->oDB->getOne($sSQL);
        if (PEAR::isError($iWordID)) {
            return 'Query failed';
        }
        if (!$iWordID) {
            return 'No value';
        }

        return;
    }

    public function dataDate()
    {
        $sSQL = "SELECT EXTRACT(EPOCH FROM lastimportdate - '2 minutes'::interval), ";
        $sSQL .= "TO_CHAR(lastimportdate - '2 minutes'::interval,'YYYY/MM/DD HH24:MI')||' GMT' ";
        $sSQL .= 'FROM import_status LIMIT 1';
        $oDataDates = $this->oDB->getAll($sSQL);

        if (PEAR::isError($oDataDates)) {
            throw Exception('Data date query failed '.$oDataDates->getMessage());
        }
        return [
                'epoch' => $oDataDates[0][0],
                'formatted' => $oDataDates[0][1]
               ];
    }
}
