<?php
	require_once('DB.php');

	function &getDB($bNew = false, $bPersistent = false)
	{
		// Get the database object
		$oDB =& DB::connect(CONST_Database_DSN.($bNew?'?new_link=true':''), $bPersistent);
		if (PEAR::IsError($oDB))
		{
			var_dump(CONST_Database_DSN);
			var_Dump($oDB);
			fail($oDB->getMessage());
		}
		$oDB->setFetchMode(DB_FETCHMODE_ASSOC);
		$oDB->query("SET DateStyle TO 'sql,european'");
		$oDB->query("SET client_encoding TO 'utf-8'");
		return $oDB;
	}

	function getDBQuoted($s)
	{
		return "'".pg_escape_string($s)."'";
	}

