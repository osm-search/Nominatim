#!/bin/bash

# This script sets up a Nominatim installation on a Ubuntu box.
#
# For more detailed installation instructions see also
# http://wiki.openstreetmap.org/wiki/Nominatim/Installation

## Part 1: System preparation

## During 'vagrant provision' this script runs as root and the current
## directory is '/root'
USERNAME=vagrant

### 
### maybe create ubuntu user
### 

# if [[ ! `id -u $USERNAME` ]]; then
#   useradd $USERNAME --create-home --shell /bin/bash
#   
#   # give sudo power
#   echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/99-$USERNAME-user
#   chmod 0440 /etc/sudoers.d/99-$USERNAME-user
#   service sudo restart
#   
#   # add basic .profile
#   cp -r .ssh .profile .bashrc /home/$USERNAME/
#   chown -R $USERNAME /home/$USERNAME/.*
#   chgrp -R $USERNAME /home/$USERNAME/.*
#   
#   # now ideally login as $USERNAME and continue
#   su $USERNAME -l
# fi


sudo apt-get update -qq
sudo apt-get upgrade -y
sudo apt-get install -y build-essential libgeos-dev libpq-dev libbz2-dev \
                        libtool automake libproj-dev libboost-dev  libboost-system-dev \
                        libboost-filesystem-dev libboost-thread-dev libexpat-dev
sudo apt-get autoremove -y

# get arrow-keys working in terminal (e.g. editing in vi)
echo 'stty sane' >> ~/.bash_profile
echo 'export TERM=linux' >> ~/.bash_profile
source ~/.bash_profile


###
### PostgreSQL 9.3 + PostGIS 2.1
###

sudo apt-get install -y postgresql-9.3-postgis-2.1 postgresql-contrib-9.3 postgresql-server-dev-9.3 
# already included: proj-bin libgeos-dev

# make sure OS-authenticated users (e.g. $USERNAME) can access
sudo sed -i "s/ident/trust/" /etc/postgresql/9.3/main/pg_hba.conf
sudo sed -i "s/md5/trust/"   /etc/postgresql/9.3/main/pg_hba.conf
sudo sed -i "s/peer/trust/"  /etc/postgresql/9.3/main/pg_hba.conf
sudo /etc/init.d/postgresql restart

# creates the role
sudo -u postgres createuser -s $USERNAME



###
### PHP for frontend
###
sudo apt-get install -y php5 php5-pgsql php-pear php-db


# get rid of some warning
# where is the ini file? 'php --ini'
echo "date.timezone = 'Etc/UTC'" | sudo tee /etc/php5/cli/conf.d/99-timezone.ini > /dev/null



###
### Nominatim
###
sudo apt-get install -y libgeos-c1 libgeos++-dev libxml2-dev

## Part 2: Nominatim installaion

# now ideally login as $USERNAME and continue
cd /home/$USERNAME

# If the Nominatim source is not being shared with the host, check out source.
if [ ! -d "Nominatim" ]; then
  sudo apt-get install -y git
  sudo -u $USERNAME git clone --recursive https://github.com/twain47/Nominatim.git
fi

cd Nominatim

sudo -u $USERNAME ./autogen.sh
sudo -u $USERNAME ./configure
sudo -u $USERNAME make
chmod +x ./
chmod +x ./module


LOCALSETTINGS_FILE='settings/local.php'
if [[ -e "$LOCALSETTINGS_FILE" ]]; then
  echo "$LOCALSETTINGS_FILE already exist, writing to settings/local-vagrant.php instead."
  LOCALSETTINGS_FILE='settings/local-vagrant.php'
fi

# IP=`curl -s http://bot.whatismyipaddress.com`
IP=localhost
echo "<?php
   // General settings
   @define('CONST_Database_DSN', 'pgsql://@/nominatim');
   // Paths
   @define('CONST_Postgresql_Version', '9.3');
   @define('CONST_Postgis_Version', '2.1');
   // Website settings
   @define('CONST_Website_BaseURL', 'http://$IP:8089/nominatim/');
" > $LOCALSETTINGS_FILE







###
### Setup Apache/website
###

sudo -u postgres createuser -SDR www-data

echo '
Listen 8089
<VirtualHost *:8089>
    # DirectoryIndex index.html
    # ErrorDocument 403 /index.html

    DocumentRoot "/var/www/"
 
    <Directory "/var/www/nominatim/">
      Options FollowSymLinks MultiViews
      AddType text/html   .php     
    </Directory>
</VirtualHost>
' | sudo tee /etc/apache2/sites-enabled/nominatim.conf > /dev/null


apache2ctl graceful


mkdir -m 755 /var/www/nominatim
chown $USERNAME /var/www/nominatim
sudo -u $USERNAME ./utils/setup.php --create-website /var/www/nominatim


# if you get 'permission denied for relation word', then try
# GRANT usage ON SCHEMA public TO "www-data";
# GRANT SELECT ON ALL TABLES IN SCHEMA public TO "www-data";

##
## Test suite (Python)
## https://github.com/twain47/Nominatim/tree/master/tests
##
apt-get install -y python-dev python-pip python-Levenshtein python-shapely \
                        python-psycopg2 tidy python-nose python-tidylib
pip install lettuce==0.2.18 six==1.7 haversine

## Test suite (PHP)
## https://github.com/twain47/Nominatim/tree/master/tests-php
apt-get install -y phpunit


