<?php

namespace Nominatim;

require_once(CONST_LibDir.'/output.php');

class OutputTest extends \PHPUnit\Framework\TestCase
{
    public function testDetailsPermaLinkNode()
    {
        $aFeature = array('osm_type' => 'N', 'osm_id'=> 38274, 'class' => 'place');
        $this->assertSame(
            detailsPermaLink($aFeature),
            '<a href="details.php?osmtype=N&osmid=38274&class=place">node 38274</a>'
        );
    }

    public function testDetailsPermaLinkWay()
    {
        $aFeature = array('osm_type' => 'W', 'osm_id'=> 65, 'class' => 'highway');
        $this->assertSame(
            detailsPermaLink($aFeature),
            '<a href="details.php?osmtype=W&osmid=65&class=highway">way 65</a>'
        );
    }

    public function testDetailsPermaLinkRelation()
    {
        $aFeature = array('osm_type' => 'R', 'osm_id'=> 9908, 'class' => 'waterway');
        $this->assertSame(
            detailsPermaLink($aFeature),
            '<a href="details.php?osmtype=R&osmid=9908&class=waterway">relation 9908</a>'
        );
    }

    public function testDetailsPermaLinkTiger()
    {
        $aFeature = array('osm_type' => 'T', 'osm_id'=> 2, 'place_id' => 334);
        $this->assertSame(
            detailsPermaLink($aFeature, 'foo'),
            '<a href="details.php?place_id=334">foo</a>'
        );
    }

    public function testDetailsPermaLinkInterpolation()
    {
        $aFeature = array('osm_type' => 'I', 'osm_id'=> 400, 'place_id' => 3);
        $this->assertSame(
            detailsPermaLink($aFeature, 'foo'),
            '<a href="details.php?place_id=3">foo</a>'
        );
    }

    public function testDetailsPermaLinkWithExtraPropertiesNode()
    {
        $aFeature = array('osm_type' => 'N', 'osm_id'=> 2, 'class' => 'amenity');
        $this->assertSame(
            detailsPermaLink($aFeature, 'something', 'class="xtype"'),
            '<a class="xtype" href="details.php?osmtype=N&osmid=2&class=amenity">something</a>'
        );
    }

    public function testDetailsPermaLinkWithExtraPropertiesTiger()
    {
        $aFeature = array('osm_type' => 'T', 'osm_id'=> 5, 'place_id' => 46);
        $this->assertSame(
            detailsPermaLink($aFeature, 'something', 'class="xtype"'),
            '<a class="xtype" href="details.php?place_id=46">something</a>'
        );
    }
}
