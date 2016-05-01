#!/bin/bash
#
# Installing the Required Software
# ================================
#
# *Note:* these installation instructions are also available in executable
#         form for use with vagrant in the vagrant/ directory.
#
# These instructions expect that you have a freshly installed CentOS version 7.
# Make sure all packages are are up-to-date by running:
#
    sudo yum update -y
#
# Setting up Repositories
# -----------------------
#
# The standard CentOS repositories don't contain all the required packages,
# you need to enable the EPEL repository as well. To enable it on CentOS,
# install the epel-release RPM by running:

    sudo yum install -y epel-release

#
# Getting the Software Packages
# -----------------------------
#
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
    sudo -u postgres apache

#
# Setting up the Apache Webserver
# -------------------------------
#
# You need to create an alias to the website directory in your apache
# configuration. This can be most easily done by XXX

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

    cd $USERHOME
    sudo -u $USERNAME git clone --recursive git://github.com/twain47/Nominatim.git

# The code is built in a special directory. Create this directory,
# then configure and build Nominatim in there:

#DOCS:    cd Nominatim
    sudo -u $USERNAME mkdir build
    cd build
    sudo -u $USERNAME cmake ../Nominatim
    sudo -u $USERNAME make

# You need to create a minimal configuration file that tells nominatim
# the name of your webserver user:

#DOCS:```
sudo -u $USERNAME tee << EOF
<?php
 @define('CONST_Database_Web_User', 'apache');
EOF
#DOCS:```

# There are lots of configuration settings you can tweak. Have a look
# at `settings/settings.php` for a full list. Most should have a sensible default.
# If you plan to import a large dataset (e.g. Europe, North America, planet),
# you should also enable flatnode storage of node locations. With this
# setting enabled, node coordinates are stored in a simple file instead
# of the database. This will save you import time and disk storage.
# Add to your settings/local.php:
#
#     @define('CONST_Osm2pgsql_Flatnode_File', '/path/to/flatnode.file');
#
#
# Downloading additional data
# ---------------------------
#
# The following data is optional but download is strongly recommended:
#
#     sudo -u $USERNAME wget -O data/wikipedia_article.sql.bin http://www.nominatim.org/data/wikipedia_article.sql.bin
#     sudo -u $USERNAME wget -O data/wikipedia_redirect.sql.bin http://www.nominatim.org/data/wikipedia_redirect.sql.bin
#     sudo -u $USERNAME wget -O data/gb_postcode_data.sql.gz http://www.nominatim.org/data/gb_postcode_data.sql.gz
#
#
# Initial Import of the Data
# --------------------------
#
# **Attention:** first try the import with a small excerpt, for example from Geofabrik.
#
# Download the data to import and load the data with the following command:
#
#     ./utils/setup.php --osm-file <your data file> --all [--osm2pgsql-cache 28000] 2>&1 | tee setup.log
#
# The --osm2pgsql-cache parameter is optional but strongly recommended for
# planet imports. It sets the node cache size for the osm2pgsql import part
# (see -C parameter in osm2pgsql help). 28GB are recommended for a full planet
# imports, for excerpts you can use less.
# Adapt to your available RAM to avoid swapping.
#
# The import will take as little as an hour for a small country extract
# and as much as 10 days for a full-scale planet import on less powerful
# hardware.
#
#
# Loading Additional Datasets
# ---------------------------
#
# The following commands will create additional entries for countries and POI searches:
#
#     ./utils/specialphrases.php --countries > data/specialphrases_countries.sql
#     psql -d nominatim -f data/specialphrases_countries.sql
#     ./utils/specialphrases.php --wiki-import > data/specialphrases.sql
#     psql -d nominatim -f data/specialphrases.sql

