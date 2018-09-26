<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/Phrase.php');

class PhraseTest extends \PHPUnit\Framework\TestCase
{
    # Geocode.php calls the SQL function make_standard_name, which does
    # normalising and trimming.
    private function makeStandardName($sPhrase)
    {
        return preg_replace('/  +/', ' ', trim($sPhrase));
    }

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
        $oPhrase = new Phrase($this->makeStandardName('  a     b  '), '');
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


    public function testUnique()
    {
        $oPhrase = new Phrase('1 2 3 4 5 6 7 8 9 10', '');
        # serialize, then split again to get a one-dimensional array
        $aWordsets = explode(',', $this->serializeSets($oPhrase->getWordSets()));
        $this->assertEquals(count($aWordsets), count(array_unique($aWordsets)));
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


    public function testMaxSets()
    {
        // usually 100 words (even 20) would max out memory
        $oPhrase = new Phrase(join(' ', array_fill(0, 100, 'a')), '');
        $this->assertLessThan(Phrase::MAX_SETS * 1.1, count($oPhrase->getWordSets()));
        $oPhrase->invertWordSets();
        $this->assertLessThan(Phrase::MAX_SETS * 1.1, count($oPhrase->getWordSets()));
    }
}
