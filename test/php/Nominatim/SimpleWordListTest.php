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

require_once(CONST_LibDir.'/SimpleWordList.php');

class TokensFullSet
{
    public function containsAny($sTerm)
    {
        return true;
    }
}

// phpcs:ignore PSR1.Classes.ClassDeclaration.MultipleClasses
class TokensPartialSet
{
    public function __construct($aTokens)
    {
        $this->aTokens = array_flip($aTokens);
    }

    public function containsAny($sTerm)
    {
        return isset($this->aTokens[$sTerm]);
    }
}

// phpcs:ignore PSR1.Classes.ClassDeclaration.MultipleClasses
class SimpleWordListTest extends \PHPUnit\Framework\TestCase
{


    private function serializeSets($aSets)
    {
        $aParts = array();
        foreach ($aSets as $aSet) {
            $aParts[] = '(' . join('|', $aSet) . ')';
        }
        return join(',', $aParts);
    }


    public function testEmptyPhrase()
    {
        $oList = new SimpleWordList('');
        $this->assertNull($oList->getWordSets(new TokensFullSet()));
    }


    public function testSingleWordPhrase()
    {
        $oList = new SimpleWordList('a');

        $this->assertEquals(
            '(a)',
            $this->serializeSets($oList->getWordSets(new TokensFullSet()))
        );
    }


    public function testMultiWordPhrase()
    {
        $oList = new SimpleWordList('a b');
        $this->assertEquals(
            '(a b),(a|b)',
            $this->serializeSets($oList->getWordSets(new TokensFullSet()))
        );

        $oList = new SimpleWordList('a b c');
        $this->assertEquals(
            '(a b c),(a b|c),(a|b c),(a|b|c)',
            $this->serializeSets($oList->getWordSets(new TokensFullSet()))
        );

        $oList = new SimpleWordList('a b c d');
        $this->assertEquals(
            '(a b c d),(a b c|d),(a b|c d),(a|b c d),(a b|c|d),(a|b c|d),(a|b|c d),(a|b|c|d)',
            $this->serializeSets($oList->getWordSets(new TokensFullSet()))
        );
    }

    public function testCmpByArraylen()
    {
        // Array elements are phrases, we want to sort so longest phrases are first
        $aList1 = array('hackney', 'bridge', 'london', 'england');
        $aList2 = array('hackney', 'london', 'bridge');
        $aList3 = array('bridge', 'hackney', 'london', 'england');

        $this->assertEquals(0, \Nominatim\SimpleWordList::cmpByArraylen($aList1, $aList1));

        // list2 "wins". Less array elements
        $this->assertEquals(1, \Nominatim\SimpleWordList::cmpByArraylen($aList1, $aList2));
        $this->assertEquals(-1, \Nominatim\SimpleWordList::cmpByArraylen($aList2, $aList3));

        // list1 "wins". Same number of array elements but longer first element
        $this->assertEquals(-1, \Nominatim\SimpleWordList::cmpByArraylen($aList1, $aList3));
    }

    public function testMaxWordSets()
    {
        $aWords = array_fill(0, 4, 'a');
        $oList = new SimpleWordList(join(' ', $aWords));
        $this->assertEquals(8, count($oList->getWordSets(new TokensFullSet())));

        $aWords = array_fill(0, 18, 'a');
        $oList = new SimpleWordList(join(' ', $aWords));
        $this->assertEquals(100, count($oList->getWordSets(new TokensFullSet())));
    }


    public function testPartialTokensShortTerm()
    {
        $oList = new SimpleWordList('a b c d');
        $this->assertEquals(
            '(a|b c d),(a|b c|d)',
            $this->serializeSets($oList->getWordSets(new TokensPartialSet(array('a', 'b', 'd', 'b c', 'b c d'))))
        );
    }


    public function testPartialTokensLongTerm()
    {
        $aWords = array_fill(0, 18, 'a');
        $oList = new SimpleWordList(join(' ', $aWords));
        $this->assertEquals(80, count($oList->getWordSets(new TokensPartialSet(array('a', 'a a a a a')))));
    }
}
