<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/lib.php');
require_once(CONST_BasePath.'/lib/DB.php');

// subclassing so we can set the protected connection variable
class NominatimSubClassedDB extends \Nominatim\DB
{
    public function setConnection($oConnection)
    {
        $this->connection = $oConnection;
    }
}

// phpcs:ignore PSR1.Classes.ClassDeclaration.MultipleClasses
class DBTest extends \PHPUnit\Framework\TestCase
{
    public function testReusingConnection()
    {
        $oDB = new NominatimSubClassedDB('');
        $oDB->setConnection('anything');
        $this->assertTrue($oDB->connect());
    }

    public function testDatabaseExists()
    {
        $oDB = new \Nominatim\DB('');
        $this->assertFalse($oDB->databaseExists());
    }

    public function testErrorHandling()
    {
        $this->expectException(DatabaseError::class);
        $this->expectExceptionMessage('Failed to establish database connection');

        $oDB = new \Nominatim\DB('pgsql:dbname=abc');
        $oDB->connect();
    }

    public function testErrorHandling2()
    {
        $this->expectException(DatabaseError::class);
        $this->expectExceptionMessage('Database query failed');

        $oPDOStub = $this->getMockBuilder(PDO::class)
                         ->setMethods(array('query', 'quote'))
                         ->getMock();

        $oPDOStub->method('query')
                 ->will($this->returnCallback(function ($sVal) {
                    return "'$sVal'";
                 }));

        $oPDOStub->method('query')
                 ->will($this->returnCallback(function () {
                     throw new \PDOException('ERROR:  syntax error at or near "FROM"');
                 }));

        $oDB = new NominatimSubClassedDB('');
        $oDB->setConnection($oPDOStub);
        $oDB->getOne('SELECT name FROM');
    }

    public function testGetPostgresVersion()
    {
        $oDBStub = $this->getMockBuilder(\Nominatim\DB::class)
                        ->disableOriginalConstructor()
                        ->setMethods(array('getOne'))
                        ->getMock();

        $oDBStub->method('getOne')
                ->willReturn('100006');

        $this->assertEquals(10, $oDBStub->getPostgresVersion());
    }

    public function testGetPostgisVersion()
    {
        $oDBStub = $this->getMockBuilder(\Nominatim\DB::class)
                        ->disableOriginalConstructor()
                        ->setMethods(array('getOne'))
                        ->getMock();

        $oDBStub->method('getOne')
                ->willReturn('2.4.4');

        $this->assertEquals(2.4, $oDBStub->getPostgisVersion());
    }

    public function testParseDSN()
    {
        $this->assertEquals(
            array(),
            \Nominatim\DB::parseDSN('')
        );
        $this->assertEquals(
            array(
             'database' => 'db1',
             'hostspec' => 'machine1'
            ),
            \Nominatim\DB::parseDSN('pgsql:dbname=db1;host=machine1')
        );
        $this->assertEquals(
            array(
             'database' => 'db1',
             'hostspec' => 'machine1',
             'port' => '1234',
             'username' => 'john',
             'password' => 'secret'
            ),
            \Nominatim\DB::parseDSN('pgsql:dbname=db1;host=machine1;port=1234;user=john;password=secret')
        );
    }
}
