<?php

namespace Nominatim;

// require_once(CONST_BasePath.'/lib/db.php');
// require_once(CONST_BasePath.'/lib/cmd.php');
require_once(CONST_BasePath.'/lib/TokenList.php');


class TokenTest extends \PHPUnit\Framework\TestCase
{
    protected function setUp()
    {
        $this->oNormalizer = $this->getMockBuilder(\MockNormalizer::class)
                                  ->setMethods(array('transliterate'))
                                  ->getMock();
        $this->oNormalizer->method('transliterate')
                          ->will($this->returnCallback(function ($text) {
                              return strtolower($text);
                          }));
    }

    private function wordResult($aFields)
    {
        $aRow = array(
                 'word_id' => null,
                 'word_token' => null,
                 'word' => null,
                 'class' => null,
                 'type' => null,
                 'country_code' => null,
                 'count' => 0
                );
        return array_merge($aRow, $aFields);
    }

    public function testList()
    {
        $TL = new TokenList;

        $this->assertEquals(0, $TL->count());

        $TL->addToken('word1', 'token1');
        $TL->addToken('word1', 'token2');

        $this->assertEquals(1, $TL->count());

        $this->assertTrue($TL->contains('word1'));
        $this->assertEquals(array('token1', 'token2'), $TL->get('word1'));

        $this->assertFalse($TL->contains('unknownword'));
        $this->assertEquals(array(), $TL->get('unknownword'));
    }

    public function testAddress()
    {
        $this->expectOutputRegex('/<p><tt>/');

        $oDbStub = $this->getMockBuilder(\DB::class)
                        ->setMethods(array('getAll'))
                        ->getMock();
        $oDbStub->method('getAll')
                ->will($this->returnCallback(function ($sql) {
                    $aResults = array();
                    if (preg_match('/1051/', $sql)) {
                        $aResults[] = $this->wordResult(array(
                                                         'word_id' => 999,
                                                         'word_token' => '1051',
                                                         'class' => 'place',
                                                         'type' => 'house'
                                                        ));
                    }
                    if (preg_match('/64286/', $sql)) {
                        $aResults[] = $this->wordResult(array(
                                                         'word_id' => 999,
                                                         'word_token' => '64286',
                                                         'word' => '64286',
                                                         'class' => 'place',
                                                         'type' => 'postcode'
                                                        ));
                    }
                    if (preg_match('/darmstadt/', $sql)) {
                        $aResults[] = $this->wordResult(array(
                                                         'word_id' => 999,
                                                         'word_token' => 'darmstadt',
                                                         'count' => 533
                                                        ));
                    }
                    if (preg_match('/alemagne/', $sql)) {
                        $aResults[] = $this->wordResult(array(
                                                         'word_id' => 999,
                                                         'word_token' => 'alemagne',
                                                         'country_code' => 'de',
                                                        ));
                    }
                    if (preg_match('/mexico/', $sql)) {
                        $aResults[] = $this->wordResult(array(
                                                         'word_id' => 999,
                                                         'word_token' => 'mexico',
                                                         'country_code' => 'mx',
                                                        ));
                    }
                    return $aResults;
                }));

        $aCountryCodes = array('de', 'fr');
        $sNormQuery = '1051 hauptstr 64286 darmstadt alemagne mexico';
        $aTokens = explode(' ', $sNormQuery);

        $TL = new TokenList;
        $TL->addTokensFromDB($oDbStub, $aTokens, $aCountryCodes, $sNormQuery, $this->oNormalizer);
        $this->assertEquals(4, $TL->count());

        $this->assertEquals(array(new Token\HouseNumber(999, '1051')), $TL->get('1051'));
        $this->assertEquals(array(new Token\Country(999, 'de')), $TL->get('alemagne'));
        $this->assertEquals(array(new Token\Postcode(999, '64286')), $TL->get('64286'));
        $this->assertEquals(array(new Token\Word(999, true, 533)), $TL->get('darmstadt'));
    }
}
