<?php

namespace Nominatim;

require_once(dirname(dirname(__FILE__)).'/../../build/settings/settings.php');
require_once(dirname(dirname(__FILE__)).'/bootstrap.php');

require_once(CONST_BasePath.'/lib/Geocode.php');
require_once(CONST_BasePath.'/lib/ParameterParser.php');

class GeocodeTest extends \PHPUnit_Framework_TestCase
{


    protected function setUp()
    {
        $this->oDB =& getDB();
    }


    public function testViewbox()
    {
        $oGeocode = new Geocode($oDB);

        $this->assertNull($oGeocode->getViewBoxString());

        $oGeocode->setViewbox([-10, 20, 30, 40]);
        $this->assertEquals('-10,40,30,20', $oGeocode->getViewBoxString());

        // string as input is supported
        $oGeocode->setViewbox(['1', '1', '2', '2']);
        $this->assertEquals('1,2,2,1', $oGeocode->getViewBoxString());

        // null values are mapped to 0
        $oGeocode->setViewbox([1, 1, null, null]);
        $this->assertEquals('1,0,0,1', $oGeocode->getViewBoxString());

        // values are cut to min and max limits
        $oGeocode->setViewbox([-190, -90, 190, 90]);
        $this->assertEquals('-180,90,180,-90', $oGeocode->getViewBoxString());


        // boxes with width or height of 0 cause exceptions, the
        // ViewBoxString still gets set
        try {
            $oGeocode->setViewbox([10, 10, 10, 10]);
            $this->assertEquals('10,10,10,10', $oGeocode->getViewBoxString());
        } catch (\Exception $e) {
            $this->assertEquals($e->getMessage(), "Bad parameter 'viewbox'. Not a box.");
        }
    }
}
