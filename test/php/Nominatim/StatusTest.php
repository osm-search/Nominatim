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

@define('CONST_TokenizerDir', dirname(__FILE__));

require_once(CONST_LibDir.'/DB.php');
require_once(CONST_LibDir.'/Status.php');


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
        $this->expectExceptionMessage('Database connection failed');
        $this->expectExceptionCode(700);

        $oDbStub = $this->getMockBuilder(Nominatim\DB::class)
                        ->setMethods(array('connect'))
                        ->getMock();

        $oDbStub->method('connect')
                ->will($this->returnCallback(function () {
                    throw new \Nominatim\DatabaseError('psql connection problem', 500, null, 'unknown database');
                }));


        $oStatus = new Status($oDbStub);
        $this->assertEquals('No database', $oStatus->status());
    }

    public function testOK()
    {
        $oDbStub = $this->getMockBuilder(Nominatim\DB::class)
                        ->setMethods(array('connect', 'getOne'))
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
        $oDbStub = $this->getMockBuilder(Nominatim\DB::class)
                        ->setMethods(array('getOne'))
                        ->getMock();

        $oDbStub->method('getOne')
                ->willReturn(1519430221);

        $oStatus = new Status($oDbStub);
        $this->assertEquals(1519430221, $oStatus->dataDate());
    }
}
