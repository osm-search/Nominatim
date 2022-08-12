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

class DatabaseError extends \Exception
{

    public function __construct($message, $code, $previous, $oPDOErr, $sSql = null)
    {
        parent::__construct($message, $code, $previous);
        // https://secure.php.net/manual/en/class.pdoexception.php
        $this->oPDOErr = $oPDOErr;
        $this->sSql = $sSql;
    }

    public function __toString()
    {
        return __CLASS__ . ": [{$this->code}]: {$this->message}\n";
    }

    public function getSqlError()
    {
        return $this->oPDOErr->getMessage();
    }

    public function getSqlDebugDump()
    {
        if (CONST_Debug) {
            return var_export($this->oPDOErr, true);
        } else {
            return $this->sSql;
        }
    }
}
