<?php
require_once 'SebastianBergmann/CodeCoverage/autoload.php';


function coverage_shutdown($oCoverage)
{
    $oCoverage->stop();
    $writer = new \SebastianBergmann\CodeCoverage\Report\PHP;
    $writer->process($oCoverage, $_SERVER['PHP_CODE_COVERAGE_FILE']);
}

$covfilter = new SebastianBergmann\CodeCoverage\Filter();
$covfilter->addDirectoryToWhitelist($_SERVER['COV_PHP_DIR'].'/lib');
$covfilter->addDirectoryToWhitelist($_SERVER['COV_PHP_DIR'].'/website');
$coverage = new SebastianBergmann\CodeCoverage\CodeCoverage(null, $covfilter);
$coverage->start($_SERVER['COV_TEST_NAME']);

register_shutdown_function('coverage_shutdown', $coverage);

include $_SERVER['COV_SCRIPT_FILENAME'];
