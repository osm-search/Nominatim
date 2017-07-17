<?php
require_once 'SebastianBergmann/CodeCoverage/autoload.php';
$covfilter = new SebastianBergmann\CodeCoverage\Filter();
$covfilter->addDirectoryToWhitelist($_SERVER['COV_PHP_DIR']);
$coverage = new SebastianBergmann\CodeCoverage\CodeCoverage(null, $covfilter);
$coverage->start($_SERVER['COV_TEST_NAME']);

include $_SERVER['COV_SCRIPT_FILENAME'];


$coverage->stop();
$writer = new \SebastianBergmann\CodeCoverage\Report\PHP;
$writer->process($coverage, $_SERVER['PHP_CODE_COVERAGE_FILE']);
