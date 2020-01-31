# Basic Installation

This page contains generic installation instructions for Nominatim and its
prerequisites. There are also step-by-step instructions available for
the following operating systems:

  * [Ubuntu 18.04](../appendix/Install-on-Ubuntu-18.md)
  * [Ubuntu 16.04](../appendix/Install-on-Ubuntu-16.md)
  * [CentOS 7.2](../appendix/Install-on-Centos-7.md)

These OS-specific instructions can also be found in executable form
in the `vagrant/` directory.

Users have created instructions for other frameworks. We haven't tested those
and can't offer support.

  * [Docker](https://github.com/mediagis/nominatim-docker)
  * [Docker on Kubernetes](https://github.com/peter-evans/nominatim-k8s)
  * [Ansible](https://github.com/synthesio/infra-ansible-nominatim)

## Prerequisites

### Software

For compiling:

  * [cmake](https://cmake.org/)
  * [expat](https://libexpat.github.io/)
  * [proj](https://proj.org/)
  * [bzip2](http://www.bzip.org/)
  * [zlib](https://www.zlib.net/)
  * [Boost libraries](https://www.boost.org/), including system and filesystem
  * PostgreSQL client libraries
  * a recent C++ compiler (gcc 5+ or Clang 3.8+)

For running Nominatim:

  * [PostgreSQL](https://www.postgresql.org) (9.3 or later)
  * [PostGIS](https://postgis.org) (2.2 or later)
  * [Python 3](https://www.python.org/)
  * [Psycopg2](https://initd.org/psycopg)
  * [PHP](https://php.net) (7.0 or later)
  * PHP-pgsql
  * PHP-intl (bundled with PHP)
  * a webserver (apache or nginx are recommended)

For running continuous updates:

  * [pyosmium](https://osmcode.org/pyosmium/) (with Python 3)

For running tests:

  * [behave](http://pythonhosted.org/behave/)
  * [nose](https://nose.readthedocs.io)
  * [phpunit](https://phpunit.de)

### Hardware

A minimum of 2GB of RAM is required or installation will fail. For a full
planet import 64GB of RAM or more are strongly recommended. Do not report
out of memory problems if you have less than 64GB RAM.

For a full planet install you will need at least 800GB of hard disk space
(take into account that the OSM database is growing fast). SSD disks
will help considerably to speed up import and queries.

Even on a well configured machine the import of a full planet takes
at least 2 days. Without SSDs 7-8 days are more realistic.

## Setup of the server

### PostgreSQL tuning

You might want to tune your PostgreSQL installation so that the later steps
make best use of your hardware. You should tune the following parameters in
your `postgresql.conf` file.

    shared_buffers = 2GB
    maintenance_work_mem = (10GB)
    autovacuum_work_mem = 2GB
    work_mem = (50MB)
    effective_cache_size = (24GB)
    synchronous_commit = off
    checkpoint_segments = 100 # only for postgresql <= 9.4
    max_wal_size = 1GB # postgresql > 9.4
    checkpoint_timeout = 10min
    checkpoint_completion_target = 0.9

The numbers in brackets behind some parameters seem to work fine for
64GB RAM machine. Adjust to your setup. A higher number for `max_wal_size`
means that PostgreSQL needs to run checkpoints less often but it does require
the additional space on your disk.

Autovacuum must not be switched off because it ensures that the
tables are frequently analysed. If your machine has very little memory,
you might consider setting:

    autovacuum_max_workers = 1

and even reduce `autovacuum_work_mem` further. This will reduce the amount
of memory that autovacuum takes away from the import process.

For the initial import, you should also set:

    fsync = off
    full_page_writes = off

Don't forget to reenable them after the initial import or you risk database
corruption.


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
at `http://localhost/`.


Now continue with [importing the database](Import-and-Update.md).
