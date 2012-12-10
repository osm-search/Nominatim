<?php

	function getBucketMemcache()
	{
		static $m;

		if (!CONST_ConnectionBucket_MemcacheServerAddress) return null;
		if (!isset($m))
		{
		        $m = new Memcached();
        		$m->addServer(CONST_ConnectionBucket_MemcacheServerAddress, CONST_ConnectionBucket_MemcacheServerPort);
		}
		return $m;
	}

	function doBucket($asKey, $iRequestCost, $iLeakPerSecond, $iThreshold)
	{
	        $m = getBucketMemcache();
		if (!$m) return 0;

		$iMaxVal = 0;
	        $t = time();

		foreach($asKey as $sKey)
		{
		        $aCurrentBlock = $m->get($sKey);
	        	if (!$aCurrentBlock)
			{
		                $aCurrentBlock = array($iRequestCost, $t, false);
        		}
			else
			{
				// add RequestCost
				// remove leak * the time since the last request 
	        		$aCurrentBlock[0] += $iRequestCost - ($t - $aCurrentBlock[1])*$iLeakPerSecond;
		        	$aCurrentBlock[1] = $t;
			}

	        	if ($aCurrentBlock[0] <= 0)
			{
                		$m->delete($sKey);
		        }
			else
			{
				// If we have hit the threshold stop and record this to the block list
				if ($aCurrentBlock[0] >= $iThreshold)
				{
					$aCurrentBlock[0] = $iThreshold;

					// Make up to 10 attempts to record this to memcache (with locking to prevent conflicts)
					$i = 10;
					for($i = 0; $i < 10; $i++)
					{
						$aBlockedList = $m->get('blockedList', null, $hCasToken);
						if (!$aBlockedList)
						{
							$aBlockedList = array();
							$m->add('blockedList', $aBlockedList);
							$aBlockedList = $m->get('blockedList', null, $hCasToken);
						}
						if (!isset($aBlockedList[$sKey]))
						{
							$aBlockedList[$sKey] = array(1, $t);
						}
						else
						{
							$aBlockedList[$sKey][0]++;
							$aBlockedList[$sKey][1] = $t;
						}
						if (sizeof($aBlockedList) > CONST_ConnectionBucket_MaxBlockList)
						{
							uasort($aBlockedList, 'byValue1');
							$aBlockedList = array_slice($aBlockedList, 0, CONST_ConnectionBucket_MaxBlockList);
						}
						$x = $m->cas($hCasToken, 'blockedList', $aBlockedList);
						if ($x) break;
					}
				}
				// Only keep in memcache until the time it would have expired (to avoid clutering memcache)
	                	$m->set($sKey, $aCurrentBlock, $t + 1 + $aCurrentBlock[0]/$iLeakPerSecond);
			}

			// Bucket result in the largest bucket we find
			$iMaxVal = max($iMaxVal, $aCurrentBlock[0]);
		}

		return $iMaxVal;
        }

	function isBucketSleeping($asKey)
	{
	        $m = getBucketMemcache();
		if (!$m) return false;

		foreach($asKey as $sKey)
		{
		        $aCurrentBlock = $m->get($sKey);
			if ($aCurrentBlock[2]) return true;
		}
		return false;
	}

	function setBucketSleeping($asKey, $bVal)
	{
	        $m = getBucketMemcache();
		if (!$m) return false;

		$iMaxVal = 0;
	        $t = time();

		foreach($asKey as $sKey)
		{
		        $aCurrentBlock = $m->get($sKey);
			$aCurrentBlock[2] = $bVal;
			$m->set($sKey, $aCurrentBlock, $t + 1 + $aCurrentBlock[0]/CONST_ConnectionBucket_LeakRate);
		}
		return true;
	}

	function byValue1($a, $b)
	{
		if ($a[1] == $b[1])
		{
			return 0;
		}
		return ($a[1] > $b[1]) ? -1 : 1;
	}

	function byLastBlockTime($a, $b)
	{
		if ($a['lastBlockTimestamp'] == $b['lastBlockTimestamp'])
		{
			return 0;
		}
		return ($a['lastBlockTimestamp'] > $b['lastBlockTimestamp']) ? -1 : 1;
	}

	function getBucketBlocks()
	{
	        $m = getBucketMemcache();
		if (!$m) return null;
	        $t = time();
		$aBlockedList = $m->get('blockedList', null, $hCasToken);
		if (!$aBlockedList) $aBlockedList = array();
		foreach($aBlockedList as $sKey => $aDetails)
		{
			$aCurrentBlock = $m->get($sKey);
			if (!$aCurrentBlock) $aCurrentBlock = array(0, $t);
			$iCurrentBucketSize = max(0, $aCurrentBlock[0] - ($t - $aCurrentBlock[1])*CONST_ConnectionBucket_LeakRate);
			$aBlockedList[$sKey] = array(
				'totalBlocks' => $aDetails[0],
				'lastBlockTimestamp' => $aDetails[1],
				'isSleeping' => (isset($aCurrentBlock[2])?$aCurrentBlock[2]:false),
				'currentBucketSize' => $iCurrentBucketSize,
				'currentlyBlocked' => $iCurrentBucketSize + (CONST_ConnectionBucket_Cost_Reverse) >= CONST_ConnectionBucket_BlockLimit,
				);
		}
		uasort($aBlockedList, 'byLastBlockTime');
		return $aBlockedList;
	}

	function clearBucketBlocks()
	{
	        $m = getBucketMemcache();
		if (!$m) return false;
		$m->delete('blockedList');
		return true;
	}
