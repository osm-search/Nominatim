#!/bin/bash
#
# hacks for broken vagrant box      #DOCS:
sudo rm -f /var/lib/dpkg/lock       #DOCS:
sudo update-locale LANG=en_US.UTF-8 #DOCS:
export APT_LISTCHANGES_FRONTEND=none #DOCS:
export DEBIAN_FRONTEND=noninteractive #DOCS:

# *Note:* these installation instructions are also available in executable
#         form for use with vagrant under vagrant/Install-on-Ubuntu-20.sh.
#
# Installing the Required Software
# ================================
#
# These instructions expect that you have a freshly installed Ubuntu 20.04.
#
# Make sure all packages are are up-to-date by running:
#

#DOCS:    :::sh
    sudo apt-get \ #DOCS:
        -o DPkg::options::="--force-confdef" -o DPkg::options::="--force-confold" \ #DOCS:
        --allow-downgrades --allow-remove-essential --allow-change-held-packages \ #DOCS:
        -fuy install grub-pc #DOCS:
    sudo apt update -qq

# Now you can install all packages needed for Nominatim:

    sudo apt install -y php-cgi
    sudo apt install -y build-essential cmake g++ libboost-dev libboost-system-dev \
                        libboost-filesystem-dev libexpat1-dev zlib1g-dev \
                        libbz2-dev libpq-dev libproj-dev \
                        postgresql-server-dev-12 postgresql-12-postgis-3 \
                        postgresql-contrib-12 postgresql-12-postgis-3-scripts \
                        php php-pgsql php-intl libicu-dev python3-dotenv \
                        python3-psycopg2 python3-psutil python3-jinja2 python3-icu git \
                        python3-argparse-manpage

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
# `/etc/postgresql/12/main/postgresql.conf`. See section *Postgres Tuning* in
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
# [project directory](../admin/import.md#creating-the-project-directory).
# Therefore set up a project directory and populate the website directory:

    mkdir $USERHOME/nominatim-project
    cd $USERHOME/nominatim-project
    nominatim refresh --website

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
    sudo systemctl restart apache2

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
sudo tee /etc/php/7.4/fpm/pool.d/www.conf << EOF_PHP_FPM_CONF
[www]
; Replace the tcp listener and add the unix socket
listen = /var/run/php7.4-fpm.sock

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
        fastcgi_pass unix:/var/run/php7.4-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
    }

    location ~ [^/]\.php(/|$) {
        fastcgi_split_path_info ^(.+?\.php)(/.*)$;
        if (!-f \$document_root\$fastcgi_script_name) {
            return 404;
        }
        fastcgi_pass unix:/var/run/php7.4-fpm.sock;
        fastcgi_index search.php;
        include fastcgi.conf;
    }
}
EOF_NGINX_CONF
#DOCS:```

#
# Enable the configuration and restart Nginx
#

    sudo systemctl restart php7.4-fpm nginx

# The Nominatim API is now available at `http://localhost/`.



fi   #DOCS:
