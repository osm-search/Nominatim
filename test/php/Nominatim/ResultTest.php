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

require_once(CONST_LibDir.'/Result.php');

function mkRankedResult($iId, $iResultRank)
{
    $oResult = new Result($iId);
    $oResult->iResultRank = $iResultRank;

    return $oResult;
}


class ResultTest extends \PHPUnit\Framework\TestCase
{
    public function testSplitResults()
    {
        $aSplitResults = Result::splitResults(array(
            mkRankedResult(1, 2),
            mkRankedResult(2, 0),
            mkRankedResult(3, 0),
            mkRankedResult(4, 2),
            mkRankedResult(5, 1)
        ));


        $aHead = array_keys($aSplitResults['head']);
        $aTail = array_keys($aSplitResults['tail']);

        $this->assertEquals($aHead, array(2, 3));
        $this->assertEquals($aTail, array(1, 4, 5));
    }
}
