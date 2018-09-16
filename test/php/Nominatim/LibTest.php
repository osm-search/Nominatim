<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/lib.php');
require_once(CONST_BasePath.'/lib/ClassTypes.php');

class LibTest extends \PHPUnit\Framework\TestCase
{

    public function testAddQuotes()
    {
        // FIXME: not quoting existing quote signs is probably a bug
        $this->assertSame("'St. John's'", addQuotes("St. John's"));
        $this->assertSame("''", addQuotes(''));
    }


    public function testCreatePointsAroundCenter()
    {
        // you might say we're creating a circle
        $aPoints = createPointsAroundCenter(0, 0, 2);

        $this->assertEquals(
            101,
            count($aPoints)
        );
        $this->assertEquals(
            array(
             array('', 0, 2),
             array('', 0.12558103905863, 1.9960534568565),
             array('', 0.25066646712861, 1.984229402629)
            ),
            array_splice($aPoints, 0, 3)
        );
    }


    public function testGeometryText2Points()
    {
        $fRadius = 1;
        // invalid value
        $this->assertEquals(
            null,
            geometryText2Points('', $fRadius)
        );

        // POINT
        $aPoints = geometryText2Points('POINT(10 20)', $fRadius);
        $this->assertEquals(
            101,
            count($aPoints)
        );
        $this->assertEquals(
            array(
             array(10, 21),
             array(10.062790519529, 20.998026728428),
             array(10.125333233564, 20.992114701314)
            ),
            array_splice($aPoints, 0, 3)
        );

        // POLYGON
        $this->assertEquals(
            array(
             array('30', '10'),
             array('40', '40'),
             array('20', '40'),
             array('10', '20'),
             array('30', '10')
            ),
            geometryText2Points('POLYGON((30 10, 40 40, 20 40, 10 20, 30 10))', $fRadius)
        );

        // MULTIPOLYGON
        $this->assertEquals(
            array(
             array('30', '20'), // first polygon only
             array('45', '40'),
             array('10', '40'),
             array('30', '20'),
            ),
            geometryText2Points('MULTIPOLYGON(((30 20, 45 40, 10 40, 30 20)),((15 5, 40 10, 10 20, 5 10, 15 5)))', $fRadius)
        );
    }

    public function testParseLatLon()
    {
        // no coordinates expected
        $this->assertFalse(parseLatLon(''));
        $this->assertFalse(parseLatLon('abc'));
        $this->assertFalse(parseLatLon('12 34'));

        // coordinates expected
        $this->assertNotNull(parseLatLon('0.0 -0.0'));

        $aRes = parseLatLon(' abc 12.456 -78.90 def ');
        $this->assertEquals($aRes[1], 12.456);
        $this->assertEquals($aRes[2], -78.90);
        $this->assertEquals($aRes[0], ' 12.456 -78.90 ');

        $aRes = parseLatLon(' [12.456,-78.90] ');
        $this->assertEquals($aRes[1], 12.456);
        $this->assertEquals($aRes[2], -78.90);
        $this->assertEquals($aRes[0], ' [12.456,-78.90] ');

        $aRes = parseLatLon(' -12.456,-78.90 ');
        $this->assertEquals($aRes[1], -12.456);
        $this->assertEquals($aRes[2], -78.90);
        $this->assertEquals($aRes[0], ' -12.456,-78.90 ');

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
                     '40° 26′ 46.00″ N 79° 58′ 56.00″ W',
                     '40°26′46″N 79°58′56″W',
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
            $aRes = parseLatLon($sQuery);
            $this->assertEquals(40.446, $aRes[1], 'degrees decimal ' . $sQuery, 0.01);
            $this->assertEquals(-79.982, $aRes[2], 'degrees decimal ' . $sQuery, 0.01);
            $this->assertEquals($sQuery, $aRes[0]);
        }
    }

    private function closestHouseNumberEvenOddOther($startnumber, $endnumber, $fraction, $aExpected)
    {
        foreach (array('even', 'odd', 'other') as $itype) {
            $this->assertEquals(
                $aExpected[$itype],
                closestHouseNumber(array(
                                    'startnumber' => $startnumber,
                                    'endnumber' => $endnumber,
                                    'fraction' => $fraction,
                                    'interpolationtype' => $itype
                                   )),
                "$startnumber => $endnumber, $fraction, $itype"
            );
        }
    }

    public function testClosestHouseNumber()
    {
        $this->closestHouseNumberEvenOddOther(50, 100, 0.5, array('even' => 76, 'odd' => 75, 'other' => 75));
        // upper bound
        $this->closestHouseNumberEvenOddOther(50, 100, 1.5, array('even' => 100, 'odd' => 100, 'other' => 100));
        // lower bound
        $this->closestHouseNumberEvenOddOther(50, 100, -0.5, array('even' => 50, 'odd' => 50, 'other' => 50));
        // fraction 0
        $this->closestHouseNumberEvenOddOther(50, 100, 0, array('even' => 50, 'odd' => 51, 'other' => 50));
        // start == end
        $this->closestHouseNumberEvenOddOther(50, 50, 0.5, array('even' => 50, 'odd' => 50, 'other' => 50));
    }
}
