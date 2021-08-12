<?php

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
            '(a b c),(a|b c),(a b|c),(a|b|c)',
            $this->serializeSets($oList->getWordSets(new TokensFullSet()))
        );

        $oList = new SimpleWordList('a b c d');
        $this->assertEquals(
            '(a b c d),(a b c|d),(a b|c d),(a|b c d),(a b|c|d),(a|b c|d),(a|b|c d),(a|b|c|d)',
            $this->serializeSets($oList->getWordSets(new TokensFullSet()))
        );
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
