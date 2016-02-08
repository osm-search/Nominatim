#!/bin/bash

# This script sets up a Nominatim installation on a CentOS 7 box.
#
# For more detailed CentOS installation instructions see also
# http://wiki.openstreetmap.org/wiki/Nominatim/Installation_on_CentOS

## Part 1: System preparation

## During 'vagrant provision' this script runs as root and the current
## directory is '/root'
USERNAME=vagrant

yum update -y
yum install -y epel-release

yum install -y postgresql-server postgresql-contrib postgresql-devel postgis postgis-utils \
               make automake gcc gcc-c++ libtool policycoreutils-python \
               php-pgsql php php-pear php-pear-DB libpqxx-devel proj-epsg \
               bzip2-devel proj-devel geos-devel libxml2-devel boost-devel \
               expat-devel zlib-devel

# Create a cluster and start up postgresql.
postgresql-setup initdb
systemctl enable postgresql
systemctl start postgresql

# We leave postgresql in its default configuration here. This is only
# suitable for small extracts.

# Create the necessary postgres users.
sudo -u postgres createuser -s vagrant
sudo -u postgres createuser apache

# Create the website directory.
mkdir -m 755 /var/www/html/nominatim
chown vagrant /var/www/html/nominatim

# Set up the necessary rights on SELinux.
semanage fcontext -a -t httpd_sys_content_t "/home/vagrant/Nominatim/(website|lib|settings)(/.*)?"
semanage fcontext -a -t lib_t "/home/vagrant/Nominatim/module/nominatim.so"
semanage port -a -t http_port_t -p tcp 8089
restorecon -R -v /home/vagrant/Nominatim

# Configure apache site.
echo '
Listen 8089
<VirtualHost *:8089>
    # DirectoryIndex index.html
    # ErrorDocument 403 /index.html

    DocumentRoot "/var/www/html/"
 
    <Directory "/var/www/html/nominatim/">
      Options FollowSymLinks MultiViews
      AddType text/html   .php
    </Directory>
</VirtualHost>
' | sudo tee /etc/httpd/conf.d/nominatim.conf > /dev/null

# Restart apache to enable the site configuration.
systemctl enable httpd
systemctl restart httpd

## Part 2: Nominatim installaion

# now ideally login as $USERNAME and continue
cd /home/$USERNAME

# If the Nominatim source is not being shared with the host, check out source.
if [ ! -d "Nominatim" ]; then
  yum install -y git
  sudo -u $USERNAME git clone --recursive https://github.com/twain47/Nominatim.git
fi

# Configure and compile the source.
cd Nominatim
sudo -u $USERNAME ./autogen.sh
sudo -u $USERNAME ./configure
sudo -u $USERNAME make

# Make sure that postgres has access to the nominatim library.
chmod +x /home/$USERNAME
chmod +x ./
chmod +x ./module

# Create customized settings suitable for this VM installation.
LOCALSETTINGS_FILE='settings/local.php'
if [[ -e "$LOCALSETTINGS_FILE" ]]; then
  echo "$LOCALSETTINGS_FILE already exist, writing to settings/local-vagrant.php instead."
  LOCALSETTINGS_FILE='settings/local-vagrant.php'
fi

IP=localhost
echo "<?php
   // General settings
   @define('CONST_Database_DSN', 'pgsql://@/nominatim');
   // Paths
   @define('CONST_Postgresql_Version', '9.2');
   @define('CONST_Postgis_Version', '2.0');
   @define('CONST_Database_Web_User', 'apache');
   // Website settings
   @define('CONST_Website_BaseURL', 'http://$IP:8089/nominatim/');
" > $LOCALSETTINGS_FILE

# Install the web interface.
sudo -u $USERNAME ./utils/setup.php --create-website /var/www/html/nominatim
