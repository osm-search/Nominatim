<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

namespace Nominatim;

require_once(CONST_LibDir.'/init-website.php');
require_once(CONST_LibDir.'/DatabaseError.php');

class DatabaseErrorTest extends \PHPUnit\Framework\TestCase
{

    public function testSqlMessage()
    {
        $oSqlStub = $this->getMockBuilder(PDOException::class)
                    ->setMethods(array('getMessage'))
                    ->getMock();

        $oSqlStub->method('getMessage')
                ->willReturn('Unknown table.');

        $oErr = new DatabaseError('Sql error', 123, null, $oSqlStub);
        $this->assertEquals('Sql error', $oErr->getMessage());
        $this->assertEquals(123, $oErr->getCode());
        $this->assertEquals('Unknown table.', $oErr->getSqlError());
    }

    public function testSqlObjectDump()
    {
        $oErr = new DatabaseError('Sql error', 123, null, array('one' => 'two'));
        $this->assertStringContainsString('two', $oErr->getSqlDebugDump());
    }
}
