<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/init-website.php');
require_once(CONST_BasePath.'/lib/AddressDetails.php');


class AddressDetailsTest extends \PHPUnit\Framework\TestCase
{

    protected function setUp()
    {
        // How the fixture got created
        //
        // 1) search for '10 downing street'
        // https://nominatim.openstreetmap.org/details.php?osmtype=R&osmid=1879842
        //
        // 2) find place_id in the local database
        // SELECT place_id, name FROM placex WHERE osm_type='R' AND osm_id=1879842;
        //
        // 3) set postgresql to non-align output, e.g. psql -A or \a in the CLI
        //
        // 4) query
        // SELECT row_to_json(row,true) FROM (
        //   SELECT *, get_name_by_language(name, ARRAY['name:en']) as localname
        //   FROM get_addressdata(194663412,10)
        //   ORDER BY rank_address DESC, isaddress DESC
        // ) AS row;
        //
        // 5) copy&paste into file. Add commas between records
        //
        $json = file_get_contents(CONST_BasePath.'/test/php/fixtures/address_details_10_downing_street.json');
        $data = json_decode($json, true);

        $this->oDbStub = $this->getMockBuilder(\DB::class)
                              ->setMethods(array('getAll'))
                              ->getMock();
        $this->oDbStub->method('getAll')
                      ->willReturn($data);
    }

    public function testGetLocaleAddress()
    {
        $oAD = new AddressDetails($this->oDbStub, 194663412, 10, 'en');
        $expected = join(', ', array(
            '10 Downing Street',
            '10',
            'Downing Street',
            'St. James\'s',
            'Covent Garden',
            'Westminster',
            'London',
            'Greater London',
            'England',
            'SW1A 2AA',
            'United Kingdom'
        ));
        $this->assertEquals($expected, $oAD->getLocaleAddress());
    }

    public function testGetAddressDetails()
    {
        $oAD = new AddressDetails($this->oDbStub, 194663412, 10, 'en');
        $this->assertEquals(18, count($oAD->getAddressDetails(true)));
        $this->assertEquals(12, count($oAD->getAddressDetails(false)));
    }

    public function testGetAddressNames()
    {
        $oAD = new AddressDetails($this->oDbStub, 194663412, 10, 'en');
        $expected = array(
                     'attraction' => '10 Downing Street',
                     'house_number' => '10',
                     'road' => 'Downing Street',
                     'neighbourhood' => 'St. James\'s',
                     'suburb' => 'Covent Garden',
                     'city' => 'London',
                     'state_district' => 'Greater London',
                     'state' => 'England',
                     'postcode' => 'SW1A 2AA',
                     'country' => 'United Kingdom',
                     'country_code' => 'gb'
        );

        $this->assertEquals($expected, $oAD->getAddressNames());
    }

    public function testGetAdminLevels()
    {
        $oAD = new AddressDetails($this->oDbStub, 194663412, 10, 'en');
        $expected = array(
                     'level8' => 'Westminster',
                     'level6' => 'London',
                     'level5' => 'Greater London',
                     'level4' => 'England',
                     'level2' => 'United Kingdom'
        );
        $this->assertEquals($expected, $oAD->getAdminLevels());
    }

    public function testDebugInfo()
    {
        $oAD = new AddressDetails($this->oDbStub, 194663412, 10, 'en');
        $this->assertTrue(is_array($oAD->debugInfo()));
        $this->assertEquals(18, count($oAD->debugInfo()));
    }
}
