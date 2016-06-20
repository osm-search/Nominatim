#!/bin/bash

sudo apt-get update -qq

sudo apt-get -o Dpkg::Options::="--force-confnew" upgrade -y -qq

sudo apt-get install -y -qq build-essential cmake g++ libboost-dev libboost-system-dev \
                        libboost-filesystem-dev libexpat1-dev zlib1g-dev libxml2-dev\
                        libbz2-dev libpq-dev libgeos-dev libgeos++-dev libproj-dev \
                        postgresql-server-dev-9.5 postgresql-9.5-postgis-2.2 postgresql-contrib-9.5 \
                        apache2 php php-pgsql libapache2-mod-php php-pear php-db \
                        git


sudo apt-get install -y --quiet python-dev python-pip python-levenshtein python-shapely \
                        python-psycopg2 tidy python-nose python-tidylib \
                        phpunit

pip install --quiet lettuce==0.2.18 six==1.7 haversine

sudo service postgresql restart

# sudo -u postgres createuser -s travis
# sudo -u postgres 
createuser www-data

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