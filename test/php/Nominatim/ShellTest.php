<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/lib.php');
require_once(CONST_BasePath.'/lib/Shell.php');

class ShellTest extends \PHPUnit\Framework\TestCase
{

    public function testEscapeFromArray()
    {
        $oShell = new \Nominatim\Shell;

        $this->assertSame(
            'do -a abc 9',
            $oShell->escapeFromArray(array('do', '-a', 'abc', 9)),
            'no escaping needed'
        );
        $this->assertSame(
            "do -a ' b ' --flag 'two words' 'v=1'",
            $oShell->escapeFromArray(array('do', '-a', ' b ', '--flag', 'two words', 'v=1')),
            'escape whitespace'
        );
        $this->assertSame(
            "do ';' '|more&' '2>&1'",
            $oShell->escapeFromArray(array('do', ';', '|more&', '2>&1')),
            'escape'
        );
    }
}
