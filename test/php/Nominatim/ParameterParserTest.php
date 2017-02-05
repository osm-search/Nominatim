<?php

namespace Nominatim;

require_once(dirname(dirname(__FILE__)).'/../../build/settings/settings.php');
require_once(dirname(dirname(__FILE__)).'/bootstrap.php');

require_once(CONST_BasePath.'/lib/ParameterParser.php');

class ParameterParserTest extends \PHPUnit_Framework_TestCase
{


    protected function setUp()
    {
    }


    public function testGetBool()
    {
        $oParams = new ParameterParser(['bool1' => '1', 'bool2' => '0', 'bool3' => 'true', 'bool4' => 'false', 'bool5' => '']);

        $this->assertEquals(false, $oParams->getBool('non-exists'));
        $this->assertEquals(true, $oParams->getBool('non-exists', true));
        $this->assertEquals(true, $oParams->getBool('bool1'));
        $this->assertEquals(false, $oParams->getBool('bool2'));
        $this->assertEquals(true, $oParams->getBool('bool3'));
        $this->assertEquals(true, $oParams->getBool('bool4'));
        $this->assertEquals(false, $oParams->getBool('bool5'));
    }


    public function testGetInt()
    {
        $oParams = new ParameterParser(['int1' => '5', 'int2' => 'a', 'int3' => '-1', 'int4' => '', 'int5' => 0]);

        $this->assertEquals(false, $oParams->getInt('non-exists'));
        $this->assertEquals(999, $oParams->getInt('non-exists', 999));
        $this->assertEquals(5, $oParams->getInt('int1'));

        try {
            $this->assertEquals(false, $oParams->getInt('int2'));
        } catch (\Exception $e) {
            $this->assertEquals($e->getMessage(), "Integer number expected for parameter 'int2'");
        }
        $this->assertEquals(-1, $oParams->getInt('int3'));
        $this->assertEquals(false, $oParams->getInt('int4'));
        $this->assertEquals(false, $oParams->getInt('int5'));
    }


    public function testGetFloat()
    {
        $oParams = new ParameterParser(['float1' => '1.0', 'float2' => '-5', 'float3' => '-55.', 'float4' => 'a', 'float5' => '', 'float6' => 0]);

        $this->assertEquals(false, $oParams->getFloat('non-exists'));
        $this->assertEquals(999, $oParams->getFloat('non-exists', 999));
        $this->assertEquals(1, $oParams->getFloat('float1'));
        $this->assertEquals(-5, $oParams->getFloat('float2'));

        try {
            $this->assertEquals(false, $oParams->getFloat('float3'));
        } catch (\Exception $e) {
            $this->assertEquals($e->getMessage(), "Floating-point number expected for parameter 'float3'");
        }

        try {
            $this->assertEquals(false, $oParams->getFloat('float4'));
        } catch (\Exception $e) {
            $this->assertEquals($e->getMessage(), "Floating-point number expected for parameter 'float4'");
        }
        $this->assertEquals(false, $oParams->getFloat('float5'));
        $this->assertEquals(false, $oParams->getFloat('float6'));
    }



    public function testGetString()
    {
        $oParams = new ParameterParser(['str1' => 'abc', 'str2' => '', 'str3' => '0']);

        $this->assertEquals(false, $oParams->getString('non-exists'));
        $this->assertEquals('default', $oParams->getString('non-exists', 'default'));
        $this->assertEquals('abc', $oParams->getString('str1'));
        $this->assertEquals(false, $oParams->getStringList('str2'));
        $this->assertEquals(false, $oParams->getStringList('str3'));
    }



    public function testGetSet()
    {
        $oParams = new ParameterParser(['val1' => 'foo', 'val2' => 'FOO', 'val3' => '', 'val4' => 0]);

        $this->assertEquals(false, $oParams->getSet('non-exists', ['foo', 'bar']));
        $this->assertEquals('default', $oParams->getSet('non-exists', ['foo', 'bar'], 'default'));
        $this->assertEquals('foo', $oParams->getSet('val1', ['foo', 'bar']));

        try {
            $this->assertEquals(false, $oParams->getSet('val2', ['foo', 'bar']));
        } catch (\Exception $e) {
            $this->assertEquals($e->getMessage(), "Parameter 'val2' must be one of: foo, bar");
        }
        $this->assertEquals(false, $oParams->getSet('val3', ['foo', 'bar']));
        $this->assertEquals(false, $oParams->getSet('val4', ['foo', 'bar']));
    }


    public function testGetStringList()
    {
        $oParams = new ParameterParser(['list1' => ',a,b,c,,c,d', 'list2' => 'a', 'list3' => '', 'list4' => '0']);

        $this->assertEquals(false, $oParams->getStringList('non-exists'));
        $this->assertEquals(['a', 'b'], $oParams->getStringList('non-exists', ['a', 'b']));
        $this->assertEquals(['', 'a', 'b', 'c', '', 'c', 'd'], $oParams->getStringList('list1'));
        $this->assertEquals(['a'], $oParams->getStringList('list2'));
        $this->assertEquals(false, $oParams->getStringList('list3'));
        $this->assertEquals(false, $oParams->getStringList('list4'));
    }

    public function testGetPreferredLanguages()
    {
        $oParams = new ParameterParser(['accept-language' => '']);
        $this->assertEquals([
                             'brand' => 'brand',
                             'ref' => 'ref',
                             'type' => 'type',
                             'name' => 'name',
                             'name:default' => 'name:default',
                             'short_name' => 'short_name',
                             'short_name:default' => 'short_name:default',
                             'official_name' => 'official_name',
                             'official_name:default' => 'official_name:default',
                            ], $oParams->getPreferredLanguages('default'));

        $oParams = new ParameterParser(['accept-language' => 'de,en']);
        $this->assertEquals([
                             'brand' => 'brand',
                             'ref' => 'ref',
                             'type' => 'type',
                             'name' => 'name',
                             'name:de' => 'name:de',
                             'name:en' => 'name:en',
                             'short_name' => 'short_name',
                             'short_name:de' => 'short_name:de',
                             'short_name:en' => 'short_name:en',
                             'official_name' => 'official_name',
                             'official_name:de' => 'official_name:de',
                             'official_name:en' => 'official_name:en',
                            ], $oParams->getPreferredLanguages('default'));

        $oParams = new ParameterParser(['accept-language' => 'fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3']);
        $this->assertEquals([
                             'short_name:fr-ca' => 'short_name:fr-ca',
                             'name:fr-ca' => 'name:fr-ca',
                             'short_name:fr' => 'short_name:fr',
                             'name:fr' => 'name:fr',
                             'short_name:en-ca' => 'short_name:en-ca',
                             'name:en-ca' => 'name:en-ca',
                             'short_name:en' => 'short_name:en',
                             'name:en' => 'name:en',
                             'short_name' => 'short_name',
                             'name' => 'name',
                             'brand' => 'brand',
                             'official_name:fr-ca' => 'official_name:fr-ca',
                             'official_name:fr' => 'official_name:fr',
                             'official_name:en-ca' => 'official_name:en-ca',
                             'official_name:en' => 'official_name:en',
                             'official_name' => 'official_name',
                             'ref' => 'ref',
                             'type' => 'type',
                            ], $oParams->getPreferredLanguages('default'));
    }
}
