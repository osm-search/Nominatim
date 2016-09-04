<?php

require_once(CONST_BasePath.'/lib/lib.php');
require_once(CONST_BasePath.'/lib/db.php');

if (get_magic_quotes_gpc())
{
    echo "Please disable magic quotes in your php.ini configuration\n";
    exit;
}
