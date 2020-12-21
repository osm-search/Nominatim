<?php

namespace Nominatim;

require_once(CONST_LibDir.'/SearchContext.php');

class SearchContextTest extends \PHPUnit\Framework\TestCase
{
    private $oCtx;


    protected function setUp(): void
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

    public function testSetViewboxFromBox()
    {
        $viewbox = array(30, 20, 40, 50);
        $this->oCtx->setViewboxFromBox($viewbox, true);
        $this->assertEquals(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(30.000000,20.000000),ST_Point(40.000000,50.000000)),4326)',
            $this->oCtx->sqlViewboxSmall
        );
        // height: 10
        // width: 30
        $this->assertEquals(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(50.000000,80.000000),ST_Point(20.000000,-10.000000)),4326)',
            $this->oCtx->sqlViewboxLarge
        );


        $viewbox = array(-1.5, -2, 1.5, 2);
        $this->oCtx->setViewboxFromBox($viewbox, true);
        $this->assertEquals(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(-1.500000,-2.000000),ST_Point(1.500000,2.000000)),4326)',
            $this->oCtx->sqlViewboxSmall
        );
        // height: 3
        // width: 4
        $this->assertEquals(
            'ST_SetSRID(ST_MakeBox2D(ST_Point(4.500000,6.000000),ST_Point(-4.500000,-6.000000)),4326)',
            $this->oCtx->sqlViewboxLarge
        );
    }
}
