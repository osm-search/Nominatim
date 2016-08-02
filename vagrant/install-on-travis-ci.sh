#!/bin/bash

# This script runs in a travis-ci.org (or .com) virtual machine
# https://docs.travis-ci.com/user/trusty-ci-environment/
# Ubuntu 14 (trusty)
# user 'travis'
# $TRAVIS_BUILD_DIR is /home/travis/build/twain47/Nominatim/, for more see
#   https://docs.travis-ci.com/user/environment-variables/#Default-Environment-Variables
# Postgres 9.2 installed and started. role 'travis' already superuser
# Python 2.7.10, pip 7.1.2

# Travis has a 4 MB, 10000 line output limit, so where possible we supress
#  output from installation scripts
# Travis strips color from the output

sudo service postgresql stop

sudo apt-get update -qq
sudo apt-get install -y -qq libboost-dev libboost-system-dev \
                        libboost-filesystem-dev libexpat1-dev zlib1g-dev libxml2-dev\
                        libbz2-dev libpq-dev libgeos-c1 libgeos++-dev libproj-dev \
                        postgresql-server-dev-9.3 postgresql-9.3-postgis-2.1 postgresql-contrib-9.3 \
                        apache2 php5 php5-pgsql php-pear php-db

sudo apt-get install -y -qq python-Levenshtein python-shapely \
                        python-psycopg2 tidy python-nose python-tidylib \
                        python-numpy phpunit

sudo -H pip install --quiet 'setuptools>=23.0.0' lettuce==0.2.18 'six>=1.9' haversine

sudo service postgresql restart
sudo -u postgres createuser -S www-data

# Make sure that system servers can read from the home directory:
chmod a+x $HOME
chmod a+x $TRAVIS_BUILD_DIR


sudo tee /etc/apache2/conf-available/nominatim.conf << EOFAPACHECONF > /dev/null
    <Directory "$TRAVIS_BUILD_DIR/build/website">
      Options FollowSymLinks MultiViews
      AddType text/html   .php
      Require all granted
    </Directory>

    Alias /nominatim $TRAVIS_BUILD_DIR/build/website
EOFAPACHECONF


sudo a2enconf nominatim
sudo service apache2 restart


mkdir build
cd build
cmake $TRAVIS_BUILD_DIR
make


tee settings/local.php << EOF
<?php
 @define('CONST_Website_BaseURL', '/nominatim/');
EOF