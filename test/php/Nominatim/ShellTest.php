<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/Shell.php');

class ShellTest extends \PHPUnit\Framework\TestCase
{
    public function testNew()
    {
        $this->expectException('ArgumentCountError');
        $this->expectExceptionMessage('Too few arguments to function');
        $oCmd = new \Nominatim\Shell();


        $oCmd = new \Nominatim\Shell('wc', '-l', 'file.txt');
        $this->assertSame(
            "wc -l 'file.txt'",
            $oCmd->escapedCmd()
        );
    }

    public function testaddParams()
    {
        $oCmd = new \Nominatim\Shell('grep');
        $oCmd->addParams('-a', 'abc')
               ->addParams(10);

        $this->assertSame(
            'grep -a abc 10',
            $oCmd->escapedCmd(),
            'no escaping needed, chained'
        );

        $oCmd = new \Nominatim\Shell('grep');
        $oCmd->addParams();
        $oCmd->addParams(null);
        $oCmd->addParams('');

        $this->assertEmpty($oCmd->aParams);
        $this->assertSame('grep', $oCmd->escapedCmd(), 'empty params');

        $oCmd = new \Nominatim\Shell('echo', '-n', 0);
        $this->assertSame(
            'echo -n 0',
            $oCmd->escapedCmd(),
            'zero param'
        );

        $oCmd = new \Nominatim\Shell('/path with space/do.php');
        $oCmd->addParams('-a', ' b ');
        $oCmd->addParams('--flag');
        $oCmd->addParams('two words');
        $oCmd->addParams('v=1');

        $this->assertSame(
            "'/path with space/do.php' -a ' b ' --flag 'two words' 'v=1'",
            $oCmd->escapedCmd(),
            'escape whitespace'
        );

        $oCmd = new \Nominatim\Shell('grep');
        $oCmd->addParams(';', '|more&', '2>&1');

        $this->assertSame(
            "grep ';' '|more&' '2>&1'",
            $oCmd->escapedCmd(),
            'escape shell characters'
        );
    }

    public function testaddEnvPair()
    {
        $oCmd = new \Nominatim\Shell('date');

        $oCmd->addEnvPair('one', 'two words')
             ->addEnvPair('null', null)
             ->addEnvPair(null, 'null')
             ->addEnvPair('empty', '')
             ->addEnvPair('', 'empty');

        $this->assertEquals(
            array('one' => 'two words', 'empty' => ''),
            $oCmd->aEnv
        );

        $oCmd->addEnvPair('one', 'overwrite');
        $this->assertEquals(
            array('one' => 'overwrite', 'empty' => ''),
            $oCmd->aEnv
        );
    }

    public function testClone()
    {
        $oCmd = new \Nominatim\Shell('wc', '-l', 'file.txt');
        $oCmd2 = clone $oCmd;
        $oCmd->addParams('--flag');
        $oCmd2->addParams('--flag2');

        $this->assertSame(
            "wc -l 'file.txt' --flag",
            $oCmd->escapedCmd()
        );

        $this->assertSame(
            "wc -l 'file.txt' --flag2",
            $oCmd2->escapedCmd()
        );
    }

    public function testRun()
    {
        $oCmd = new \Nominatim\Shell('echo');

        $this->assertSame(0, $oCmd->run());

        // var_dump($sStdout);
    }
}
