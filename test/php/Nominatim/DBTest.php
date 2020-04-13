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

    public function testCheckConnection()
    {
        $oDB = new \Nominatim\DB('');
        $this->assertFalse($oDB->checkConnection());
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

    public function testGenerateDSN()
    {
        $this->assertEquals(
            'pgsql:',
            \Nominatim\DB::generateDSN(array())
        );
        $this->assertEquals(
            'pgsql:host=machine1;dbname=db1',
            \Nominatim\DB::generateDSN(\Nominatim\DB::parseDSN('pgsql:host=machine1;dbname=db1'))
        );
    }

    public function testAgainstDatabase()
    {
        if (getenv('UNIT_TEST_DSN') == false) $this->markTestSkipped('UNIT_TEST_DSN not set');

        ## Create the database.
        {
            $aDSNParsed = \Nominatim\DB::parseDSN(getenv('UNIT_TEST_DSN'));
            $sDbname = $aDSNParsed['database'];
            $aDSNParsed['database'] = 'postgres';

            $oDB = new \Nominatim\DB(\Nominatim\DB::generateDSN($aDSNParsed));
            $oDB->connect();
            $oDB->exec('DROP DATABASE IF EXISTS ' . $sDbname);
            $oDB->exec('CREATE DATABASE ' . $sDbname);
        }

        $oDB = new \Nominatim\DB(getenv('UNIT_TEST_DSN'));
        $oDB->connect();

        $this->assertTrue(
            $oDB->checkConnection($sDbname)
        );

        # Tables, Indices
        {
            $this->assertEmpty($oDB->getListOfTables());
            $oDB->exec('CREATE TABLE table1 (id integer, city varchar, country varchar)');
            $oDB->exec('CREATE TABLE table2 (id integer, city varchar, country varchar)');
            $this->assertEquals(
                array('table1', 'table2'),
                $oDB->getListOfTables()
            );
            $this->assertTrue($oDB->deleteTable('table2'));
            $this->assertTrue($oDB->deleteTable('table99'));
            $this->assertEquals(
                array('table1'),
                $oDB->getListOfTables()
            );

            $this->assertTrue($oDB->tableExists('table1'));
            $this->assertFalse($oDB->tableExists('table99'));
            $this->assertFalse($oDB->tableExists(null));

            $this->assertEmpty($oDB->getListOfIndices());
            $oDB->exec('CREATE UNIQUE INDEX table1_index ON table1 (id)');
            $this->assertEquals(
                array('table1_index'),
                $oDB->getListOfIndices()
            );
            $this->assertEmpty($oDB->getListOfIndices('table2'));
        }

        # select queries
        {
            $oDB->exec(
                "INSERT INTO table1 VALUES (1, 'Berlin', 'Germany'), (2, 'Paris', 'France')"
            );

            $this->assertEquals(
                array(
                    array('city' => 'Berlin'),
                    array('city' => 'Paris')
                ),
                $oDB->getAll('SELECT city FROM table1')
            );
            $this->assertEquals(
                array(),
                $oDB->getAll('SELECT city FROM table1 WHERE id=999')
            );


            $this->assertEquals(
                array('id' => 1, 'city' => 'Berlin', 'country' => 'Germany'),
                $oDB->getRow('SELECT * FROM table1 WHERE id=1')
            );
            $this->assertEquals(
                false,
                $oDB->getRow('SELECT * FROM table1 WHERE id=999')
            );


            $this->assertEquals(
                array('Berlin', 'Paris'),
                $oDB->getCol('SELECT city FROM table1')
            );
            $this->assertEquals(
                array(),
                $oDB->getCol('SELECT city FROM table1 WHERE id=999')
            );

            $this->assertEquals(
                'Berlin',
                $oDB->getOne('SELECT city FROM table1 WHERE id=1')
            );
            $this->assertEquals(
                null,
                $oDB->getOne('SELECT city FROM table1 WHERE id=999')
            );

            $this->assertEquals(
                array('Berlin' => 'Germany', 'Paris' => 'France'),
                $oDB->getAssoc('SELECT city, country FROM table1')
            );
            $this->assertEquals(
                array(),
                $oDB->getAssoc('SELECT city, country FROM table1 WHERE id=999')
            );
        }
    }
}
