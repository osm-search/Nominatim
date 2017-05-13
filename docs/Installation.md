Nominatim installation
======================

This page contains generic installation instructions for Nominatim and its
prerequisites. There are also step-by-step instructions available for
the following operating systems:

  * [Ubuntu 16.04](install-on-ubuntu-16.md)
  * [CentOS 7.2](install-on-centos-7.md)

These OS-specific instructions can also be found in executable form
in the `vagrant/` directory.

Prerequisites
-------------

### Software

For compiling:

  * [cmake](https://cmake.org/)
  * [libxml2](http://xmlsoft.org/)
  * a recent C++ compiler

Nominatim comes with its own version of osm2pgsql. See the
[osm2pgsql README](../osm2pgsql/README.md) for additional dependencies
required for compiling osm2pgsql.

For running tests:

  * [behave](http://pythonhosted.org/behave/)
  * [Psycopg2](http://initd.org/psycopg)
  * [nose](https://nose.readthedocs.io)
  * [phpunit](https://phpunit.de)

For running Nominatim:

  * [PostgreSQL](http://www.postgresql.org) (9.1 or later)
  * [PostGIS](http://postgis.refractions.net) (2.0 or later)
  * [PHP](http://php.net) (5.4 or later)
  * PHP-pgsql
  * [PEAR::DB](http://pear.php.net/package/DB)
  * a webserver (apache or nginx are recommended)

For running continuous updates:

  * [osmosis](http://wiki.openstreetmap.org/wiki/Osmosis)

### Hardware

A minimum of 2GB of RAM is required or installation will fail. For a full
planet import 32GB of RAM or more strongly are recommended.

For a full planet install you will need about 500GB of hard disk space (as of
June 2016, take into account that the OSM database is growing fast). SSD disks
will help considerably to speed up import and queries.

On a 6-core machine with 32GB RAM and SSDs the import of a full planet takes
a bit more than 2 days. Without SSDs 7-8 days are more realistic.


Setup of the server
-------------------

### PostgreSQL tuning

You might want to tune your PostgreSQL installation so that the later steps
make best use of your hardware. You should tune the following parameters in
your `postgresql.conf` file.

    shared_buffers (2GB)
    maintenance_work_mem (10GB)
    work_mem (50MB)
    effective_cache_size (24GB)
    synchronous_commit = off
    checkpoint_segments = 100 # only for postgresql <= 9.4
    checkpoint_timeout = 10min
    checkpoint_completion_target = 0.9

The numbers in brackets behind some parameters seem to work fine for
32GB RAM machine. Adjust to your setup.

For the initial import, you should also set:

    fsync = off
    full_page_writes = off

Don't forget to reenable them after the initial import or you risk database
corruption. Autovacuum must not be switched off because it ensures that the
tables are frequently analysed.

### Webserver setup

The `website/` directory in the build directory contains the configured
website. Include the directory into your webbrowser to serve php files
from there.

#### Configure for use with Apache

Make sure your Apache configuration contains the required permissions for the
directory and create an alias:

    <Directory "/srv/nominatim/build/website">
      Options FollowSymLinks MultiViews
      AddType text/html   .php
      DirectoryIndex search.php
      Require all granted
    </Directory>
    Alias /nominatim /srv/nominatim/build/website

`/srv/nominatim/build` should be replaced with the location of your
build directory.

After making changes in the apache config you need to restart apache.
The website should now be available on http://localhost/nominatim.

#### Configure for use with Nginx

Use php-fpm as a deamon for serving PHP cgi. Install php-fpm together with nginx.

By default php listens on a network socket. If you want it to listen to a
Unix socket instead, change the pool configuration (`pool.d/www.conf`) as
follows:

    ; Comment out the tcp listener and add the unix socket
    ;listen = 127.0.0.1:9000
    listen = /var/run/php5-fpm.sock

    ; Ensure that the daemon runs as the correct user
    listen.owner = www-data
    listen.group = www-data
    listen.mode = 0666

Tell nginx that php files are special and to fastcgi_pass to the php-fpm
unix socket by adding the location definition to the default configuration.

    root /srv/nominatim/build/website;
    index search.php index.html;
    location ~ [^/]\.php(/|$) {
        fastcgi_split_path_info ^(.+?\.php)(/.*)$;
        if (!-f $document_root$fastcgi_script_name) {
            return 404;
        }
        fastcgi_pass unix:/var/run/php5-fpm.sock;
        fastcgi_index search.php;
        include fastcgi.conf;
    }

Restart the nginx and php5-fpm services and the website should now be available
on http://localhost/.


Now continue with [importing the database](Import_and_update.md).
