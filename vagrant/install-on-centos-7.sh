#!/bin/bash
#
# *Note:* these installation instructions are also available in executable
#         form for use with vagrant in the vagrant/ directory.
#
# Installing the Required Software
# ================================
#
# These instructions expect that you have a freshly installed CentOS version 7.
# Make sure all packages are are up-to-date by running:
#
    sudo yum update -y

# The standard CentOS repositories don't contain all the required packages,
# you need to enable the EPEL repository as well. To enable it on CentOS,
# install the epel-release RPM by running:

    sudo yum install -y epel-release

# Now you can install all packages needed for Nominatim:

    sudo yum install -y postgresql-server postgresql-contrib postgresql-devel postgis postgis-utils \
                        git cmake make gcc gcc-c++ libtool policycoreutils-python \
                        php-pgsql php php-pear php-pear-DB libpqxx-devel proj-epsg \
                        bzip2-devel proj-devel geos-devel libxml2-devel boost-devel expat-devel zlib-devel

#
# System Configuration
# ====================
#
# The following steps are meant to configure a fresh CentOS installation
# for use with Nominatim. You may skip some of the steps if you have your
# OS already configured.
#
# Creating Dedicated User Accounts
# --------------------------------
#
# Nominatim will run as a global service on your machine. It is therefore
# best to install it under its own separate user account. In the following
# we assume this user is called nominatim and the installation will be in
# /srv/nominatim. To create the user and directory run:
#
#     sudo useradd -d /srv/nominatim -s /bin/bash -m nominatim
#
# You may find a more suitable location if you wish.
#
# To be able to copy and paste instructions from this manual, export
# user name and home directory now like this:
#
    export USERNAME=vagrant        #DOCS:    export USERNAME=nominatim
    export USERHOME=/home/vagrant  #DOCS:    export USERHOME=/srv/nominatim
#
# **Never, ever run the installation as a root user.** You have been warned.
#
# Setting up PostgreSQL
# ---------------------
#
# CentOS does not automatically create a database cluster. Therefore, start
# with initializing the database, then enable the server to start at boot:

    sudo postgresql-setup initdb
    sudo systemctl enable postgresql

#
# Next tune the postgresql configuration, which is located in 
# `/var/lib/pgsql/data/postgresql.conf`. See
# [the wiki](http://wiki.openstreetmap.org/wiki/Nominatim/Installation#PostgreSQL_Tuning_and_Configuration) for the parameters to change.
#
# Now start the postgresql service after updating this config file.

    sudo systemctl restart postgresql

#
# Finally, we need to add two postgres users: one for the user that does
# the import and another for the webserver ro access the database:
#

    sudo -u postgres createuser -s $USERNAME
    sudo -u postgres createuser apache

#
# Setting up the Apache Webserver
# -------------------------------
#
# You need to create an alias to the website directory in your apache
# configuration. Add a separate nominatim configuration to your webserver:

#DOCS:```
sudo cat > /etc/httpd/conf.d/nominatim.conf << EOFAPACHECONF
<Directory "$USERHOME/build/website"> #DOCS:<Directory "$USERHOME/Nominatim/build/website">
  Options FollowSymLinks MultiViews
  AddType text/html   .php
</Directory>

Alias /nominatim $USERHOME/build/website  #DOCS:Alias /nominatim $USERHOME/Nominatim/build/website
EOFAPACHECONF
#DOCS:```

sudo sed -i 's:#.*::' /etc/httpd/conf.d/nominatim.conf #DOCS:

#
# Then reload apache
#

    sudo systemctl restart httpd

#
# Adding SELinux Security Settings
# --------------------------------
#
# It is a good idea to leave SELinux enabled and enforcing, particularly
# with a web server accessible from the Internet. At a minimum the
# following SELinux labeling should be done for Nominatim:

    sudo semanage fcontext -a -t httpd_sys_content_t "$USERHOME/Nominatim/(website|lib|settings)(/.*)?"
    sudo semanage fcontext -a -t lib_t "$USERHOME/Nominatim/module/nominatim.so"
    sudo restorecon -R -v $USERHOME/Nominatim

#
# Installing Nominatim
# ====================
#
# Building and Configuration
# --------------------------
#
# Get the source code from Github and change into the source directory
#
if [ "x$CHECKOUT" == "xy" ]; then  #DOCS:

    cd $USERHOME
    sudo -u $USERNAME git clone --recursive git://github.com/twain47/Nominatim.git
#DOCS:    cd Nominatim

else                               #DOCS:
    cd $USERHOME                   #DOCS:
fi                                 #DOCS:

# The code is built in a special directory. Create this directory,
# then configure and build Nominatim in there:

    sudo -u $USERNAME mkdir build
    cd build
    sudo -u $USERNAME cmake $USERHOME/Nominatim
    sudo -u $USERNAME make

# You need to create a minimal configuration file that tells nominatim
# the name of your webserver user:

#DOCS:```
sudo -u $USERNAME cat > settings/local.php << EOF
<?php
 @define('CONST_Database_Web_User', 'apache');
EOF
#DOCS:```


Nominatim is now ready to use. Continue with
[importing a database from OSM data](Import_and_update.md).
