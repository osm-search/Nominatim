<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/db.php');
require_once(CONST_BasePath.'/lib/Status.php');


class StatusTest extends \PHPUnit\Framework\TestCase
{

    public function testNoDatabaseGiven()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage('No database');
        $this->expectExceptionCode(700);

        $oDB = null;
        $oStatus = new Status($oDB);
        $this->assertEquals('No database', $oStatus->status());
    }

    public function testNoDatabaseConnectionFail()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage('No database');
        $this->expectExceptionCode(700);

        // causes 'Non-static method should not be called statically, assuming $this from incompatible context'
        // failure on travis
        // $oDB = \DB::connect('', false); // returns a DB_Error instance

        $oDB = new \DB_Error;
        $oStatus = new Status($oDB);
        $this->assertEquals('No database', $oStatus->status());

        $oDB = null;
        $oStatus = new Status($oDB);
        $this->assertEquals('No database', $oStatus->status());
    }


    public function testModuleFail()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage('Module call failed');
        $this->expectExceptionCode(702);

        // stub has getOne method but doesn't return anything
        $oDbStub = $this->getMockBuilder(\DB::class)
                        ->setMethods(array('getOne'))
                        ->getMock();

        $oStatus = new Status($oDbStub);
        $this->assertNull($oStatus->status());
    }


    public function testWordIdQueryFail()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage('No value');
        $this->expectExceptionCode(704);

        $oDbStub = $this->getMockBuilder(\DB::class)
                        ->setMethods(array('getOne'))
                        ->getMock();

        // return no word_id
        $oDbStub->method('getOne')
                ->will($this->returnCallback(function ($sql) {
                    if (preg_match("/make_standard_name\('a'\)/", $sql)) return 'a';
                    if (preg_match('/SELECT word_id, word_token/', $sql)) return null;
                }));

        $oStatus = new Status($oDbStub);
        $this->assertNull($oStatus->status());
    }


    public function testOK()
    {
        $oDbStub = $this->getMockBuilder(\DB::class)
                        ->setMethods(array('getOne'))
                        ->getMock();

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
        $oDbStub = $this->getMockBuilder(\DB::class)
                        ->setMethods(array('getOne'))
                        ->getMock();
     
        $oDbStub->method('getOne')
                ->willReturn(1519430221);

        $oStatus = new Status($oDbStub);
        $this->assertEquals(1519430221, $oStatus->dataDate());
    }
}
