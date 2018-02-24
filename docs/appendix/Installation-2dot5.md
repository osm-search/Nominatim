# Nominatim 2.5 installation


**These installation instructions are for the old 2.5.x stable release only.**

**For installation instructions for the current release see http://nominatim.org/release-docs/latest/admin/Installation**

This page describes the general installation process for [Nominatim](http://github.com/openstreetmap/Nominatim). It is assumed that you are familiar with basic system and database administration.

## Prerequisites

### Software

* [GCC compiler](http://gcc.gnu.org/)  
* [PostgreSQL](http://www.postgresql.org/) (9.0 or later)
* [Proj4](http://trac.osgeo.org/proj/)		
* [GEOS](http://trac.osgeo.org/geos/)		
* [PostGIS](http://postgis.refractions.net/) (1.5 or later)
* [PHP5](http://php.net/) (both apache and command line)
* PHP-pgsql
* [PEAR::DB](http://pear.php.net/package/DB)
* wget
* [boost](http://www.boost.org) (1.48 or later)
* [osmosis](http://wiki.openstreetmap.org/wiki/Osmosis)

#### Ubuntu/Debian

In standard Debian/Ubuntu distributions all dependencies should be available as packages.

Ubuntu / Debian 7:

	sudo apt-get install build-essential libxml2-dev libpq-dev libbz2-dev \
	libtool automake libproj-dev libboost-dev libboost-system-dev \
	libboost-filesystem-dev libboost-thread-dev libexpat-dev gcc \
	proj-bin libgeos-c1 libgeos++-dev libexpat-dev php5 php-pear \
	php5-pgsql php5-json php-db libapache2-mod-php5 postgresql \
	postgis postgresql-contrib postgresql-9.3-postgis-2.1 \
	postgresql-server-dev-9.3 wget

Debian 8:

	sudo apt-get install build-essential libxml2-dev libpq-dev libbz2-dev \
	libtool automake libproj-dev libboost-dev libboost-system-dev \
	libboost-filesystem-dev libboost-thread-dev libexpat-dev gcc \
	proj-bin libgeos-c1 libgeos++-dev libexpat-dev php5 php-pear \
	php5-pgsql php5-json php-db libapache2-mod-php5 postgresql \
	postgis postgresql-contrib postgresql-9.4-postgis-2.1 \
	postgresql-server-dev-9.4 wget

Ubuntu 16.04:

	sudo apt-get install build-essential libxml2-dev libpq-dev libbz2-dev \
	libtool automake libproj-dev libboost-dev libboost-system-dev \
	libboost-filesystem-dev libboost-thread-dev libexpat1-dev gcc \
	proj-bin libgeos-c1v5 libgeos++-dev php php-pear php-pgsql \
	php-json php-db libapache2-mod-php postgresql postgis \
	postgresql-contrib postgresql-9.5-postgis-2.2 \
	postgresql-server-dev-9.5 wget

Note that you must install php5, **php7 does not work**.


You may have a different postgres version, adapt the package names as required.

#### CentOS

**Follow the detailed step-by-step installation instructions for CentOS available at [Installation-2dot5-centos](Nominatim 2.5 CentOS)**.

#### PostgreSQL Tuning

You might want to tune your PostgreSQL installation so that the later steps make best use of your hardware. You should tune the following parameters in your `postgresql.conf` file.

Ubuntu location `/etc/postgresql/9.x/main/postgresql.conf`

CentOS location `/var/lib/pgsql/data/postgresql.conf`

	* shared_buffers (2GB)
	* maintenance_work_mem (10GB)
	* work_mem (50MB)
	* effective_cache_size (24GB)
	* synchronous_commit = off
	* checkpoint_segments = 100 (only for PostgreSQL <= 9.4)
	* checkpoint_timeout = 10min
	* checkpoint_completion_target = 0.9

The numbers in brackets behind some parameters seem to work fine for 32GB RAM machine. Adjust to your setup.

For the initial import, you should also set:

	* fsync = off
	* full_page_writes = off

Don't forget to reenable them after the initial import or you risk database corruption.

Autovacuum must not be switched off because it ensures that the tables are frequently analysed.

### Hardware

A minimum of 2GB of RAM is required or installation will fail. For a full planet import 32GB or more are recommended.

For a full planet install you will need about 800GB of hard disk space (as of January 2016, take into account that the OSM database is growing fast). SSD disks will help considerably to speed up import and queries.

On [pummelzacken](https://hardware.openstreetmap.org/servers/pummelzacken.openstreetmap.org/) the complete initial import requires around 2 days.
On a 12-core machine with 32GB RAM and standard SATA disks, the initial import (osm2pgsql) takes around 20 hours and the indexing process another 250 hours. Only 8 parallel threads were used for this setup because I/O speed was the limiting factor. The same machine is able to import the Germany extract in around 4 hours.

## First Installation

It is important to run the installation steps as a normal (non-root) user. Even in docker containers, create a normal user and use it. PostgreSQL commands as listed here will not work otherwise.

### Downloading Nominatim

Download the latest stable release and unpack it:

	wget http://www.nominatim.org/release/Nominatim-2.5.1.tar.bz2
	tar xvf Nominatim-2.5.1.tar.bz2

### Compiling Nominatim

To compile the sources, run

	cd Nominatim-2.5.1
	./configure
	make

The warning about missing lua libraries can be ignored. Nominatim does not make use of osm2pgsql's lua extension.

### Customization of the Installation

You can customize Nominatim by creating a local configuration file `settings/local.php`. Have a look at `settings/settings.php` for available configuration settings. 

Here is an example of a `local.php`:

	<?php
	// Paths
	@define('CONST_Postgresql_Version', '9.3');
	@define('CONST_Postgis_Version', '2.1');
	 
	// Website settings
	@define('CONST_Website_BaseURL', 'http://mysite/nominatim/');

The website setting should be adapted to your host. If you plan to import a large dataset (e.g. Europe, North America, planet), you should also enable flatnode storage of node locations. This saves node coordinates in a simple file instead of the database and saves both on import time and disk storage. Add to your `settings/local.php`:

	@define('CONST_Osm2pgsql_Flatnode_File', '/path/to/flatnode.file');

### Download (optional) data

#### Wikipedia rankings

Wikipedia can be used as an optional auxiliary data source to help indicate the importance of osm features.  Nominatim will work without this information but it will improve the quality of the results if this is installed.  This data is available as a binary download.

	wget --output-document=data/wikipedia_article.sql.bin http://www.nominatim.org/data/wikipedia_article.sql.bin
	wget --output-document=data/wikipedia_redirect.sql.bin http://www.nominatim.org/data/wikipedia_redirect.sql.bin

Combined the 2 files are around 1.5GB and add around 30GB to the install size of nominatim.  They also increase the install time by an hour or so.

#### UK postcodes

Nominatim can use postcodes from an external source to improve searches that involve a UK postcode. This data can be optionally downloaded:

	wget --output-document=data/gb_postcode_data.sql.gz http://www.nominatim.org/data/gb_postcode_data.sql.gz

### Creating postgres accounts

#### Creating the importer account

The import needs to be done with a postgres superuser with the same name as the account doing the import. 
You can create such a postgres superuser account by running:

 sudo -u postgres createuser -s <your user name>

Where <your user name> is the name of the account that will be used to perform the installation.  You should ensure that this user can log in to the database without requiring a password (e.g. using ident authentication).  This is the default on most distributions.  See [trust authentication](http://www.postgresql.org/docs/9.1/static/auth-methods.html) for more information.

**You must not run the import as user www-data or root.**

#### Create website user

Create the website user www-data as a PostgreSQL database role

	createuser -SDR www-data

For the installation process, you must have this user. If you want to run the website under another user, see comment in section /Set up the website/.

### Nominatim module reading permissions

Some Nominatim Postgres functions are implemented in the nominatim.so C module that was compiled in one of the earlier steps. In order for these functions to be successfully created, PostgreSQL server process has to be able to read the module file.
Make sure that directory and file permissions allow the file to be read. For example, if you downloaded and compiled Nominatim in your home directory, you will need to issue the following commands:

	chmod +x ~/src
	chmod +x ~/src/Nominatim
	chmod +x ~/src/Nominatim/module

### Import and index OSM data

First download a [Planet File](https://wiki.openstreetmap.org/wiki/Planet.osm) or a planet extract, for example from [Geofabrik](http://download.geofabrik.de/openstreetmap/) ([how to merge multiple extracts](https://help.openstreetmap.org/questions/48843/merging-two-or-more-geographical-areas-to-import-two-or-more-osm-files-in-nominatim)). Using a file in PBF format is recommended.

The import can take a long time, so you probably want to do it inside of a `screen` [session](http://www.tecmint.com/screen-command-examples-to-manage-linux-terminals/ session). Now start the import:

	./utils/setup.php --osm-file <your planet file> --all [--osm2pgsql-cache 18000] 2>&1 | tee setup.log

The `--osm2pgsql-cache` parameter is optional but strongly recommended for planet imports. It sets the node cache size for the osm2pgsql import part (see -C parameter in osm2pgsql help). 24GB are recommended for a full planet import, for excerpts you can use less. Adapt to your available RAM to avoid swapping.

The import will take as little as an hour for a small country extract and as much as 10 days for a full-scale planet import.
It produces a lot of log messages, which you should carefully examine. The last part of the command ensures that all output is logged into a file. *Make sure that you have this log file ready when asking for support for the installation.*

*We recommend running an import of a small osm/pdf file (e.g. [Luxembourg](http://download.geofabrik.de/europe/luxembourg.html)) before attempting a full planet import to verify that everything is working.*

If something goes wrong, you might need to clean up by dropping the database since the script will fail when trying to recreate an already existing database. Use this command to do this: `sudo -u postgres dropdb nominatim`

### Add special phrases

Add country codes and country names to the search index:

	./utils/specialphrases.php --countries > data/specialphrases_countries.sql
	psql -d nominatim -f data/specialphrases_countries.sql

If you want to be able to search for special amenities like ''pubs in Dublin'', you need to import special phrases from this wiki like this:

	./utils/specialphrases.php --wiki-import > data/specialphrases.sql
	psql -d nominatim -f data/specialphrases.sql

This may be repeated from time to time when there are changes in the wiki. There is no need to repeat it after each update.

If you do not need phrases for all languages, edit `settings/phrase_settings.php` and delete unneeded languages at the beginning of the file.

### Set up the website

*The following instructions will make Nominatim available at `http://localhost/nominatim`.*

Create the directory for the website and make sure it is writable by the install user and readable by Apache:

	sudo mkdir -m 755 <Apache document root>/nominatim
	sudo chown <your username> <Apache document root>/nominatim

Populate the website directory with the necessary symlinks:

	./utils/setup.php --create-website <Apache document root>/nominatim

You will need to make sure settings/local.php is configured with correct values for `CONST_Website_BaseURL`. see above.

#### Configure for use with Apache

Make sure your Apache configuration contains the following settings for the directory:

	<Directory "/var/www/nominatim/">
	    Options FollowSymLinks MultiViews
	    AddType text/html   .php     
	</Directory>

`/var/www/nominatim/` should be replaced with the directory where you have set up the Nominatim website in the step above.

After making changes in the apache config you need to restart apache.

#### Configure for use with Nginx

Install nginx and php-fpm as server-side, HTML-embedded scripting language (FPM-CGI binary) that runs as a daemon and receives Fast/CGI requests passed from nginx.

	Ubuntu# apt-get install nginx php5-fpm
	CentOS# yum install nginx php-fpm

If you want to change the daemon to listen on unix socket instead configure the pool listener  (`/etc/php5/fpm/pool.d/www.conf` in a standard Ubuntu/Debian installation)

	; Comment out the tcp listener and add the unix socket
	;listen = 127.0.0.1:9000
	listen = /var/run/php5-fpm.sock

&nbsp;

	: Ensure that the daemon runs as the correct user
	listen.owner = www-data
	listen.group = www-data
	listen.mode = 0666

Tell nginx that php files are special and to `fastcgi_pass` to the php-fpm unix socket by adding the location definition to the default configuration.  (`/etc/nginx/sites-available/default` in a standard Ubuntu/Debian installation)

	location ~ [^/]\.php(/|$) {
	    fastcgi_split_path_info ^(.+?\.php)(/.*)$;
	    if (!-f $document_root$fastcgi_script_name) {
	        return 404;
	    }
	    fastcgi_pass unix:/var/run/php5-fpm.sock;
	    fastcgi_index index.php;
	    include fastcgi_params;
	}

Note: If you are using Debian 8.1/Jesse or newer, you would have to change `include fastcgi_params;` to "`include fastcgi.conf;` in the above configuration code. Refer [here](http://www.pedaldrivenprogramming.com/2015/04/upgrading-wheezy-to-jessie:-nginx-and-php-fpm/) for more details.

Restart the nginx and php5-fpm services and view your home brew Nominatim indexed OpenStreetMap with your favourite browser.

## Updates


There are many different possibilities to update your Nominatim database. The following section describes how to keep it up-to-date with osmosis. For a list of other methods see the output of `./utils/update.php --help`.

### Installing the newest version of osmosis

Get the latest version of osmosis from 

Then tell Nominatim to use this version by adding the following line to your `settings/local.php`:

	@define('CONST_Osmosis_Binary', '/usr/local/bin/osmosis');

### Setting up the update process

Next the update needs to be initialised. By default nominatim is configured to update using the global minutely diffs.

If you want a different update source you will need to add some settings to settings/local.php. For example, to use the daily country extracts diffs for Ireland from geofabrik add the following:

	@define('CONST_Replication_Url', 'http://download.geofabrik.de/europe/ireland-and-northern-ireland-updates');
	@define('CONST_Replication_MaxInterval', '40000');     // Process each update separately, osmosis cannot merge multiple updates
	@define('CONST_Replication_Update_Interval', '86400');  // How often upstream publishes diffs
	@define('CONST_Replication_Recheck_Interval', '900');   // How long to sleep if no update found yet


First you have to delete existing 'configuration.txt' then run the following command to create the osmosis configuration files:

	./utils/setup.php --osmosis-init

### Enabling hierarchical updates

When a place is updated in the database, all places that contain this place in their address need to be updated as well. These hierarchical updates are disabled by default because they slow down the initial import. Enable them with the following command:

	./utils/setup.php --create-functions --enable-diff-updates

### Updating Nominatim

The following command will keep your database constantly up to date:

	./utils/update.php --import-osmosis-all --no-npi

If you have imported multiple country extracts and want to keep them up to date, have a look at the script in [this issue](https://github.com/twain47/Nominatim/issues/60).

### Installing Tiger housenumber data for the US

In the US, the OSM instance of Nominatim uses TIGER address data to complement the still sparse OSM house number data. You can add TIGER data to your own Nominatim instance by following these steps:

* Install the GDAL library and python bindings

	* Ubuntu: `apt-get install python-gdal`
	* CentOS: `yum install gdal-python`

* Get the [TIGER 2015 data](https://www.census.gov/geo/maps-data/data/tiger-geodatabases.html). You will need the EDGES files (3,234 zip files, 11GB total)

```
	wget -r ftp://ftp2.census.gov/geo/tiger/TIGER2015/EDGES/
```

* Convert the data into SQL statements (stored in data/tiger): 

```
	./utils/imports.php --parse-tiger <tiger edge data directory>
```
* Import the data into your Nominatim database: 

```
  ./utils/setup.php --import-tiger-data
```

Be warned that the import can take a very long time, especially if you are importing all of the US.

## Troubleshooting

For frequently encountered errors during the installation see [Troubleshooting](https://wiki.openstreetmap.org/wiki/Nominatim/Installation/Troubleshooting).

