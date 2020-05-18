<?php

namespace Nominatim;

use Dotenv\Dotenv;

/**
 * Uses Dotenv to acess environment values
 */
class Config
{
    static $dotenv;
    
    public static function setupEnv($dir = __DIR__, $path = '../.env')
    {
        define('DIR_VENDOR', dirname(__DIR__).'/vendor/');
        echo 'Trying to connect from the directory: '.$dir."\n";
        if (file_exists(DIR_VENDOR . 'autoload.php')) {
            require_once(DIR_VENDOR . 'autoload.php');
            $dotenv = Dotenv::createImmutable($dir, $path);
            $dotenv->load();
        } else {
            echo 'Failed to load autoload.php from '.DIR_VENDOR;
        }
    }
}
