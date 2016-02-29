<?php

namespace Nominatim;
require '../lib/lib.php';


class NominatimTest extends \PHPUnit_Framework_TestCase
{

	protected function setUp()
	{
	}


	public function test_addQuotes()
	{
		// FIXME: not quoting existing quote signs is probably a bug
		$this->assertSame("'St. John's'", addQuotes("St. John's"));
		$this->assertSame("''", addQuotes(''));
	}

	public function test_looksLikeLatLonPair()
	{
		// no coordinates expected
		$this->assertNull(looksLikeLatLonPair(''));
		$this->assertNull(looksLikeLatLonPair('abc'));
		$this->assertNull(looksLikeLatLonPair('12 34'));
		$this->assertNull(looksLikeLatLonPair('200.1 89.9')); // because latitude > 180

		// coordinates expected
		$this->assertNotNull(looksLikeLatLonPair('0.0 -0.0'));

		$this->assertEquals(
				array( 'lat' => 12.456, 'lon' => -78.90, 'query' => 'abc   def'),
				looksLikeLatLonPair(' abc 12.456 -78.90 def ')
			);

		$this->assertEquals(
				array( 'lat' => 12.456, 'lon' => -78.90, 'query' => ''),
				looksLikeLatLonPair(' [12.456,-78.90] ')
			);

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


		foreach($aQueries as $sQuery){
			$aRes = looksLikeLatLonPair($sQuery);
			$this->assertEquals( 40.446, $aRes['lat'], 'degrees decimal ' . $sQuery, 0.01);
			$this->assertEquals(-79.982, $aRes['lon'], 'degrees decimal ' . $sQuery, 0.01);
		}

	}



	public function test_getWordSets()
	{

		// given an array of arrays like
		// array( array('a','b'), array('c','d') )
		// returns a summary as string: '(a|b),(c|d)'
		function serialize_sets($aSets)
		{	
			$aParts = array();
			foreach($aSets as $aSet){
				$aParts[] = '(' . join('|', $aSet) . ')';
			}
			return join(',', $aParts);
		}

		$this->assertEquals(
			array(array('')),
			getWordSets(array(),0)
		);

		$this->assertEquals(
			'(a)',
			serialize_sets( getWordSets(array("a"),0) )
		);

		$this->assertEquals(
			'(a b),(a|b)',
			serialize_sets( getWordSets(array('a','b'),0) )
		);

		$this->assertEquals(
			'(a b c),(a|b c),(a|b|c),(a b|c)',
			serialize_sets( getWordSets(array('a','b','c'),0) )
		);

		$this->assertEquals(
			'(a b c d),(a|b c d),(a|b|c d),(a|b|c|d),(a|b c|d),(a b|c d),(a b|c|d),(a b c|d)',
			serialize_sets( getWordSets(array('a','b','c','d'),0) )
		);


		// Inverse
		$this->assertEquals(
			'(a b c),(c|a b),(c|b|a),(b c|a)',
			serialize_sets( getInverseWordSets(array('a','b','c'),0) )
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
			count( getWordSets(array_fill( 0, 4, 'a'),0) )
		);


		$this->assertEquals(
			65536,
			count( getWordSets(array_fill( 0, 18, 'a'),0) )
		);

	}




	public function test_geometryText2Points()
	{
		$fRadius = 1;

		// invalid value
		$this->assertEquals(
			NULL,
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
  			['', 10, 21],
  			['', 10.062790519529, 20.998026728428],
				['', 10.125333233564, 20.992114701314]
			),
			array_splice($aPoints, 0,3)
		);

		// POLYGON
		$this->assertEquals(
			array(
				['30 10', '30', '10'],
				['40 40', '40', '40'],
				['20 40', '20', '40'],
				['10 20', '10', '20'],
				['30 10', '30', '10']
			),
			geometryText2Points('POLYGON((30 10, 40 40, 20 40, 10 20, 30 10))', $fRadius)
		);

		// MULTIPOLYGON
		// only the first polygon is used
		$this->assertEquals(
			array(
				['30 20', '30', '20'],
				['45 40', '45', '40'],
				['10 40', '10', '40'],
				['30 20', '30', '20'],

				// ['15 5' , '15', '5' ],
				// ['45 10', '45', '10'],
				// ['10 20', '10', '20'],
				// ['5 10' , '5' , '10'],
				// ['15 5' , '15', '5' ]
			),
			geometryText2Points('MULTIPOLYGON(((30 20, 45 40, 10 40, 30 20)),((15 5, 40 10, 10 20, 5 10, 15 5)))', $fRadius)
		);


	}


}
