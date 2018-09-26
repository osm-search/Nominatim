<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/Phrase.php');

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

        $this->assertEquals(
            array(array('')),
            $oPhrase->getWordSets()
        );
    }


    public function testSingleWordPhrase()
    {
        $oPhrase = new Phrase('a', '');

        $this->assertEquals(
            '(a)',
            $this->serializeSets($oPhrase->getWordSets())
        );
    }


    public function testMultiWordPhrase()
    {
        $oPhrase = new Phrase('a b', '');
        $this->assertEquals(
            '(a b),(a|b)',
            $this->serializeSets($oPhrase->getWordSets())
        );

        # trailing and multiple spaces are removed
        $oPhrase = new Phrase('  a     b  ', '');
        $this->assertEquals(
            '(a b),(a|b)',
            $this->serializeSets($oPhrase->getWordSets())
        );


        $oPhrase = new Phrase('a b c', '');
        $this->assertEquals(
            '(a b c),(a|b c),(a|b|c),(a b|c)',
            $this->serializeSets($oPhrase->getWordSets())
        );

        $oPhrase = new Phrase('a b c d', '');
        $this->assertEquals(
            '(a b c d),(a|b c d),(a|b|c d),(a|b|c|d),(a|b c|d),(a b|c d),(a b|c|d),(a b c|d)',
            $this->serializeSets($oPhrase->getWordSets())
        );
    }


    public function testInverseWordSets()
    {
        $oPhrase = new Phrase('a b c', '');
        $oPhrase->invertWordSets();

        $this->assertEquals(
            '(a b c),(c|a b),(c|b|a),(b c|a)',
            $this->serializeSets($oPhrase->getWordSets())
        );
    }


    public function testMaxDepth()
    {
        $oPhrase = new Phrase(join(' ', array_fill(0, 4, 'a')), '');
        $this->assertEquals(8, count($oPhrase->getWordSets()));
        $oPhrase->invertWordSets();
        $this->assertEquals(8, count($oPhrase->getWordSets()));

        $oPhrase = new Phrase(join(' ', array_fill(0, 18, 'a')), '');
        $this->assertEquals(41226, count($oPhrase->getWordSets()));
        $oPhrase->invertWordSets();
        $this->assertEquals(41226, count($oPhrase->getWordSets()));
    }
}
