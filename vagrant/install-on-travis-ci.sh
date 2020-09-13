#!/bin/bash

# This script runs in a travis-ci.org virtual machine
# https://docs.travis-ci.com/user/reference/focal/
# Ubuntu 20 (focal)
# user 'travis'
# $TRAVIS_BUILD_DIR is /home/travis/build/openstreetmap/Nominatim/, for others see
#   https://docs.travis-ci.com/user/environment-variables/#Default-Environment-Variables
# Postgres 12 installed and started. role 'travis' already superuser
# Python 3.8
# Travis has a 4 MB, 10000 line output limit, so where possible we run script --quiet


sudo apt-get update -qq

sudo apt-get install -y -qq build-essential cmake g++ libboost-dev libboost-system-dev \
                            libboost-filesystem-dev libexpat1-dev zlib1g-dev \
                            libbz2-dev libpq-dev libproj-dev \
                            postgresql-server-dev-12 postgresql-12-postgis-3 \
                            postgresql-contrib postgresql-12-postgis-3-scripts \
                            apache2 php php-pgsql libapache2-mod-php \
                            php-intl python3-setuptools python3-dev python3-pip \
                            python3-psycopg2 python3-tidylib git

sudo apt-get install -y -qq php-cgi

pip3 install --quiet behave nose osmium

# https://github.com/squizlabs/PHP_CodeSniffer
composer global require "squizlabs/php_codesniffer=*"
sudo ln -s /home/travis/.config/composer/vendor/bin/phpcs /usr/bin/

composer global require "phpunit/phpunit=7.*"
sudo ln -s /home/travis/.config/composer/vendor/bin/phpunit /usr/bin/

sudo -u postgres createuser -S www-data

# Make sure that system servers can read from the home directory:
chmod a+x $HOME
chmod a+x $TRAVIS_BUILD_DIR


sudo tee /etc/apache2/conf-available/nominatim.conf << EOFAPACHECONF > /dev/null
    <Directory "$TRAVIS_BUILD_DIR/build/website">
      Options FollowSymLinks MultiViews
      AddType text/html   .php
      DirectoryIndex search.php
      Require all granted
    </Directory>

    Alias /nominatim $TRAVIS_BUILD_DIR/build/website
EOFAPACHECONF


sudo a2enconf nominatim
sudo service apache2 restart

wget -O $TRAVIS_BUILD_DIR/data/country_osm_grid.sql.gz https://www.nominatim.org/data/country_grid.sql.gz

mkdir build
cd build
cmake $TRAVIS_BUILD_DIR
make


tee settings/local.php << EOF
<?php
 @define('CONST_Website_BaseURL', '/nominatim/');
 @define('CONST_Database_DSN', 'pgsql:dbname=test_api_nominatim');
 @define('CONST_Wikipedia_Data_Path', CONST_BasePath.'/test/testdb');
 @define('CONST_Replication_Max_Diff_size', '3');
EOF

