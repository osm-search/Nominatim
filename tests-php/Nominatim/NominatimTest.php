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

}
