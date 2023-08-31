#!/bin/bash -e
#
# hacks for broken vagrant box      #DOCS:
sudo rm -f /var/lib/dpkg/lock       #DOCS:
export APT_LISTCHANGES_FRONTEND=none #DOCS:
export DEBIAN_FRONTEND=noninteractive #DOCS:

# *Note:* these installation instructions are also available in executable
#         form for use with vagrant under vagrant/Install-on-Ubuntu-22.sh.
#
# Installing the Required Software
# ================================
#
# These instructions expect that you have a freshly installed Ubuntu 22.04.
#
# Make sure all packages are up-to-date by running:
#

    sudo apt update -qq

# Now you can install all packages needed for Nominatim:

    sudo apt install -y build-essential cmake g++ libboost-dev libboost-system-dev \
                        libboost-filesystem-dev libexpat1-dev zlib1g-dev \
                        libbz2-dev libpq-dev liblua5.3-dev lua5.3 lua-dkjson \
                        nlohmann-json3-dev postgresql-14-postgis-3 \
                        postgresql-contrib-14 postgresql-14-postgis-3-scripts \
                        php-cli php-pgsql php-intl libicu-dev python3-dotenv \
                        python3-psycopg2 python3-psutil python3-jinja2 \
                        python3-icu python3-datrie python3-sqlalchemy \
                        python3-asyncpg python3-yaml git

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
# The following instructions assume you are logged in as this user.
# You can also switch to the user with:
#
#     sudo -u nominatim bash
#
# To be able to copy and paste instructions from this manual, export
# user name and home directory now like this:
#
if [ "x$USERNAME" == "x" ]; then #DOCS:
    export USERNAME=vagrant        #DOCS:    export USERNAME=nominatim
    export USERHOME=/home/vagrant  #DOCS:    export USERHOME=/srv/nominatim
fi                                 #DOCS:
#
# **Never, ever run the installation as a root user.** You have been warned.
#
# Make sure that system servers can read from the home directory:

    chmod a+x $USERHOME

# Setting up PostgreSQL
# ---------------------
#
# Tune the postgresql configuration, which is located in 
# `/etc/postgresql/14/main/postgresql.conf`. See section *Tuning the PostgreSQL database*
# in [the installation page](../admin/Installation.md#tuning-the-postgresql-database)
# for the parameters to change.
#
# Restart the postgresql service after updating this config file.

if [ "x$NOSYSTEMD" == "xyes" ]; then  #DOCS:
    sudo pg_ctlcluster 14 main start  #DOCS:
else                                  #DOCS:
    sudo systemctl restart postgresql
fi                                    #DOCS:
#
# Finally, we need to add two postgres users: one for the user that does
# the import and another for the webserver which should access the database
# for reading only:
#

    sudo -u postgres createuser -s $USERNAME
    sudo -u postgres createuser www-data

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
    git clone --recursive https://github.com/openstreetmap/Nominatim.git
    cd Nominatim
else                               #DOCS:
    cd $USERHOME/Nominatim         #DOCS:
fi                                 #DOCS:

# When installing the latest source from github, you also need to
# download the country grid:

if [ ! -f data/country_osm_grid.sql.gz ]; then       #DOCS:    :::sh
    wget -O data/country_osm_grid.sql.gz https://nominatim.org/data/country_grid.sql.gz
fi                                 #DOCS:

# The code must be built in a separate directory. Create this directory,
# then configure and build Nominatim in there:

    mkdir $USERHOME/build
    cd $USERHOME/build
    cmake $USERHOME/Nominatim
    make
    sudo make install

# Nominatim is now ready to use. You can continue with
# [importing a database from OSM data](../admin/Import.md). If you want to set up
# a webserver first, continue reading.
#
# Setting up a webserver
# ======================
#
# The webserver should serve the php scripts from the website directory of your
# [project directory](../admin/Import.md#creating-the-project-directory).
# This directory needs to exist when being configured.
# Therefore set up a project directory and create a website directory:

    mkdir $USERHOME/nominatim-project
    mkdir $USERHOME/nominatim-project/website

# The import process will populate the directory later.

#
# Option 1: Using Apache
# ----------------------
#
if [ "x$2" == "xinstall-apache" ]; then #DOCS:
#
# Apache has a PHP module that can be used to serve Nominatim. To install them
# run:

    sudo apt install -y apache2 libapache2-mod-php

# You need to create an alias to the website directory in your apache
# configuration. Add a separate nominatim configuration to your webserver:

#DOCS:```sh
sudo tee /etc/apache2/conf-available/nominatim.conf << EOFAPACHECONF
<Directory "$USERHOME/nominatim-project/website">
  Options FollowSymLinks MultiViews
  AddType text/html   .php
  DirectoryIndex search.php
  Require all granted
</Directory>

Alias /nominatim $USERHOME/nominatim-project/website
EOFAPACHECONF
#DOCS:```

#
# Then enable the configuration and restart apache
#

    sudo a2enconf nominatim
if [ "x$NOSYSTEMD" == "xyes" ]; then  #DOCS:
    sudo apache2ctl start             #DOCS:
else                                  #DOCS:
    sudo systemctl restart apache2
fi                                    #DOCS:

# The Nominatim API is now available at `http://localhost/nominatim/`.

fi   #DOCS:

#
# Option 2: Using nginx
# ---------------------
#
if [ "x$2" == "xinstall-nginx" ]; then #DOCS:

# Nginx has no native support for php scripts. You need to set up php-fpm for
# this purpose. First install nginx and php-fpm:

    sudo apt install -y nginx php-fpm

# You need to configure php-fpm to listen on a Unix socket.

#DOCS:```sh
sudo tee /etc/php/8.1/fpm/pool.d/www.conf << EOF_PHP_FPM_CONF
[www]
; Replace the tcp listener and add the unix socket
listen = /var/run/php-fpm-nominatim.sock

; Ensure that the daemon runs as the correct user
listen.owner = www-data
listen.group = www-data
listen.mode = 0666

; Unix user of FPM processes
user = www-data
group = www-data

; Choose process manager type (static, dynamic, ondemand)
pm = ondemand
pm.max_children = 5
EOF_PHP_FPM_CONF
#DOCS:```

# Then create a Nginx configuration to forward http requests to that socket.

#DOCS:```sh
sudo tee /etc/nginx/sites-available/default << EOF_NGINX_CONF
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root $USERHOME/nominatim-project/website;
    index search.php index.html;
    location / {
        try_files \$uri \$uri/ @php;
    }

    location @php {
        fastcgi_param SCRIPT_FILENAME "\$document_root\$uri.php";
        fastcgi_param PATH_TRANSLATED "\$document_root\$uri.php";
        fastcgi_param QUERY_STRING    \$args;
        fastcgi_pass unix:/var/run/php-fpm-nominatim.sock;
        fastcgi_index index.php;
        include fastcgi_params;
    }

    location ~ [^/]\.php(/|$) {
        fastcgi_split_path_info ^(.+?\.php)(/.*)$;
        if (!-f \$document_root\$fastcgi_script_name) {
            return 404;
        }
        fastcgi_pass unix:/var/run/php-fpm-nominatim.sock;
        fastcgi_index search.php;
        include fastcgi.conf;
    }
}
EOF_NGINX_CONF
#DOCS:```

# If you have some errors, make sure that php-fpm-nominatim.sock is well under
# /var/run/ and not under /var/run/php. Otherwise change the Nginx configuration
# to /var/run/php/php-fpm-nominatim.sock.
#
# Enable the configuration and restart Nginx
#

if [ "x$NOSYSTEMD" == "xyes" ]; then  #DOCS:
    sudo /usr/sbin/php-fpm8.1 --nodaemonize --fpm-config /etc/php/8.1/fpm/php-fpm.conf & #DOCS:
    sudo /usr/sbin/nginx &            #DOCS:
else                                  #DOCS:
    sudo systemctl restart php8.1-fpm nginx
fi                                    #DOCS:

# The Nominatim API is now available at `http://localhost/`.



fi   #DOCS:
