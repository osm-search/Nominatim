<?php

namespace Nominatim;

require_once '../../lib/lib.php';

class NominatimTest extends \PHPUnit_Framework_TestCase
{


    protected function setUp()
    {
    }


    public function testGetClassTypesWithImportance()
    {
        $aClasses = getClassTypesWithImportance();

        $this->assertGreaterThan(
            200,
            count($aClasses)
        );

        $this->assertEquals(
            array(
             'label' => "Country",
             'frequency' => 0,
             'icon' => "poi_boundary_administrative",
             'defzoom' => 6,
             'defdiameter' => 15,
             'importance' => 3
            ),
            $aClasses['place:country']
        );
    }


    public function testGetResultDiameter()
    {
        $aResult = array();
        $this->assertEquals(
            0.0001,
            getResultDiameter($aResult)
        );

        $aResult = array('class' => 'place', 'type' => 'country');
        $this->assertEquals(
            15,
            getResultDiameter($aResult)
        );

        $aResult = array('class' => 'boundary', 'type' => 'administrative', 'admin_level' => 6);
        $this->assertEquals(
            0.32,
            getResultDiameter($aResult)
        );
    }


    public function testAddQuotes()
    {
        // FIXME: not quoting existing quote signs is probably a bug
        $this->assertSame("'St. John's'", addQuotes("St. John's"));
        $this->assertSame("''", addQuotes(''));
    }


    public function testGetWordSets()
    {
        // given an array of arrays like
        // array( array('a','b'), array('c','d') )
        // returns a summary as string: '(a|b),(c|d)'


        function serializeSets($aSets)
        {
            $aParts = array();
            foreach ($aSets as $aSet) {
                $aParts[] = '(' . join('|', $aSet) . ')';
            }
            return join(',', $aParts);
        }

        $this->assertEquals(
            array(array('')),
            getWordSets(array(), 0)
        );

        $this->assertEquals(
            '(a)',
            serializeSets(getWordSets(array("a"), 0))
        );

        $this->assertEquals(
            '(a b),(a|b)',
            serializeSets(getWordSets(array('a', 'b'), 0))
        );

        $this->assertEquals(
            '(a b c),(a|b c),(a|b|c),(a b|c)',
            serializeSets(getWordSets(array('a', 'b', 'c'), 0))
        );

        $this->assertEquals(
            '(a b c d),(a|b c d),(a|b|c d),(a|b|c|d),(a|b c|d),(a b|c d),(a b|c|d),(a b c|d)',
            serializeSets(getWordSets(array('a', 'b', 'c', 'd'), 0))
        );


        // Inverse
        $this->assertEquals(
            '(a b c),(c|a b),(c|b|a),(b c|a)',
            serializeSets(getInverseWordSets(array('a', 'b', 'c'), 0))
        );


        // make sure we don't create too many sets
        // 4 words => 8 sets
        // 10 words => 511 sets
        // 15 words => 12911 sets
        // 18 words => 65536 sets
        // 20 words => 169766 sets
        // 22 words => 401930 sets
        // 28 words => 3505699 sets (needs more than 4GB via 'phpunit -d memory_limit=' to run)
        $this->assertEquals(
            8,
            count(getWordSets(array_fill(0, 4, 'a'), 0))
        );


        $this->assertEquals(
            41226,
            count(getWordSets(array_fill(0, 18, 'a'), 0))
        );
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
             ['', 0, 2],
             ['', 0.12558103905863, 1.9960534568565],
             ['', 0.25066646712861, 1.984229402629]
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
             [10, 21],
             [10.062790519529, 20.998026728428],
             [10.125333233564, 20.992114701314]
            ),
            array_splice($aPoints, 0, 3)
        );

        // POLYGON
        $this->assertEquals(
            array(
             ['30', '10'],
             ['40', '40'],
             ['20', '40'],
             ['10', '20'],
             ['30', '10']
            ),
            geometryText2Points('POLYGON((30 10, 40 40, 20 40, 10 20, 30 10))', $fRadius)
        );

        // MULTIPOLYGON
        $this->assertEquals(
            array(
             ['30', '20'], // first polygon only
             ['45', '40'],
             ['10', '40'],
             ['30', '20'],
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
}
