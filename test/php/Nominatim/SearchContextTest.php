<?php

namespace Nominatim;

@define('CONST_BasePath', '../../');

require_once '../../lib/SearchContext.php';

class SearchContextTest extends \PHPUnit_Framework_TestCase
{
    private $oCtx;

    protected function setUp()
    {
        $this->oCtx = new SearchContext();
    }

    public function testHasNearPoint()
    {
        $this->assertFalse($this->oCtx->hasNearPoint());
        $this->oCtx->setNearPoint(0, 0);
        $this->assertTrue($this->oCtx->hasNearPoint());
    }

    public function testNearRadius()
    {
        $this->oCtx->setNearPoint(1, 1);
        $this->assertEquals(0.1, $this->oCtx->nearRadius());
        $this->oCtx->setNearPoint(1, 1, 0.338);
        $this->assertEquals(0.338, $this->oCtx->nearRadius());
    }

    public function testWithinSQL()
    {
        $this->oCtx->setNearPoint(0.1, 23, 1);

        $this->assertEquals(
            'ST_DWithin(foo, ST_SetSRID(ST_Point(23,0.1),4326), 1.000000)',
            $this->oCtx->withinSQL('foo')
        );
    }

    public function testDistanceSQL()
    {
        $this->oCtx->setNearPoint(0.1, 23, 1);

        $this->assertEquals(
            'ST_Distance(ST_SetSRID(ST_Point(23,0.1),4326), foo)',
            $this->oCtx->distanceSQL('foo')
        );
    }
}
