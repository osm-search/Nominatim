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

require_once(CONST_LibDir.'/DebugHtml.php');

class DebugTest extends \PHPUnit\Framework\TestCase
{

    protected function setUp(): void
    {
        $this->oWithDebuginfo = $this->getMockBuilder(\GeococdeMock::class)
                                    ->setMethods(array('debugInfo'))
                                    ->getMock();
        $this->oWithDebuginfo->method('debugInfo')
                  ->willReturn(array('key1' => 'val1', 'key2' => 'val2', 'key3' => 'val3'));


        $this->oWithToString = $this->getMockBuilder(\SomeMock::class)
                                    ->setMethods(array('__toString'))
                                    ->getMock();
        $this->oWithToString->method('__toString')->willReturn('me as string');
    }

    public function testPrintVar()
    {
        $this->expectOutputString(<<<EOT
<pre><b>Var0:</b>  </pre>
<pre><b>Var1:</b>  <i>True</i></pre>
<pre><b>Var2:</b>  <i>False</i></pre>
<pre><b>Var3:</b>  0</pre>
<pre><b>Var4:</b>  &#039;String&#039;</pre>
<pre><b>Var5:</b>  0 => &#039;one&#039;
       1 => &#039;two&#039;
       2 => &#039;three&#039;</pre>
<pre><b>Var6:</b>  &#039;key&#039; => &#039;value&#039;
       &#039;key2&#039; => &#039;value2&#039;</pre>
<pre><b>Var7:</b>  me as string</pre>
<pre><b>Var8:</b>  &#039;value&#039;, &#039;value2&#039;</pre>

EOT
        );
    
        Debug::printVar('Var0', null);
        Debug::printVar('Var1', true);
        Debug::printVar('Var2', false);
        Debug::printVar('Var3', 0);
        Debug::printVar('Var4', 'String');
        Debug::printVar('Var5', array('one', 'two', 'three'));
        Debug::printVar('Var6', array('key' => 'value', 'key2' => 'value2'));
        Debug::printVar('Var7', $this->oWithToString);
        Debug::printVar('Var8', Debug::fmtArrayVals(array('key' => 'value', 'key2' => 'value2')));
    }


    public function testDebugArray()
    {
        $this->expectOutputString(<<<EOT
<pre><b>Arr0:</b>  &#039;null&#039;</pre>
<pre><b>Arr1:</b>  &#039;key1&#039; => &#039;val1&#039;
       &#039;key2&#039; => &#039;val2&#039;
       &#039;key3&#039; => &#039;val3&#039;</pre>

EOT
        );
    
        Debug::printDebugArray('Arr0', null);
        Debug::printDebugArray('Arr1', $this->oWithDebuginfo);
    }


    public function testPrintDebugTable()
    {
        $this->expectOutputString(<<<EOT
<b>Table1:</b>
<table border='1'>
</table>
<b>Table2:</b>
<table border='1'>
</table>
<b>Table3:</b>
<table border='1'>
  <tr>
    <th><small>0</small></th>
    <th><small>1</small></th>
  </tr>
  <tr>
    <td><pre>&#039;one&#039;</pre></td>
    <td><pre>&#039;two&#039;</pre></td>
  </tr>
  <tr>
    <td><pre>&#039;three&#039;</pre></td>
    <td><pre>&#039;four&#039;</pre></td>
  </tr>
</table>
<b>Table4:</b>
<table border='1'>
  <tr>
    <th><small>key1</small></th>
    <th><small>key2</small></th>
    <th><small>key3</small></th>
  </tr>
  <tr>
    <td><pre>&#039;val1&#039;</pre></td>
    <td><pre>&#039;val2&#039;</pre></td>
    <td><pre>&#039;val3&#039;</pre></td>
  </tr>
</table>

EOT
        );
    
        Debug::printDebugTable('Table1', null);

        Debug::printDebugTable('Table2', array());

        // Numeric headers
        Debug::printDebugTable('Table3', array(array('one', 'two'), array('three', 'four')));

        // Associate array
        Debug::printDebugTable('Table4', array($this->oWithDebuginfo));
    }

    public function testPrintGroupTable()
    {
        $this->expectOutputString(<<<EOT
<b>Table1:</b>
<table border='1'>
</table>
<b>Table2:</b>
<table border='1'>
</table>
<b>Table3:</b>
<table border='1'>
  <tr>
    <th><small>Group</small></th>
    <th><small>key1</small></th>
    <th><small>key2</small></th>
  </tr>
  <tr>
    <td><pre>group1</pre></td>
    <td><pre>&#039;val1&#039;</pre></td>
    <td><pre>&#039;val2&#039;</pre></td>
  </tr>
  <tr>
    <td><pre>group1</pre></td>
    <td><pre>&#039;one&#039;</pre></td>
    <td><pre>&#039;two&#039;</pre></td>
  </tr>
  <tr>
    <td><pre>group2</pre></td>
    <td><pre>&#039;val1&#039;</pre></td>
    <td><pre>&#039;val2&#039;</pre></td>
  </tr>
</table>
<b>Table4:</b>
<table border='1'>
  <tr>
    <th><small>Group</small></th>
    <th><small>key1</small></th>
    <th><small>key2</small></th>
    <th><small>key3</small></th>
  </tr>
  <tr>
    <td><pre>group1</pre></td>
    <td><pre>&#039;val1&#039;</pre></td>
    <td><pre>&#039;val2&#039;</pre></td>
    <td><pre>&#039;val3&#039;</pre></td>
  </tr>
  <tr>
    <td><pre>group1</pre></td>
    <td><pre>&#039;val1&#039;</pre></td>
    <td><pre>&#039;val2&#039;</pre></td>
    <td><pre>&#039;val3&#039;</pre></td>
  </tr>
</table>

EOT
        );
    
        Debug::printGroupTable('Table1', null);
        Debug::printGroupTable('Table2', array());

        // header are taken from first group item, thus no key3 gets printed
        $aGroups = array(
                    'group1' => array(
                                 array('key1' => 'val1', 'key2' => 'val2'),
                                 array('key1' => 'one', 'key2' => 'two', 'unknown' => 1),
                                ),
                    'group2' => array(
                                 array('key1' => 'val1', 'key2' => 'val2', 'key3' => 'val3'),
                                )
                   );
        Debug::printGroupTable('Table3', $aGroups);

        $aGroups = array(
                    'group1' => array($this->oWithDebuginfo, $this->oWithDebuginfo),
                   );
        Debug::printGroupTable('Table4', $aGroups);
    }
}
