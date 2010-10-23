<?php
	require_once('DB.php');

	// Get the database object
	$oDB =& DB::connect(CONST_Database_DSN, false);
	if (PEAR::IsError($oDB))
	{
		fail($oDB->getMessage(), 'Unable to connect to the database');
	}
	$oDB->setFetchMode(DB_FETCHMODE_ASSOC);
	$oDB->query("SET DateStyle TO 'sql,european'");
	$oDB->query("SET client_encoding TO 'utf-8'");

	function getDBQuoted($s)
	{
		return "'".pg_escape_string($s)."'";
	}

