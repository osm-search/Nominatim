<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/lib.php');
require_once(CONST_BasePath.'/lib/db.php');

class DBTest extends \PHPUnit\Framework\TestCase
{

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

        $oDB = new \Nominatim\DB('');
        $oDB->connection = $oPDOStub;
        $oDB->tableExists('abc');
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
