<?php

	function logStart(&$oDB, $sType = '', $sQuery = '', $aLanguageList = array())
	{
		$aStartTime = explode('.',microtime(true));
		if (!$aStartTime[1]) $aStartTime[1] = '0';

		$hLog = array(
				date('Y-m-d H:i:s',$aStartTime[0]).'.'.$aStartTime[1],
				$_SERVER["REMOTE_ADDR"],
				$_SERVER['QUERY_STRING'],
				$sQuery
			);

		if (CONST_Log_DB)
		{
	                // Log
			if ($sType == 'search')
			{
		                $oDB->query('insert into query_log values ('.getDBQuoted($hLog[0]).','.getDBQuoted($hLog[3]).','.getDBQuoted($hLog[1]).')');
			}

			$sSQL = 'insert into new_query_log (type,starttime,query,ipaddress,useragent,language,format)';
			$sSQL .= ' values ('.getDBQuoted($sType).','.getDBQuoted($hLog[0]).','.getDBQuoted($hLog[2]);
			$sSQL .= ','.getDBQuoted($hLog[1]).','.getDBQuoted($_SERVER['HTTP_USER_AGENT']).','.getDBQuoted(join(',',$aLanguageList)).','.getDBQuoted($_GET['format']).')';
			$oDB->query($sSQL);
		}

		if (CONST_Log_File && CONST_Log_File_ReverseLog != '')
		{
                if ($sType == 'reverse')
                {
                        $aStartTime = explode('.',$hLog[0]);
                        file_put_contents(CONST_Log_File_ReverseLog,
                                $aStartTime[0].','.$aStartTime[1].','.
                                php_uname('n').','.
                                '"'.addslashes(isset($_SERVER['HTTP_REFERER'])?$_SERVER['HTTP_REFERER']:'').'",'.
                                '"'.addslashes($hLog[1]).'",'.
                                $_GET['lat'].','.
                                $_GET['lon'].','.
                                $_GET['zoom'].','.
                                '"'.addslashes($_SERVER['HTTP_USER_AGENT']).'",'.
                                '"'.addslashes($_GET['format']).'"'."\n",
                        FILE_APPEND);
                }
		}

		return $hLog;
	}

	function logEnd(&$oDB, $hLog, $iNumResults)
	{
                $aEndTime = explode('.',microtime(true));
                if (!$aEndTime[1]) $aEndTime[1] = '0';
                $sEndTime = date('Y-m-d H:i:s',$aEndTime[0]).'.'.$aEndTime[1];

		if (CONST_Log_DB)
		{
			$sSQL = 'update query_log set endtime = '.getDBQuoted($sEndTime).', results = '.$iNumResults;
			$sSQL .= ' where starttime = '.getDBQuoted($hLog[0]);
			$sSQL .= ' and ipaddress = '.getDBQuoted($hLog[1]);
			$sSQL .= ' and query = '.getDBQuoted($hLog[3]);
                	$oDB->query($sSQL);

			$sSQL = 'update new_query_log set endtime = '.getDBQuoted($sEndTime).', results = '.$iNumResults;
			$sSQL .= ' where starttime = '.getDBQuoted($hLog[0]);
			$sSQL .= ' and ipaddress = '.getDBQuoted($hLog[1]);
			$sSQL .= ' and query = '.getDBQuoted($hLog[2]);
			$oDB->query($sSQL);
		}

		if (CONST_Log_File && CONST_Log_File_SearchLog != '')
		{
                $aStartTime = explode('.',$hLog[0]);
                file_put_contents(CONST_Log_File_SearchLog,
                                $aStartTime[0].','.$aStartTime[1].','.
                                php_uname('n').','.
                                '"'.addslashes(isset($_SERVER['HTTP_REFERER'])?$_SERVER['HTTP_REFERER']:'').'",'.
                                '"'.addslashes($hLog[1]).'",'.
                                '"'.addslashes($hLog[3]).'",'.
                                '"'.addslashes($_SERVER['HTTP_USER_AGENT']).'",'.
                                '"'.addslashes($_GET['format']).'",'.
                                $iNumResults."\n",
                        FILE_APPEND);
		}

	}
