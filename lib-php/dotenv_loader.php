<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

require('Symfony/Component/Dotenv/autoload.php');

function loadDotEnv()
{
    $dotenv = new \Symfony\Component\Dotenv\Dotenv();
    $dotenv->load(CONST_ConfigDir.'/env.defaults');

    if (file_exists('.env')) {
        $dotenv->load('.env');
    }
}
