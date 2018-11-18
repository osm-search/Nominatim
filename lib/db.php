<?php

require_once('DB.php');


function &getDB($bNew = false, $bPersistent = false)
{
    // Get the database object
    $oDB = chksql(
        DB::connect(CONST_Database_DSN.($bNew?'?new_link=true':''), $bPersistent),
        'Failed to establish database connection'
    );
    $oDB->setFetchMode(DB_FETCHMODE_ASSOC);
    $oDB->query("SET DateStyle TO 'sql,european'");
    $oDB->query("SET client_encoding TO 'utf-8'");
    $iMaxExecution = ini_get('max_execution_time') * 1000;
    if ($iMaxExecution > 0) $oDB->query("SET statement_timeout TO $iMaxExecution");
    return $oDB;
}

function getDBQuoted($s)
{
    return "'".pg_escape_string($s)."'";
}

function getArraySQL($a)
{
    return 'ARRAY['.join(',', $a).']';
}

function getPostgresVersion(&$oDB)
{
    $sVersionString = $oDB->getOne('SHOW server_version_num');
    preg_match('#([0-9]?[0-9])([0-9][0-9])[0-9][0-9]#', $sVersionString, $aMatches);
    return (float) ($aMatches[1].'.'.$aMatches[2]);
}

function getPostgisVersion(&$oDB)
{
    $sVersionString = $oDB->getOne('select postgis_lib_version()');
    preg_match('#^([0-9]+)[.]([0-9]+)[.]#', $sVersionString, $aMatches);
    return (float) ($aMatches[1].'.'.$aMatches[2]);
}
