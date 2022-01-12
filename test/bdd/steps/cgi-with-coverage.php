<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */
require_once 'SebastianBergmann/CodeCoverage/autoload.php';


function coverage_shutdown($oCoverage)
{
    $oCoverage->stop();
    $writer = new \SebastianBergmann\CodeCoverage\Report\PHP;
    $writer->process($oCoverage, $_SERVER['PHP_CODE_COVERAGE_FILE']);
}

$covfilter = new SebastianBergmann\CodeCoverage\Filter();
if (method_exists($covfilter, 'addDirectoryToWhitelist')) {
    // pre PHPUnit 9
    $covfilter->addDirectoryToWhitelist($_SERVER['COV_PHP_DIR'].'/lib-php');
    $covfilter->addDirectoryToWhitelist($_SERVER['COV_PHP_DIR'].'/website');
    $coverage = new SebastianBergmann\CodeCoverage\CodeCoverage(null, $covfilter);
} else {
    // since PHP Uit 9
    $covfilter->includeDirectory($_SERVER['COV_PHP_DIR'].'/lib-php');
    $covfilter->includeDirectory($_SERVER['COV_PHP_DIR'].'/website');
    $coverage = new SebastianBergmann\CodeCoverage\CodeCoverage(
        (new SebastianBergmann\CodeCoverage\Driver\Selector)->forLineCoverage($covfilter),
        $covfilter
    );
}

$coverage->start($_SERVER['COV_TEST_NAME']);

register_shutdown_function('coverage_shutdown', $coverage);

include $_SERVER['COV_SCRIPT_FILENAME'];
