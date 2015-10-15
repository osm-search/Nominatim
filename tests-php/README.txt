Basic unit tests of PHP code. Very low coverage. Doesn't cover interaction
with the webserver/HTTP or database (yet).

You need to have
https://phpunit.de/manual/4.2/en/
installed.

To execute the test suite run
$ cd tests-php
$ phpunit ./

It will read phpunit.xml which points to the library, test path, bootstrap
strip and set other parameters.

