<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/ParameterParser.php');


function userError($sError)
{
    throw new \Exception($sError);
}

class ParameterParserTest extends \PHPUnit\Framework\TestCase
{


    public function testGetBool()
    {
        $oParams = new ParameterParser(array(
                                        'bool1' => '1',
                                        'bool2' => '0',
                                        'bool3' => 'true',
                                        'bool4' => 'false',
                                        'bool5' => ''
                                       ));

        $this->assertSame(false, $oParams->getBool('non-exists'));
        $this->assertSame(true, $oParams->getBool('non-exists', true));
        $this->assertSame(true, $oParams->getBool('bool1'));
        $this->assertSame(false, $oParams->getBool('bool2'));
        $this->assertSame(true, $oParams->getBool('bool3'));
        $this->assertSame(true, $oParams->getBool('bool4'));
        $this->assertSame(false, $oParams->getBool('bool5'));
    }


    public function testGetInt()
    {
        $oParams = new ParameterParser(array(
                                        'int1' => '5',
                                        'int2' => '-1',
                                        'int3' => 0
                                       ));

        $this->assertSame(false, $oParams->getInt('non-exists'));
        $this->assertSame(999, $oParams->getInt('non-exists', 999));
        $this->assertSame(5, $oParams->getInt('int1'));

        $this->assertSame(-1, $oParams->getInt('int2'));
        $this->assertSame(0, $oParams->getInt('int3'));
    }


    public function testGetIntWithNonNumber()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage("Integer number expected for parameter 'int4'");

        (new ParameterParser(array('int4' => 'a')))->getInt('int4');
    }


    public function testGetIntWithEmpytString()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage("Integer number expected for parameter 'int5'");

        (new ParameterParser(array('int5' => '')))->getInt('int5');
    }


    public function testGetFloat()
    {

        $oParams = new ParameterParser(array(
                                        'float1' => '1.0',
                                        'float2' => '-5',
                                        'float3' => 0
                                       ));

        $this->assertSame(false, $oParams->getFloat('non-exists'));
        $this->assertSame(999, $oParams->getFloat('non-exists', 999));
        $this->assertSame(1.0, $oParams->getFloat('float1'));
        $this->assertSame(-5.0, $oParams->getFloat('float2'));
        $this->assertSame(0.0, $oParams->getFloat('float3'));
    }

    public function testGetFloatWithEmptyString()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage("Floating-point number expected for parameter 'float4'");

        (new ParameterParser(array('float4' => '')))->getFloat('float4');
    }

    public function testGetFloatWithTextString()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage("Floating-point number expected for parameter 'float5'");

        (new ParameterParser(array('float5' => 'a')))->getFloat('float5');
    }


    public function testGetFloatWithInvalidNumber()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage("Floating-point number expected for parameter 'float6'");

        (new ParameterParser(array('float6' => '-55.')))->getFloat('float6');
    }


    public function testGetString()
    {
        $oParams = new ParameterParser(array(
                                        'str1' => 'abc',
                                        'str2' => '',
                                        'str3' => '0'
                                       ));

        $this->assertSame(false, $oParams->getString('non-exists'));
        $this->assertSame('default', $oParams->getString('non-exists', 'default'));
        $this->assertSame('abc', $oParams->getString('str1'));
        $this->assertSame(false, $oParams->getStringList('str2'));
        $this->assertSame(false, $oParams->getStringList('str3')); // sadly PHP magic treats 0 as false when returned
    }


    public function testGetSet()
    {
        $oParams = new ParameterParser(array(
                                        'val1' => 'foo',
                                        'val2' => '',
                                        'val3' => 0
                                       ));

        $this->assertSame(false, $oParams->getSet('non-exists', array('foo', 'bar')));
        $this->assertSame('default', $oParams->getSet('non-exists', array('foo', 'bar'), 'default'));
        $this->assertSame('foo', $oParams->getSet('val1', array('foo', 'bar')));

        $this->assertSame(false, $oParams->getSet('val2', array('foo', 'bar')));
        $this->assertSame(0, $oParams->getSet('val3', array('foo', 'bar')));
    }


    public function testGetSetWithValueNotInSet()
    {
        $this->expectException(\Exception::class);
        $this->expectExceptionMessage("Parameter 'val4' must be one of: foo, bar");

        (new ParameterParser(array('val4' => 'faz')))->getSet('val4', array('foo', 'bar'));
    }


    public function testGetStringList()
    {
        $oParams = new ParameterParser(array(
                                        'list1' => ',a,b,c,,c,d',
                                        'list2' => 'a',
                                        'list3' => '',
                                        'list4' => '0'
                                       ));

        $this->assertSame(false, $oParams->getStringList('non-exists'));
        $this->assertSame(array('a', 'b'), $oParams->getStringList('non-exists', array('a', 'b')));
        $this->assertSame(array('a', 'b', 'c', 'c', 'd'), $oParams->getStringList('list1'));
        $this->assertSame(array('a'), $oParams->getStringList('list2'));
        $this->assertSame(false, $oParams->getStringList('list3'));
        $this->assertSame(false, $oParams->getStringList('list4'));
    }


    public function testGetPreferredLanguages()
    {
        $oParams = new ParameterParser(array('accept-language' => ''));
        $this->assertSame(array(
                           'short_name:default' => 'short_name:default',
                           'name:default' => 'name:default',
                           'short_name' => 'short_name',
                           'name' => 'name',
                           'brand' => 'brand',
                           'official_name:default' => 'official_name:default',
                           'official_name' => 'official_name',
                           'ref' => 'ref',
                           'type' => 'type'
                          ), $oParams->getPreferredLanguages('default'));

        $oParams = new ParameterParser(array('accept-language' => 'de,en'));
        $this->assertSame(array(
                           'short_name:de' => 'short_name:de',
                           'name:de' => 'name:de',
                           'short_name:en' => 'short_name:en',
                           'name:en' => 'name:en',
                           'short_name' => 'short_name',
                           'name' => 'name',
                           'brand' => 'brand',
                           'official_name:de' => 'official_name:de',
                           'official_name:en' => 'official_name:en',
                           'official_name' => 'official_name',
                           'ref' => 'ref',
                           'type' => 'type'
                          ), $oParams->getPreferredLanguages('default'));

        $oParams = new ParameterParser(array('accept-language' => 'fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3'));
        $this->assertSame(array(
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
                          ), $oParams->getPreferredLanguages('default'));

        $oParams = new ParameterParser(array('accept-language' => 'ja_rm,zh_pinyin'));
        $this->assertSame(array(
                           'short_name:ja_rm' => 'short_name:ja_rm',
                           'name:ja_rm' => 'name:ja_rm',
                           'short_name:zh_pinyin' => 'short_name:zh_pinyin',
                           'name:zh_pinyin' => 'name:zh_pinyin',
                           'short_name:ja' => 'short_name:ja',
                           'name:ja' => 'name:ja',
                           'short_name:zh' => 'short_name:zh',
                           'name:zh' => 'name:zh',
                           'short_name' => 'short_name',
                           'name' => 'name',
                           'brand' => 'brand',
                           'official_name:ja_rm' => 'official_name:ja_rm',
                           'official_name:zh_pinyin' => 'official_name:zh_pinyin',
                           'official_name:ja' => 'official_name:ja',
                           'official_name:zh' => 'official_name:zh',
                           'official_name' => 'official_name',
                           'ref' => 'ref',
                           'type' => 'type',
                          ), $oParams->getPreferredLanguages('default'));
    }
}
