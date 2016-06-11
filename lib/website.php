<?php

/***************************************************************************
 *
 * Functions for parsing URL parameters
 *
 */

	function getParamBool($sName, $bDefault=false)
	{
		if (!isset($_GET[$sName])) return $bDefault;

		return (bool) $_GET[$sName];
	}

	function getParamInt($sName, $bDefault=false)
	{
		if (!isset($_GET[$sName])) return $bDefault;

		if (!preg_match('/^[+-][0-9]+$/', $_GET[$sName]))
		{
			userError("Integer number expected for parameter '$sName'");
		}

		return (int) $_GET[$sName];
	}

	function getParamFloat($sName, $bDefault=false)
	{
		if (!isset($_GET[$sName])) return $bDefault;

		if (!preg_match('/^[+-]?[0-9]*\.?[0-9]+$/', $_GET[$sName]))
		{
			userError("Floating-point number expected for parameter '$sName'");
		}

		return (float) $_GET[$sName];
	}

	function getParamString($sName, $bDefault=false)
	{
		if (!isset($_GET[$sName])) return $bDefault;

		return $_GET[$sName];
	}

	function getParamSet($sName, $aValues, $sDefault=false)
	{
		if (!isset($_GET[$sName])) return $sDefault;

		if (!in_array($_GET[$sName], $aValues))
		{
			userError("Parameter '$sName' must be one of: ".join(', ', $aValues));
		}

		return $_GET[$sName];
	}
