# Basic Installation

This page contains generic installation instructions for Nominatim and its
prerequisites. There are also step-by-step instructions available for
the following operating systems:

  * [Ubuntu 22.04](../appendix/Install-on-Ubuntu-22.md)
  * [Ubuntu 20.04](../appendix/Install-on-Ubuntu-20.md)
  * [Ubuntu 18.04](../appendix/Install-on-Ubuntu-18.md)

These OS-specific instructions can also be found in executable form
in the `vagrant/` directory.

Users have created instructions for other frameworks. We haven't tested those
and can't offer support.

  * [Docker](https://github.com/mediagis/nominatim-docker)
  * [Docker on Kubernetes](https://github.com/peter-evans/nominatim-k8s)
  * [Kubernetes with Helm](https://github.com/robjuz/helm-charts/blob/master/charts/nominatim/README.md)
  * [Ansible](https://github.com/synthesio/infra-ansible-nominatim)

## Prerequisites

### Software

!!! Warning
    For larger installations you **must have** PostgreSQL 11+ and PostGIS 3+
    otherwise import and queries will be slow to the point of being unusable.
    Query performance has marked improvements with PostgreSQL 13+ and PostGIS 3.2+.

For compiling:

  * [cmake](https://cmake.org/)
  * [expat](https://libexpat.github.io/)
  * [proj](https://proj.org/)
  * [bzip2](http://www.bzip.org/)
  * [zlib](https://www.zlib.net/)
  * [ICU](http://site.icu-project.org/)
  * [Boost libraries](https://www.boost.org/), including system and filesystem
  * PostgreSQL client libraries
  * a recent C++ compiler (gcc 5+ or Clang 3.8+)

For running Nominatim:

  * [PostgreSQL](https://www.postgresql.org) (9.6+ will work, 11+ strongly recommended)
  * [PostGIS](https://postgis.net) (2.2+ will work, 3.0+ strongly recommended)
  * [Python 3](https://www.python.org/) (3.6+)
  * [Psycopg2](https://www.psycopg.org) (2.7+)
  * [Python Dotenv](https://github.com/theskumar/python-dotenv)
  * [psutil](https://github.com/giampaolo/psutil)
  * [Jinja2](https://palletsprojects.com/p/jinja/)
  * [PyICU](https://pypi.org/project/PyICU/)
  * [PyYaml](https://pyyaml.org/) (5.1+)
  * [datrie](https://github.com/pytries/datrie)
  * [PHP](https://php.net) (7.0 or later)
  * PHP-pgsql
  * PHP-intl (bundled with PHP)
  * PHP-cgi (for running queries from the command line)

For running continuous updates:

  * [pyosmium](https://osmcode.org/pyosmium/)

For running the experimental Python frontend:

  * [SQLAlchemy](https://www.sqlalchemy.org/) (1.4+ with greenlet support)
  * one of the following web frameworks:
    * [falcon](https://falconframework.org/) (3.0+)
    * [sanic](https://sanic.dev)
    * [starlette](https://www.starlette.io/)
  * [uvicorn](https://www.uvicorn.org/) (only with falcon and starlette framworks)

For dependencies for running tests and building documentation, see
the [Development section](../develop/Development-Environment.md).

### Hardware

A minimum of 2GB of RAM is required or installation will fail. For a full
planet import 128GB of RAM or more are strongly recommended. Do not report
out of memory problems if you have less than 64GB RAM.

For a full planet install you will need at least 1TB of hard disk space.
Take into account that the OSM database is growing fast.
Fast disks are essential. Using NVME disks is recommended.

Even on a well configured machine the import of a full planet takes
around 2 days. On traditional spinning disks, 7-8 days are more realistic.

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
    max_wal_size = 1GB
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

Don't forget to re-enable them after the initial import or you risk database
corruption.


## Downloading and building Nominatim

### Downloading the latest release

You can download the [latest release from nominatim.org](https://nominatim.org/downloads/).
The release contains all necessary files. Just unpack it.

### Downloading the latest development version

If you want to install latest development version from github, make sure to
also check out the osm2pgsql subproject:

```
git clone --recursive https://github.com/openstreetmap/Nominatim.git
```

The development version does not include the country grid. Download it separately:

```
wget -O Nominatim/data/country_osm_grid.sql.gz https://nominatim.org/data/country_grid.sql.gz
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
sudo make install
```

!!! warning
    The default installation no longer compiles the PostgreSQL module that
    is needed for the legacy tokenizer from older Nominatim versions. If you
    are upgrading an older database or want to run the
    [legacy tokenizer](../customize/Tokenizers.md#legacy-tokenizer) for
    some other reason, you need to enable the PostgreSQL module via
    cmake: `cmake -DBUILD_MODULE=on ../Nominatim`. To compile the module
    you need to have the server development headers for PostgreSQL installed.
    On Ubuntu/Debian run: `sudo apt install postgresql-server-dev-<postgresql version>`


Nominatim installs itself into `/usr/local` per default. To choose a different
installation directory add `-DCMAKE_INSTALL_PREFIX=<install root>` to the
cmake command. Make sure that the `bin` directory is available in your path
in that case, e.g.

```
export PATH=<install root>/bin:$PATH
```

Now continue with [importing the database](Import.md).
