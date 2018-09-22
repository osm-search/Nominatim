<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/ClassTypes.php');

class ClassTypesTest extends \PHPUnit\Framework\TestCase
{
    public function testGetInfo()
    {
        // 1) Admin level set
        // city Dublin
        // https://nominatim.openstreetmap.org/details.php?osmtype=R&osmid=1109531
        $aPlace = array(
                   'admin_level' => 7,
                   'class' => 'boundary',
                   'type' => 'administrative',
                   'rank_address' => 14
        );

        $this->assertEquals('County', ClassTypes\getInfo($aPlace)['label']);
        $this->assertEquals('County', ClassTypes\getFallbackInfo($aPlace)['label']);
        $this->assertEquals('County', ClassTypes\getProperty($aPlace, 'label'));

        // 2) No admin level
        // Eiffel Tower
        // https://nominatim.openstreetmap.org/details.php?osmtype=W&osmid=5013364
        $aPlace = array(
                   'class' => 'tourism',
                   'type' => 'attraction',
                   'rank_address' => 29
        );
        $this->assertEquals('Attraction', ClassTypes\getInfo($aPlace)['label']);
        $this->assertEquals(array('simplelabel' => 'address29'), ClassTypes\getFallbackInfo($aPlace));
        $this->assertEquals('Attraction', ClassTypes\getProperty($aPlace, 'label'));

        // 3) Unknown type
        // La Maison du Toutou, Paris
        // https://nominatim.openstreetmap.org/details.php?osmtype=W&osmid=164011651
        $aPlace = array(
                   'class' => 'shop',
                   'type' => 'pet_grooming',
                   'rank_address' => 29
        );
        $this->assertEquals(false, ClassTypes\getInfo($aPlace));
        $this->assertEquals(array('simplelabel' => 'address29'), ClassTypes\getFallbackInfo($aPlace));
        $this->assertEquals(false, ClassTypes\getProperty($aPlace, 'label'));
        $this->assertEquals('mydefault', ClassTypes\getProperty($aPlace, 'label', 'mydefault'));
    }

    public function testGetClassTypesWithImportance()
    {
        $aClasses = ClassTypes\getListWithImportance();

        $this->assertGreaterThan(
            200,
            count($aClasses)
        );

        $this->assertEquals(
            array(
             'label' => 'Country',
             'frequency' => 0,
             'icon' => 'poi_boundary_administrative',
             'defzoom' => 6,
             'defdiameter' => 15,
             'importance' => 3
            ),
            $aClasses['place:country']
        );
    }


    public function testGetResultDiameter()
    {
        $aResult = array('class' => '', 'type' => '');
        $this->assertEquals(
            0.0001,
            ClassTypes\getProperty($aResult, 'defdiameter', 0.0001)
        );

        $aResult = array('class' => 'place', 'type' => 'country');
        $this->assertEquals(
            15,
            ClassTypes\getProperty($aResult, 'defdiameter', 0.0001)
        );

        $aResult = array('class' => 'boundary', 'type' => 'administrative', 'admin_level' => 6);
        $this->assertEquals(
            0.32,
            ClassTypes\getProperty($aResult, 'defdiameter', 0.0001)
        );
    }
}
