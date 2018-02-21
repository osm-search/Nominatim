# Nominatim 2.5 installation on CentOS

**These installation instructions are for the old 2.5.x stable release only.**

**For installation instructions for the current release see http://nominatim.org/release-docs/latest/admin/Installation**

This page contains detailed installation instructions for Nominatim on CentOS v7 which has all the required software readily available. CentOS v7 includes PostgreSQL v9.2 and EPEL contains PostGIS v2.0, so there isn't any extra effort required for obtaining new enough software.

## Installing the OS

First, perform a minimal install of CentOS v7, and apply all updates. Keep in mind that you'll need enough disk space under `/var/lib/pgsql/` as well as potentially 10s of GiBs of space under `/srv`.

## Installing the Required Software

### Setting up Repositories

The standard CentOS repositories don't contain all the required packages, you need to enable the [EPEL repository](https://fedoraproject.org/wiki/EPEL) as well. To enable it on CentOS, install the `epel-release` RPM which is itself now included in the base CentOS repository by running:
 
  yum install epel-release

### Getting the Software Packages

Now you can install all packages needed for Nominatim:

  yum install postgresql-server postgresql-contrib postgresql-devel postgis postgis-utils
  yum install git make automake gcc gcc-c++ libtool policycoreutils-python
  yum install php-pgsql php php-pear php-pear-DB libpqxx-devel proj-epsg
  yum install bzip2-devel proj-devel geos-devel libxml2-devel boost-devel expat-devel zlib-devel

## Setting up PostgreSQL

### Starting the Server

Now initialize the database, enable the server to start at boot, and launch PostgreSQL:

  postgresql-setup initdb
  systemctl enable postgresql
  systemctl start postgresql

### Configuring Postgresql

Next tune the postgresql configuration, which is located in `/var/lib/pgsql/data/postgresql.conf`. See [Nominatim 2.5 installation ("PostgreSQL Tuning" section)](Installation-2dot5) for the parameters to change.  You will need to restart the postgresql service after updating this config file.

  systemctl restart postgresql

## Installing Nominatim

Nominatim will run as a global service on your machine. It is therefore best to install it under its own separate user account. In the following we assume this user is called `nominatim` and the installation will be in `/srv`. You may find a more suitable location if you wish.

**Never, ever do the following installation as root user.** You have been warned.

### Downloading and Compiling the Sources

Get the current stable version and unpack it:

  cd /srv
  wget http://www.nominatim.org/release/Nominatim-2.5.1.tar.bz2
  tar xvf Nominatim-2.5.1.tar.bz2

Now configure and compile taking into account the special location of postgresql:

  cd Nominatim-2.5.1
  ./configure
  make

The warning about missing lua libraries can be ignored. Nominatim does not make use of osm2pgsql's lua extension.

### Configuring the Software

You can customize the installation by adding a localized `settings/local.php`. You need to add at least the follow:

  <?php
    // General settings
    @define('CONST_Database_Web_User', 'apache');
    // Paths
    @define('CONST_Postgresql_Version', '9.2');
    @define('CONST_Postgis_Version', '2.0');
    // Website settings
    @define('CONST_Website_BaseURL', 'http://'.php_uname('n').'/nominatim/');

The website setting should be adapted to your host. If you plan to import a large dataset (e.g. Europe, North America, planet), you should also enable flatnode storage of node locations. This saves node coordinates in a simple file instead of the database and saves both on import time and disk storage. Add to your settings/local.php:

    @define('CONST_Osm2pgsql_Flatnode_File', '/path/to/flatnode.file');

More settings can be found in `settings/settings.php`.

### Adding SELinux Security Settings

It's a good idea to leave SELinux enabled and enforcing, particularly with a web server accessible from the Internet. At a minimum the following SELinux labeling should be done for Nominatim:

  su - root
  semanage fcontext -a -t httpd_sys_content_t "/srv/Nominatim/(website|lib|settings)(/.*)?"
  semanage fcontext -a -t lib_t "/srv/Nominatim/module/nominatim.so"
  restorecon -R -v /srv/Nominatim

### Downloading additional data

The following data is optional but download is strongly recommended:

  wget --output-document=data/wikipedia_article.sql.bin http://www.nominatim.org/data/wikipedia_article.sql.bin
  wget --output-document=data/wikipedia_redirect.sql.bin http://www.nominatim.org/data/wikipedia_redirect.sql.bin
  wget --output-document=data/gb_postcode_data.sql.gz http://www.nominatim.org/data/gb_postcode_data.sql.gz

### Creating Postgresql user accounts

Nominatim requires two postgresql accounts, one for the user importing the database and one for the apache webserver. These can be created as follows:

  sudo -u postgres createuser -s nominatim
  sudo -u postgres createuser apache

## Initial Import of the Data

### Loading OSM Data

**Attention:** first try the import with a small excerpt, for example from [Geofabrik](http://download.geofabrik.de/openstreetmap/).

Download the data to import and load the data with the following command:

  ./utils/setup.php --osm-file <your data file> --all [--osm2pgsql-cache 24000] 2>&1 | tee setup.log

The `--osm2pgsql-cache` parameter is optional but strongly recommended for planet imports. It sets the node cache size for the osm2pgsql import part (see -C parameter in osm2pgsql help). 24GB are recommended for a full planet import, for excerpts you can use less. Adapt to your available RAM to avoid swapping.

The import will take as little as an hour for a small country extract and as much as 10 days for a full-scale planet import on less powerful hardware.

### Loading Additional Datasets

The following commands will create additional entries for countries and POI searches:

  ./utils/specialphrases.php --countries > data/specialphrases_countries.sql
  psql -d nominatim -f data/specialphrases_countries.sql
  ./utils/specialphrases.php --wiki-import > data/specialphrases.sql
  psql -d nominatim -f data/specialphrases.sql

## Setting up the Website

Create the directory for the website and make sure it is writable by you and readable by apache:

  mkdir -m 755 /var/www/html/nominatim
  sudo chown <your username> /var/www/html/nominatim

Populate the website directory with the necessary symlinks:

  ./utils/setup.php --create-website /var/www/html/nominatim

### Configuring for Use with Apache

Edit the Apache configuration at `/etc/httpd/conf.d/nominatim.conf`
and add the following:

  <Directory "/var/www/html/nominatim/">
    Options FollowSymLinks MultiViews
    AddType text/html   .php     
  </Directory>

After making changes in the apache config you need to restart apache.

  systemctl enable httpd
  systemctl restart httpd

Now you should be able to see the Nominatim website at [http://localhost/nominatim](http://localhost/nominatim).

For further instructions on setting up updates and for troubleshooting see the [Nominatim 2.5 installation](Installation-2dot5) page.
