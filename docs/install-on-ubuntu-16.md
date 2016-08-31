




*Note:* these installation instructions are also available in executable
        form for use with vagrant under vagrant/install-on-ubuntu-16.sh.

Installing the Required Software
================================

These instructions expect that you have a freshly installed Ubuntu 16.04.

Make sure all packages are are up-to-date by running:


    sudo apt-get update -qq
    sudo apt-get upgrade -y

Now you can install all packages needed for Nominatim:

    sudo apt-get install -y build-essential cmake g++ libboost-dev libboost-system-dev \
                            libboost-filesystem-dev libexpat1-dev zlib1g-dev libxml2-dev\
                            libbz2-dev libpq-dev libgeos-dev libgeos++-dev libproj-dev \
                            postgresql-server-dev-9.5 postgresql-9.5-postgis-2.2 postgresql-contrib-9.5 \
                            apache2 php php-pgsql libapache2-mod-php php-pear php-db \
                            git

If you want to run the test suite, you need to install the following
additional packages:

    sudo apt-get install -y python-dev python-pip python-levenshtein python-shapely \
                            python-psycopg2 tidy python-nose python-tidylib \
                            phpunit

    pip install --user lettuce==0.2.18 six==1.7 haversine


System Configuration
====================

The following steps are meant to configure a fresh Ubuntu installation
for use with Nominatim. You may skip some of the steps if you have your
OS already configured.

Creating Dedicated User Accounts
--------------------------------

Nominatim will run as a global service on your machine. It is therefore
best to install it under its own separate user account. In the following
we assume this user is called nominatim and the installation will be in
/srv/nominatim. To create the user and directory run:

    sudo useradd -d /srv/nominatim -s /bin/bash -m nominatim

You may find a more suitable location if you wish.

To be able to copy and paste instructions from this manual, export
user name and home directory now like this:

    export USERNAME=nominatim
    export USERHOME=/srv/nominatim

**Never, ever run the installation as a root user.** You have been warned.

Make sure that system servers can read from the home directory:

    sudo chmod a+x $USERHOME

Setting up PostgreSQL
---------------------

Tune the postgresql configuration, which is located in 
`/etc/postgresql/9.5/main/postgresql.conf`. See section *Postgres Tuning* in
[the installation page](Installation.md) for the parameters to change.

Restart the postgresql service after updating this config file.

    sudo systemctl restart postgresql


Finally, we need to add two postgres users: one for the user that does
the import and another for the webserver which should access the database
for reading only:


    sudo -u postgres createuser -s $USERNAME
    sudo -u postgres createuser www-data


Setting up the Apache Webserver
-------------------------------

You need to create an alias to the website directory in your apache
configuration. Add a separate nominatim configuration to your webserver:

```
sudo tee /etc/apache2/conf-available/nominatim.conf << EOFAPACHECONF
<Directory "$USERHOME/Nominatim/build/website">
  Options FollowSymLinks MultiViews
  AddType text/html   .php
  Require all granted
</Directory>

Alias /nominatim $USERHOME/Nominatim/build/website
EOFAPACHECONF
```




Then enable the configuration and restart apache


    sudo a2enconf nominatim
    sudo systemctl restart apache2


Installing Nominatim
====================

Building and Configuration
--------------------------

Get the source code from Github and change into the source directory



    cd $USERHOME
    git clone --recursive git://github.com/twain47/Nominatim.git
    cd Nominatim





The code must be built in a separate directory. Create this directory,
then configure and build Nominatim in there:

    mkdir build
    cd build
    cmake $USERHOME/Nominatim
    make

You need to create a minimal configuration file that tells nominatim
where it is located on the webserver:

```
tee settings/local.php << EOF
<?php
 @define('CONST_Website_BaseURL', '/nominatim/');
EOF
```


Nominatim is now ready to use. Continue with
[importing a database from OSM data](Import_and_update.md).
