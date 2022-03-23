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

require_once(CONST_LibDir.'/ParameterParser.php');


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
                           'name:default' => 'name:default',
                           '_place_name:default' => '_place_name:default',
                           'name' => 'name',
                           '_place_name' => '_place_name'
                          ), array_slice($oParams->getPreferredLanguages('default'), 0, 4));

        $oParams = new ParameterParser(array('accept-language' => 'de,en'));
        $this->assertSame(array(
                           'name:de' => 'name:de',
                           '_place_name:de' => '_place_name:de',
                           'name:en' => 'name:en',
                           '_place_name:en' => '_place_name:en',
                           'name' => 'name',
                           '_place_name' => '_place_name'
                          ), array_slice($oParams->getPreferredLanguages('default'), 0, 6));

        $oParams = new ParameterParser(array('accept-language' => 'fr-ca,fr;q=0.8,en-ca;q=0.5,en;q=0.3'));
        $this->assertSame(array(
                           'name:fr-ca' => 'name:fr-ca',
                           '_place_name:fr-ca' => '_place_name:fr-ca',
                           'name:fr' => 'name:fr',
                           '_place_name:fr' => '_place_name:fr',
                           'name:en-ca' => 'name:en-ca',
                           '_place_name:en-ca' => '_place_name:en-ca',
                           'name:en' => 'name:en',
                           '_place_name:en' => '_place_name:en',
                           'name' => 'name',
                           '_place_name' => '_place_name'
                          ), array_slice($oParams->getPreferredLanguages('default'), 0, 10));

        $oParams = new ParameterParser(array('accept-language' => 'ja_rm,zh_pinyin'));
        $this->assertSame(array(
                           'name:ja_rm' => 'name:ja_rm',
                           '_place_name:ja_rm' => '_place_name:ja_rm',
                           'name:zh_pinyin' => 'name:zh_pinyin',
                           '_place_name:zh_pinyin' => '_place_name:zh_pinyin',
                           'name:ja' => 'name:ja',
                           '_place_name:ja' => '_place_name:ja',
                           'name:zh' => 'name:zh',
                           '_place_name:zh' => '_place_name:zh',
                           'name' => 'name',
                           '_place_name' => '_place_name'
                          ), array_slice($oParams->getPreferredLanguages('default'), 0, 10));
    }

    public function testHasSetAny()
    {
        $oParams = new ParameterParser(array(
                                        'one' => '',
                                        'two' => 0,
                                        'three' => '0',
                                        'four' => '1',
                                        'five' => 'anystring'
        ));
        $this->assertFalse($oParams->hasSetAny(array()));
        $this->assertFalse($oParams->hasSetAny(array('')));
        $this->assertFalse($oParams->hasSetAny(array('unknown')));
        $this->assertFalse($oParams->hasSetAny(array('one', 'two', 'three')));
        $this->assertTrue($oParams->hasSetAny(array('one', 'four')));
        $this->assertTrue($oParams->hasSetAny(array('four')));
        $this->assertTrue($oParams->hasSetAny(array('five')));
    }
}
