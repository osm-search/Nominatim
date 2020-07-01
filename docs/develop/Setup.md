# Setup Test Environment

To test changes and contribute to Nominatim you should be able to run
the test suite(s). For many usecases it's enough to create a Vagrant
virtual machine (see `VAGRANT.md`), import one small country into the
database.

## Prerequisites

Nominatim supports a range of PHP versions and PHPUnit versions also
move fast. We try to test against the newest stable PHP release and
PHPUnit version even though we expect many Nominatim users will install
older version on their production servers.

 * Python 3 (https://www.python.org/)
 * behave test framework >= 1.2.5 (https://github.com/behave/behave)
 * nose (https://nose.readthedocs.org)
 * pytidylib (http://countergram.com/open-source/pytidylib)
 * psycopg2 (http://initd.org/psycopg/)

#### Ubuntu 20

    sudo apt-get install -y phpunit php-codesniffer php-cgi
    pip3 install --user behave nose

#### Ubuntu 18

    pip3 install --user behave nose

    sudo apt-get install -y composer php-cgi php-cli php-mbstring php-xml zip unzip

    composer global require "squizlabs/php_codesniffer=*"
    sudo ln -s ~/.config/composer/vendor/bin/phpcs /usr/bin/

    composer global require "phpunit/phpunit=8.*"
    sudo ln -s ~/.config/composer/vendor/bin/phpunit /usr/bin/


#### CentOS 7 or 8

    sudo dnf install -y php-dom php-mbstring
    pip3 install --user behave nose

    composer global require "squizlabs/php_codesniffer=*"
    sudo ln -s ~/.config/composer/vendor/bin/phpcs /usr/bin/

    composer global require "phpunit/phpunit=^7"
    sudo ln -s ~/.config/composer/vendor/bin/phpunit /usr/bin/

## Run tests, code linter, code coverage

See `README.md` in `test` subdirectory.
