# Basic Installation

This page contains generic installation instructions for Nominatim and its
prerequisites. There are also step-by-step instructions available for
the following operating systems:

  * [Ubuntu 24.04](Install-on-Ubuntu-24.md)
  * [Ubuntu 22.04](Install-on-Ubuntu-22.md)

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

For running Nominatim:

  * [PostgreSQL](https://www.postgresql.org) (12+ will work, 13+ strongly recommended)
  * [PostGIS](https://postgis.net) (3.0+ will work, 3.2+ strongly recommended)
  * [osm2pgsql](https://osm2pgsql.org) (1.8+)
  * [Python 3](https://www.python.org/) (3.7+)

Furthermore the following Python libraries are required:

  * [Psycopg3](https://www.psycopg.org)
  * [Python Dotenv](https://github.com/theskumar/python-dotenv)
  * [psutil](https://github.com/giampaolo/psutil)
  * [Jinja2](https://palletsprojects.com/p/jinja/)
  * [PyICU](https://pypi.org/project/PyICU/)
  * [PyYaml](https://pyyaml.org/) (5.1+)
  * [datrie](https://github.com/pytries/datrie)

These will be installed automatically when using pip installation.

For running continuous updates:

  * [pyosmium](https://osmcode.org/pyosmium/)

For running the Python frontend:

  * [SQLAlchemy](https://www.sqlalchemy.org/) (1.4.31+ with greenlet support)
  * [asyncpg](https://magicstack.github.io/asyncpg) (0.8+, only when using SQLAlchemy < 2.0)
  * one of the following web frameworks:
    * [falcon](https://falconframework.org/) (3.0+)
    * [starlette](https://www.starlette.io/)
  * [uvicorn](https://www.uvicorn.org/)

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
around 2.5 days. When using traditional SSDs, 4-5 days are more realistic.

## Tuning the PostgreSQL database

You might want to tune your PostgreSQL installation so that the later steps
make best use of your hardware. You should tune the following parameters in
your `postgresql.conf` file.

    shared_buffers = 2GB
    maintenance_work_mem = (10GB)
    autovacuum_work_mem = 2GB
    work_mem = (50MB)
    synchronous_commit = off
    max_wal_size = 1GB
    checkpoint_timeout = 60min
    checkpoint_completion_target = 0.9
    random_page_cost = 1.0
    wal_level = minimal
    max_wal_senders = 0

The numbers in brackets behind some parameters seem to work fine for
128GB RAM machine. Adjust to your setup. A higher number for `max_wal_size`
means that PostgreSQL needs to run checkpoints less often but it does require
the additional space on your disk.

Autovacuum must not be switched off because it ensures that the
tables are frequently analysed. If your machine has very little memory,
you might consider setting:

    autovacuum_max_workers = 1

and even reduce `autovacuum_work_mem` further. This will reduce the amount
of memory that autovacuum takes away from the import process.

## Installing the latest release

Nominatim is easiest installed directly from Pypi. Make sure you have installed
osm2pgsql, PostgreSQL/PostGIS and libICU together with its header files.

Then you can install Nominatim with:

    pip install nominatim-db nominatim-api

## Downloading and building Nominatim

### Downloading the latest release

You can download the [latest release from nominatim.org](https://nominatim.org/downloads/).
The release contains all necessary files. Just unpack it.

### Downloading the latest development version

If you want to install latest development version from github:

```
git clone https://github.com/osm-search/Nominatim.git
```

The development version does not include the country grid. Download it separately:

```
wget -O Nominatim/data/country_osm_grid.sql.gz https://nominatim.org/data/country_grid.sql.gz
```

### Building Nominatim

Nominatim is easiest to run from its own virtual environment. To create one, run:

    sudo apt-get install virtualenv
    virtualenv /srv/nominatim-venv

To install Nominatim directly from the source tree into the virtual environment, run:

    /srv/nominatim-venv/bin/pip install packaging/nominatim-{db,api}


Now continue with [importing the database](Import.md).
