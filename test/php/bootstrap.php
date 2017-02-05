<?php

//
// This file could as well be called lib/init-tests.php
//
require_once(CONST_BasePath.'/lib/lib.php');
require_once(CONST_BasePath.'/lib/init.php');


function userError($sError)
{
    throw new Exception($sError);
}


function chksql($oSql, $sMsg = false)
{
    if (PEAR::isError($oSql)) {
        throw new Exception($sMsg || $oSql->getMessage(), $oSql->userinfo);
    }

    return $oSql;
}
