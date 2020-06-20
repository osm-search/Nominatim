#!/bin/bash
#
# hacks for broken vagrant box      #DOCS:
sudo rm -f /var/lib/dpkg/lock       #DOCS:
sudo update-locale LANG=en_US.UTF-8 #DOCS:
export APT_LISTCHANGES_FRONTEND=none #DOCS:
export DEBIAN_FRONTEND=noninteractive #DOCS:

#
# *Note:* these installation instructions are also available in executable
#         form for use with vagrant under vagrant/Install-on-Ubuntu-18.sh.
#
# Installing the Required Software
# ================================
#
# These instructions expect that you have a freshly installed Ubuntu 18.04.
#
# Make sure all packages are are up-to-date by running:
#

#DOCS:    :::sh
    sudo apt-get -o DPkg::options::="--force-confdef" -o DPkg::options::="--force-confold" --force-yes -fuy install grub-pc #DOCS:
    sudo apt-get update -qq

# Now you can install all packages needed for Nominatim:

    sudo apt-get install -y build-essential cmake g++ libboost-dev libboost-system-dev \
                            libboost-filesystem-dev libexpat1-dev zlib1g-dev\
                            libbz2-dev libpq-dev libproj-dev \
                            postgresql-server-dev-10 postgresql-10-postgis-2.4 \
                            postgresql-contrib-10 postgresql-10-postgis-scripts \
                            apache2 php php-pgsql libapache2-mod-php \
                            php-intl python3-setuptools python3-dev python3-pip \
                            python3-psycopg2 python3-tidylib git


#
# System Configuration
# ====================
#
# The following steps are meant to configure a fresh Ubuntu installation
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
# Make sure that system servers can read from the home directory:

    chmod a+x $USERHOME

# Setting up PostgreSQL
# ---------------------
#
# Tune the postgresql configuration, which is located in 
# `/etc/postgresql/10/main/postgresql.conf`. See section *Postgres Tuning* in
# [the installation page](../admin/Installation.md#postgresql-tuning)
# for the parameters to change.
#
# Restart the postgresql service after updating this config file.

    sudo systemctl restart postgresql

#
# Finally, we need to add two postgres users: one for the user that does
# the import and another for the webserver which should access the database
# for reading only:
#

    sudo -u postgres createuser -s $USERNAME
    sudo -u postgres createuser www-data

#
# Setting up the Apache Webserver
# -------------------------------
#
# You need to create an alias to the website directory in your apache
# configuration. Add a separate nominatim configuration to your webserver:

#DOCS:```sh
sudo tee /etc/apache2/conf-available/nominatim.conf << EOFAPACHECONF
<Directory "$USERHOME/build/website"> #DOCS:<Directory "$USERHOME/Nominatim/build/website">
  Options FollowSymLinks MultiViews
  AddType text/html   .php
  DirectoryIndex search.php
  Require all granted
</Directory>

Alias /nominatim $USERHOME/build/website  #DOCS:Alias /nominatim $USERHOME/Nominatim/build/website
EOFAPACHECONF
#DOCS:```

sudo sed -i 's:#.*::' /etc/apache2/conf-available/nominatim.conf #DOCS:

#
# Then enable the configuration and restart apache
#

    sudo a2enconf nominatim
    sudo systemctl restart apache2

#
# Installing Nominatim
# ====================
#
# Building and Configuration
# --------------------------
#
# Get the source code from Github and change into the source directory
#
if [ "x$1" == "xyes" ]; then  #DOCS:    :::sh
    cd $USERHOME
    git clone --recursive git://github.com/openstreetmap/Nominatim.git
    cd Nominatim
else                               #DOCS:
    cd $USERHOME/Nominatim         #DOCS:
fi                                 #DOCS:

# When installing the latest source from github, you also need to
# download the country grid:

if [ ! -f data/country_osm_grid.sql.gz ]; then       #DOCS:    :::sh
    wget -O data/country_osm_grid.sql.gz https://www.nominatim.org/data/country_grid.sql.gz
fi                                 #DOCS:

# The code must be built in a separate directory. Create this directory,
# then configure and build Nominatim in there:

    cd $USERHOME                   #DOCS:    :::sh
    mkdir build
    cd build
    cmake $USERHOME/Nominatim
    make

# You need to create a minimal configuration file that tells nominatim
# where it is located on the webserver:

#DOCS:```sh
tee settings/local.php << EOF
<?php
 @define('CONST_Website_BaseURL', '/nominatim/');
EOF
#DOCS:```


# Nominatim is now ready to use. Continue with
# [importing a database from OSM data](../admin/Import.md).
