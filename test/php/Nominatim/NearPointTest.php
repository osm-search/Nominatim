<?php

namespace Nominatim;

require '../../lib/NearPoint.php';

class NearPointTest extends \PHPUnit_Framework_TestCase
{
    protected function setUp()
    {
    }

    public function testExtractFromQuery()
    {
        // no coordinates expected
        $this->assertFalse(NearPoint::extractFromQuery(''));
        $this->assertFalse(NearPoint::extractFromQuery('abc'));
        $this->assertFalse(NearPoint::extractFromQuery('12 34'));
        $this->assertFalse(NearPoint::extractFromQuery('200.1 89.9')); // because latitude > 180

        // coordinates expected
        $this->assertNotNull(NearPoint::extractFromQuery('0.0 -0.0'));

        $aRes = NearPoint::extractFromQuery(' abc 12.456 -78.90 def ');
        $this->assertEquals($aRes['pt']->lat(), 12.456);
        $this->assertEquals($aRes['pt']->lon(), -78.90);
        $this->assertEquals($aRes['pt']->radius(), 0.1);
        $this->assertEquals($aRes['query'], 'abc   def');

        $aRes = NearPoint::extractFromQuery(' [12.456,-78.90] ');
        $this->assertEquals($aRes['pt']->lat(), 12.456);
        $this->assertEquals($aRes['pt']->lon(), -78.90);
        $this->assertEquals($aRes['pt']->radius(), 0.1);
        $this->assertEquals($aRes['query'], '');

        // http://en.wikipedia.org/wiki/Geographic_coordinate_conversion
        // these all represent the same location
        $aQueries = array(
                     '40 26.767 N 79 58.933 W',
                     '40° 26.767′ N 79° 58.933′ W',
                     "40° 26.767' N 79° 58.933' W",
                     'N 40 26.767, W 79 58.933',
                     'N 40°26.767′, W 79°58.933′',
                     "N 40°26.767', W 79°58.933'",
 
                     '40 26 46 N 79 58 56 W',
                     '40° 26′ 46″ N 79° 58′ 56″ W',
                     'N 40 26 46 W 79 58 56',
                     'N 40° 26′ 46″, W 79° 58′ 56″',
                     'N 40° 26\' 46", W 79° 58\' 56"',
 
                     '40.446 -79.982',
                     '40.446,-79.982',
                     '40.446° N 79.982° W',
                     'N 40.446° W 79.982°',
 
                     '[40.446 -79.982]',
                     '       40.446  ,   -79.982     ',
                    );


        foreach ($aQueries as $sQuery) {
            $aRes = NearPoint::extractFromQuery($sQuery);
            $this->assertEquals(40.446, $aRes['pt']->lat(), 'degrees decimal ' . $sQuery, 0.01);
            $this->assertEquals(-79.982, $aRes['pt']->lon(), 'degrees decimal ' . $sQuery, 0.01);
        }
    }

    public function testWithinSQL()
    {
        $np = new NearPoint(0.1, 23, 1);

        $this->assertEquals(
            'ST_DWithin(foo, ST_SetSRID(ST_Point(23,0.1),4326), 1.000000)',
            $np->withinSQL('foo')
        );
    }

    public function testDistanceSQL()
    {
        $np = new NearPoint(0.1, 23, 1);

        $this->assertEquals(
            'ST_Distance(ST_SetSRID(ST_Point(23,0.1),4326), foo)',
            $np->distanceSQL('foo')
        );
    }
}
