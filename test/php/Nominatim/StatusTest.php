<?php

namespace Nominatim;

require_once('../../lib/Status.php');
require_once('DB.php');

class StatusTest extends \PHPUnit_Framework_TestCase
{


    public function testNoDatabaseConnectionFail()
    {

        print get_include_path();

        // causes 'Non-static method should not be called statically, assuming $this from incompatible context'
        // failure on travis
        // $oDB = \DB::connect('', false); // returns a DB_Error instance
        $oDB = null;

        $oStatus = new Status($oDB);
        $this->assertEquals('No database', $oStatus->status());
    }


    public function testModuleFail()
    {
        // stub has getOne method but doesn't return anything
        $oDbStub = $this->getMock(\DB::class, ['getOne']);

        $oStatus = new Status($oDbStub);
        $this->assertEquals('Module call failed', $oStatus->status());
    }


    public function testWordIdQueryFail()
    {
        $oDbStub = $this->getMock(\DB::class, ['getOne']);

        // return no word_id
        $oDbStub->method('getOne')
                ->will($this->returnCallback(function ($sql) {
                    if (preg_match("/make_standard_name\('a'\)/", $sql)) return 'a';
                    if (preg_match('/SELECT word_id, word_token/', $sql)) return null;
                }));

        $oStatus = new Status($oDbStub);
        $this->assertEquals('No value', $oStatus->status());
    }


    public function testOK()
    {
        $oDbStub = $this->getMock(\DB::class, ['getOne']);

        $oDbStub->method('getOne')
                ->will($this->returnCallback(function ($sql) {
                    if (preg_match("/make_standard_name\('(\w+)'\)/", $sql, $aMatch)) return $aMatch[1];
                    if (preg_match('/SELECT word_id, word_token/', $sql)) return 1234;
                }));

        $oStatus = new Status($oDbStub);
        $this->assertNull($oStatus->status());
    }

    public function testDataDate()
    {
        $oDbStub = $this->getMock(\DB::class, ['getOne']);
     
        $oDbStub->method('getOne')
                ->willReturn(1519430221);

        $oStatus = new Status($oDbStub);
        $this->assertEquals(1519430221, $oStatus->dataDate());
    }
}
