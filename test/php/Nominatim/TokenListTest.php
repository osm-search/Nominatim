<?php

namespace Nominatim;

require_once(CONST_LibDir.'/TokenList.php');


class TokenListTest extends \PHPUnit\Framework\TestCase
{
    protected function setUp(): void
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
}
