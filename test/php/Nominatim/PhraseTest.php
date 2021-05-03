<?php

namespace Nominatim;

require_once(CONST_LibDir.'/Phrase.php');

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
class PhraseTest extends \PHPUnit\Framework\TestCase
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
        $oPhrase = new Phrase('', '');
        $oPhrase->computeWordSets(array(), new TokensFullSet());

        $this->assertNull($oPhrase->getWordSets());
    }


    public function testSingleWordPhrase()
    {
        $oPhrase = new Phrase('a', '');
        $oPhrase->computeWordSets(array('a'), new TokensFullSet());

        $this->assertEquals(
            '(a)',
            $this->serializeSets($oPhrase->getWordSets())
        );
    }


    public function testMultiWordPhrase()
    {
        $oPhrase = new Phrase('a b', '');
        $oPhrase->computeWordSets(array('a', 'b'), new TokensFullSet());
        $this->assertEquals(
            '(a b),(a|b)',
            $this->serializeSets($oPhrase->getWordSets())
        );

        $oPhrase = new Phrase('a b c', '');
        $oPhrase->computeWordSets(array('a', 'b', 'c'), new TokensFullSet());
        $this->assertEquals(
            '(a b c),(a|b c),(a b|c),(a|b|c)',
            $this->serializeSets($oPhrase->getWordSets())
        );

        $oPhrase = new Phrase('a b c d', '');
        $oPhrase->computeWordSets(array('a', 'b', 'c', 'd'), new TokensFullSet());
        $this->assertEquals(
            '(a b c d),(a b c|d),(a b|c d),(a|b c d),(a b|c|d),(a|b c|d),(a|b|c d),(a|b|c|d)',
            $this->serializeSets($oPhrase->getWordSets())
        );
    }


    public function testInverseWordSets()
    {
        $oPhrase = new Phrase('a b c', '');
        $oPhrase->computeWordSets(array('a', 'b', 'c'), new TokensFullSet());
        $oPhrase->invertWordSets();

        $this->assertEquals(
            '(a b c),(b c|a),(c|a b),(c|b|a)',
            $this->serializeSets($oPhrase->getWordSets())
        );
    }


    public function testMaxWordSets()
    {
        $aWords = array_fill(0, 4, 'a');
        $oPhrase = new Phrase(join(' ', $aWords), '');
        $oPhrase->computeWordSets($aWords, new TokensFullSet());
        $this->assertEquals(8, count($oPhrase->getWordSets()));
        $oPhrase->invertWordSets();
        $this->assertEquals(8, count($oPhrase->getWordSets()));

        $aWords = array_fill(0, 18, 'a');
        $oPhrase = new Phrase(join(' ', $aWords), '');
        $oPhrase->computeWordSets($aWords, new TokensFullSet());
        $this->assertEquals(100, count($oPhrase->getWordSets()));
        $oPhrase->invertWordSets();
        $this->assertEquals(100, count($oPhrase->getWordSets()));
    }


    public function testPartialTokensShortTerm()
    {
        $oPhrase = new Phrase('a b c d', '');
        $oPhrase->computeWordSets(array('a', 'b', 'c', 'd'), new TokensPartialSet(array('a', 'b', 'd', 'b c', 'b c d')));
        $this->assertEquals(
            '(a|b c d),(a|b c|d)',
            $this->serializeSets($oPhrase->getWordSets())
        );
    }


    public function testPartialTokensLongTerm()
    {
        $aWords = array_fill(0, 18, 'a');
        $oPhrase = new Phrase(join(' ', $aWords), '');
        $oPhrase->computeWordSets($aWords, new TokensPartialSet(array('a', 'a a a a a')));
        $this->assertEquals(80, count($oPhrase->getWordSets()));
    }
}
