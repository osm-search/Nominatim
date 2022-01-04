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

require_once(CONST_TokenizerDir.'/tokenizer.php');

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

        $oTokenizer = new \Nominatim\Tokenizer($this->oDB);
        $oTokenizer->checkStatus();
    }

    public function dataDate()
    {
        $sSQL = 'SELECT EXTRACT(EPOCH FROM lastimportdate) FROM import_status LIMIT 1';
        $iDataDateEpoch = $this->oDB->getOne($sSQL);

        if ($iDataDateEpoch === false) {
            throw new Exception('Import date is not available', 705);
        }

        return $iDataDateEpoch;
    }

    public function databaseVersion()
    {
        $sSQL = 'SELECT value FROM nominatim_properties WHERE property = \'database_version\'';
        return $this->oDB->getOne($sSQL);
    }
}
