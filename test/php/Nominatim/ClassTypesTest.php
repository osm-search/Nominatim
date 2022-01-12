<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

namespace Nominatim;

require_once(CONST_LibDir.'/ClassTypes.php');

class ClassTypesTest extends \PHPUnit\Framework\TestCase
{
    public function testGetLabelTag()
    {
        $aPlace = array('class' => 'boundary', 'type' => 'administrative',
                   'rank_address' => '4', 'place_type' => 'city');
        $this->assertEquals('city', ClassTypes\getLabelTag($aPlace));

        $aPlace = array('class' => 'boundary', 'type' => 'administrative',
                   'rank_address' => '10');
        $this->assertEquals('state_district', ClassTypes\getLabelTag($aPlace));

        $aPlace = array('class' => 'boundary', 'type' => 'administrative');
        $this->assertEquals('administrative', ClassTypes\getLabelTag($aPlace));

        $aPlace = array('class' => 'place', 'type' => 'hamlet', 'rank_address' => '20');
        $this->assertEquals('hamlet', ClassTypes\getLabelTag($aPlace));

        $aPlace = array('class' => 'highway', 'type' => 'residential',
                   'rank_address' => '26');
        $this->assertEquals('road', ClassTypes\getLabelTag($aPlace));

        $aPlace = array('class' => 'place', 'type' => 'house_number',
                   'rank_address' => '30');
        $this->assertEquals('house_number', ClassTypes\getLabelTag($aPlace));

        $aPlace = array('class' => 'amenity', 'type' => 'prison',
                   'rank_address' => '30');
        $this->assertEquals('amenity', ClassTypes\getLabelTag($aPlace));
    }

    public function testGetLabel()
    {
        $aPlace = array('class' => 'boundary', 'type' => 'administrative',
                   'rank_address' => '4', 'place_type' => 'city');
        $this->assertEquals('City', ClassTypes\getLabel($aPlace));

        $aPlace = array('class' => 'boundary', 'type' => 'administrative',
                   'rank_address' => '10');
        $this->assertEquals('State District', ClassTypes\getLabel($aPlace));

        $aPlace = array('class' => 'boundary', 'type' => 'administrative');
        $this->assertEquals('Administrative', ClassTypes\getLabel($aPlace));

        $aPlace = array('class' => 'amenity', 'type' => 'prison');
        $this->assertEquals('Prison', ClassTypes\getLabel($aPlace));

        $aPlace = array('class' => 'amenity', 'type' => 'foobar');
        $this->assertNull(ClassTypes\getLabel($aPlace));
    }

    public function testGetBoundaryLabel()
    {
        $this->assertEquals('City', ClassTypes\getBoundaryLabel(8, null));
        $this->assertEquals('Administrative', ClassTypes\getBoundaryLabel(18, null));
        $this->assertEquals('None', ClassTypes\getBoundaryLabel(18, null, 'None'));
        $this->assertEquals('State', ClassTypes\getBoundaryLabel(4, 'de', 'None'));
        $this->assertEquals('County', ClassTypes\getBoundaryLabel(4, 'se', 'None'));
        $this->assertEquals('Municipality', ClassTypes\getBoundaryLabel(7, 'se', 'None'));
    }

    public function testGetDefRadius()
    {
        $aResult = array('class' => '', 'type' => '');
        $this->assertEquals(0.00005, ClassTypes\getDefRadius($aResult));

        $aResult = array('class' => 'place', 'type' => 'country');
        $this->assertEquals(7, ClassTypes\getDefRadius($aResult));
    }

    public function testGetIcon()
    {
        $aResult = array('class' => '', 'type' => '');
        $this->assertNull(ClassTypes\getIcon($aResult));

        $aResult = array('class' => 'place', 'type' => 'airport');
        $this->assertEquals('transport_airport2', ClassTypes\getIcon($aResult));
    }

    public function testGetImportance()
    {
        $aResult = array('class' => '', 'type' => '');
        $this->assertNull(ClassTypes\getImportance($aResult));

        $aResult = array('class' => 'place', 'type' => 'airport');
        $this->assertGreaterThan(0, ClassTypes\getImportance($aResult));
    }
}
