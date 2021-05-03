<?php

namespace Nominatim;

class Tokenizer
{
    private $oDB;

    public function __construct(&$oDB)
    {
        $this->oDB =& $oDB;
    }

    public function checkStatus()
    {
    }
}
