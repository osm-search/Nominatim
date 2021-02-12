<?php

require('Symfony/Component/Dotenv/autoload.php');

function loadDotEnv()
{
    $dotenv = new \Symfony\Component\Dotenv\Dotenv();
    $dotenv->load(CONST_ConfigDir.'/env.defaults');

    if (file_exists('.env')) {
        $dotenv->load('.env');
    }
}
