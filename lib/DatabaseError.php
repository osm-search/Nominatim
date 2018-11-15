<?php

namespace Nominatim;

class DatabaseError extends \Exception
{

    public function __construct($message, $code = 500, Exception $previous = null, $oSql)
    {
        parent::__construct($message, $code, $previous);
        $this->oSql = $oSql;
    }

    public function __toString()
    {
        return __CLASS__ . ": [{$this->code}]: {$this->message}\n";
    }

    public function getSqlError()
    {
        return $this->oSql->getMessage();
    }

    public function getSqlDebugDump()
    {
        if (CONST_Debug) {
            return var_export($this->oSql, true);
        } else {
            return $this->oSql->getUserInfo();
        }
    }
}
