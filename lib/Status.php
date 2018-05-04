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

    public function status()
    {
        if (!$this->oDB || PEAR::isError($this->oDB)) {
            throw new Exception('No database', 700);
        }

        $sStandardWord = $this->oDB->getOne("SELECT make_standard_name('a')");
        if (PEAR::isError($sStandardWord)) {
            throw new Exception('Module failed', 701);
        }

        if ($sStandardWord != 'a') {
            throw new Exception('Module call failed', 702);
        }

        $sSQL = 'SELECT word_id, word_token, word, class, type, country_code, ';
        $sSQL .= "operator, search_name_count FROM word WHERE word_token IN (' a')";
        $iWordID = $this->oDB->getOne($sSQL);
        if (PEAR::isError($iWordID)) {
            throw new Exception('Query failed', 703);
        }
        if (!$iWordID) {
            throw new Exception('No value', 704);
        }
    }

    public function dataDate()
    {
        $sSQL = 'SELECT EXTRACT(EPOCH FROM lastimportdate) FROM import_status LIMIT 1';
        $iDataDateEpoch = $this->oDB->getOne($sSQL);

        if (PEAR::isError($iDataDateEpoch)) {
            throw Exception('Data date query failed '.$iDataDateEpoch->getMessage(), 705);
        }

        return $iDataDateEpoch;
    }
}
