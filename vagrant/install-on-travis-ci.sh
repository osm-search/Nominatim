#!/bin/bash


# https://docs.travis-ci.com/user/trusty-ci-environment/
# postgres 9.1 running
# python 2.7

sudo apt-get update -qq

sudo service postgresql stop # 9.1 is running

sudo apt-get install -y -qq build-essential cmake g++ libboost-dev libboost-system-dev \
                        libboost-filesystem-dev libexpat1-dev zlib1g-dev libxml2-dev\
                        libbz2-dev libpq-dev libgeos-c1 libgeos++-dev libproj-dev \
                        postgresql-server-dev-9.3 postgresql-9.3-postgis-2.1 postgresql-contrib-9.3 \
                        apache2 php5 php5-pgsql php-pear php-db




sudo apt-get install -y -qq python-dev python-pip python-levenshtein python-shapely \
                        python-psycopg2 tidy python-nose python-tidylib \
                        phpunit

pip install --quiet lettuce==0.2.18 six==1.7 haversine

sudo service postgresql restart


# Make sure that system servers can read from the home directory:
chmod a+x $TRAVIS_BUILD_DIR
chmod a+x $TRAVIS_BUILD_DIR/..


# sudo -u postgres createuser -s travis
# sudo -u postgres 
# createuser -S www-data

# sudo mkdir -p /etc/apache2/conf-available/

sudo tee /etc/apache2/conf-available/nominatim.conf << EOFAPACHECONF
    <Directory "$TRAVIS_BUILD_DIR/build/website">
      Options FollowSymLinks MultiViews
      AddType text/html   .php
      Require all granted
    </Directory>

    Alias /nominatim $TRAVIS_BUILD_DIR/build/website
EOFAPACHECONF

sudo sed -i 's:#.*::' /etc/apache2/conf-available/nominatim.conf

sudo a2enconf nominatim
sudo service apache2 restart


cd $TRAVIS_BUILD_DIR
mkdir build
cd build
cmake $TRAVIS_BUILD_DIR # /Nominatim
make


tee settings/local.php << EOF
<?php
 @define('CONST_Website_BaseURL', '/nominatim/');
EOF