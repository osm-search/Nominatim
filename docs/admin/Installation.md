# Basic Installation

This page contains generic installation instructions for Nominatim and its
prerequisites. There are also step-by-step instructions available for
the following operating systems:

  * [Ubuntu 20.04](../appendix/Install-on-Ubuntu-20.md)
  * [Ubuntu 18.04](../appendix/Install-on-Ubuntu-18.md)
  * [CentOS 8](../appendix/Install-on-Centos-8.md)
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

  * [PostgreSQL](https://www.postgresql.org) (9.3+)
  * [PostGIS](https://postgis.net) (2.2+)
  * [Python 3](https://www.python.org/)
  * [Psycopg2](https://www.psycopg.org)
  * [PHP](https://php.net) (7.0 or later)
  * PHP-pgsql
  * PHP-intl (bundled with PHP)

For running continuous updates:

  * [pyosmium](https://osmcode.org/pyosmium/) (with Python 3)

For dependencies for running tests and building documentation, see
the [Development section](../develop/Development-Environment.md).

### Hardware

A minimum of 2GB of RAM is required or installation will fail. For a full
planet import 64GB of RAM or more are strongly recommended. Do not report
out of memory problems if you have less than 64GB RAM.

For a full planet install you will need at least 800GB of hard disk space
(take into account that the OSM database is growing fast). SSD disks
will help considerably to speed up import and queries.

Even on a well configured machine the import of a full planet takes
at least 2 days. Without SSDs 7-8 days are more realistic.

## Tuning the PostgreSQL database

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


## Downloading and building Nominatim

### Downloading the latest release

You can download the [latest release from nominatim.org](https://nominatim.org/downloads/).
The release contains all necessary files. Just unpack it.

### Downloading the latest development version

If you want to install latest development version from github, make sure to
also check out the osm2pgsql subproject:

```
git clone --recursive git://github.com/openstreetmap/Nominatim.git
```

The development version does not include the country grid. Download it separately:

```
wget -O Nominatim/data/country_osm_grid.sql.gz https://www.nominatim.org/data/country_grid.sql.gz
```

### Building Nominatim

The code must be built in a separate directory. Create the directory and
change into it.

```
mkdir build
cd build
```

Nominatim uses cmake and make for building. Assuming that you have created the
build at the same level as the Nominatim source directory run:

```
cmake ../Nominatim
make
```

Now continue with [importing the database](Import.md).
