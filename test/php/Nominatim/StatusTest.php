<?php

namespace Nominatim;

<<<<<<< HEAD
<<<<<<< HEAD
require_once('../../lib/db.php');
require_once('../../lib/Status.php');
=======
require_once('../../lib/Status.php');
require_once('DB.php');
>>>>>>> /status can now output json, including data date
=======
require_once('../../lib/db.php');
require_once('../../lib/Status.php');
>>>>>>> travis: try to get DB.php to load

class StatusTest extends \PHPUnit_Framework_TestCase
{


    public function testNoDatabaseConnectionFail()
    {
        $oDB = \DB::connect('', false); // returns a DB_Error instance

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
        $this->assertEquals('OK', $oStatus->status());
    }

    public function testDataDate()
    {
        $oDbStub = $this->getMock(\DB::class, ['getAll']);
     
        $oDbStub->method('getAll')
                ->willReturn([[1519430221, '2018/02/23 23:57 GMT']]);

        $oStatus = new Status($oDbStub);
        $this->assertEquals([
                             'epoch' => 1519430221,
                             'formatted' => '2018/02/23 23:57 GMT'
                            ], $oStatus->dataDate());
    }
}
