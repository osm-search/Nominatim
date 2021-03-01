<?php

namespace Nominatim;

use Exception;

class Status
{
    protected $oDB;

    public function __construct(&$oDB)
    {
        $this->oDB =& $oDB;
    }

    public function status()
    {
        if (!$this->oDB) {
            throw new Exception('No database', 700);
        }

        try {
            $this->oDB->connect();
        } catch (\Nominatim\DatabaseError $e) {
            throw new Exception('Database connection failed', 700);
        }

        $sStandardWord = $this->oDB->getOne("SELECT make_standard_name('a')");
        if ($sStandardWord === false) {
            throw new Exception('Module failed', 701);
        }

        if ($sStandardWord != 'a') {
            throw new Exception('Module call failed', 702);
        }

        $sSQL = 'SELECT word_id, word_token, word, class, type, country_code, ';
        $sSQL .= "operator, search_name_count FROM word WHERE word_token IN (' a')";
        $iWordID = $this->oDB->getOne($sSQL);
        if ($iWordID === false) {
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

        if ($iDataDateEpoch === false) {
            throw Exception('Data date query failed '.$iDataDateEpoch->getMessage(), 705);
        }

        return $iDataDateEpoch;
    }

    public function databaseVersion()
    {
        $sSQL = 'SELECT value FROM nominatim_properties WHERE property = \'database_version\'';
        return $this->oDB->getOne($sSQL);
    }
}
