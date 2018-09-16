<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/DatabaseError.php');

class DatabaseErrorTest extends \PHPUnit\Framework\TestCase
{

    public function testSqlMessage()
    {
        $oSqlStub = $this->getMockBuilder(\DB_Error::class)
                    ->setMethods(array('getMessage'))
                    ->getMock();

        $oSqlStub->method('getMessage')
                ->willReturn('Unknown table.');

        $oErr = new DatabaseError('Sql error', 123, null, $oSqlStub);
        $this->assertEquals('Sql error', $oErr->getMessage());
        $this->assertEquals(123, $oErr->getCode());
        $this->assertEquals('Unknown table.', $oErr->getSqlError());

        // causes a circular reference warning during dump
        // $this->assertRegExp('/Mock_DB_Error/', $oErr->getSqlDebugDump());
    }

    public function testSqlObjectDump()
    {
        $oErr = new DatabaseError('Sql error', 123, null, array('one' => 'two'));
        $this->assertRegExp('/two/', $oErr->getSqlDebugDump());
    }

    public function testChksqlThrows()
    {
        $this->expectException(DatabaseError::class);
        $this->expectExceptionMessage('My custom error message');
        $this->expectExceptionCode(500);

        $oDB = new \DB_Error;
        $this->assertEquals(false, chksql($oDB, 'My custom error message'));
    }
}
