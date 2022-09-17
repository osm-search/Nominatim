# Install Nominatim in a virtual machine for development and testing

This document describes how you can install Nominatim inside a Ubuntu 16
virtual machine on your desktop/laptop (host machine). The goal is to give
you a development environment to easily edit code and run the test suite
without affecting the rest of your system. 

The installation can run largely unsupervised. You should expect 1h from
start to finish depending on how fast your computer and download speed
is.

## Prerequisites

1. [Virtualbox](https://www.virtualbox.org/wiki/Downloads)

2. [Vagrant](https://www.vagrantup.com/downloads.html)

3. Nominatim 

        git clone --recursive https://github.com/openstreetmap/Nominatim.git

    If you forgot `--recursive`, it you can later load the submodules using
    
        git submodule init
        git submodule update



## Installation

1. Start the virtual machine

        vagrant up ubuntu

2. Log into the virtual machine

        vagrant ssh ubuntu

3. Import a small country (Monaco)
    
    See the FAQ how to skip this step and point Nominatim to an existing database.

      ```
      # inside the virtual machine:
      cd nominatim-project
      wget --no-verbose --output-document=monaco.osm.pbf http://download.geofabrik.de/europe/monaco-latest.osm.pbf
      nominatim import --osm-file monaco.osm.pbf 2>&1 | tee monaco.$$.log
      ```

    To repeat an import you'd need to delete the database first

        dropdb --if-exists nominatim



## Development

Vagrant maps the virtual machine's port 8089 to your host machine. Thus you can
see Nominatim in action on [localhost:8089](http://localhost:8089/nominatim/).

You edit code on your host machine in any editor you like. There is no need to
restart any software: just refresh your browser window.

Note that the webserver uses files from the /build directory. If you change
files in Nominatim/website or Nominatim/utils for example you first need to
copy them into the /build directory by running the `cmake` step from the
installation.

PHP errors are written to `/var/log/apache2/error.log`.

With `echo` and `var_dump()` you write into the output (HTML/XML/JSON) when
you either add `&debug=1` to the URL (preferred) or set
`@define('CONST_Debug', true);` in `settings/local.php`.

In the Python BDD test you can use `logger.info()` for temporary debug
statements.



## Running unit tests

    cd ~/Nominatim/tests/php
    phpunit ./


## Running PHP code style tests

    cd ~/Nominatim
    phpcs --colors .


## Running functional tests

Tests in `test/bdd/db` and `test/bdd/osm2pgsql` have to pass 100%. Other
tests might require full planet-wide data. Sadly even if you have your own
planet-wide data there will be enough differences to the openstreetmap.org
installation to cause false positives in the other tests (see FAQ). 

To run the full test suite

    cd ~/Nominatim/test/bdd
    behave -DBUILDDIR=/home/vagrant/build/ db osm2pgsql

To run a single file

    behave -DBUILDDIR=/home/vagrant/build/ api/lookup/simple.feature

Or a single test by line number

    behave -DBUILDDIR=/home/vagrant/build/ api/lookup/simple.feature:34
    
To run specific groups of tests you can add tags just before the `Scenario line`, e.g.

    @bug-34
    Scenario: address lookup for non-existing or invalid node, way, relation

and then

    behave -DBUILDDIR=/home/vagrant/build/ --tags @bug-34






## FAQ

##### Will it run on Windows?

Yes, Vagrant and Virtualbox can be installed on MS Windows just fine. You need a 64bit
version of Windows.


##### Why Monaco, can I use another country?

Of course! The Monaco import takes less than 30 minutes and works with 2GB RAM.

##### Will the results be the same as those from nominatim.openstreetmap.org?

No. Long running Nominatim installations will differ once new import features (or
bug fixes) get added since those usually only get applied to new/changed data.

Also this document skips the optional Wikipedia data import which affects ranking
of search results. See [Nominatim installation](https://nominatim.org/release-docs/latest/admin/Installation) for details.

##### Why Ubuntu? Can I test CentOS/Fedora/CoreOS/FreeBSD?

There is a Vagrant script for CentOS available, but the Nominatim directory
isn't symlinked/mounted to the host which makes development trickier. We used
it mainly for debugging installation with SELinux.

In general Nominatim will run in the other environments. The installation steps
are slightly different, e.g. the name of the package manager, Apache2 package
name, location of files. We chose Ubuntu because that is closest to the
nominatim.openstreetmap.org production environment.

You can configure/download other Vagrant boxes from [https://app.vagrantup.com/boxes/search](https://app.vagrantup.com/boxes/search).

##### How can I connect to an existing database?

Let's say you have a Postgres database named `nominatim_it` on server `your-server.com` and port `5432`. The Postgres username is `postgres`. You can edit `settings/local.php` and point Nominatim to it.

    pgsql:host=your-server.com;port=5432;user=postgres;dbname=nominatim_it
    
No data import or restarting necessary.

If the Postgres installation is behind a firewall, you can try

    ssh -L 9999:localhost:5432 your-username@your-server.com

inside the virtual machine. It will map the port to `localhost:9999` and then
you edit `settings/local.php` with

    @define('CONST_Database_DSN', 'pgsql:host=localhost;port=9999;user=postgres;dbname=nominatim_it');

To access postgres directly remember to specify the hostname, e.g. `psql --host localhost --port 9999 nominatim_it`


##### My computer is slow and the import takes too long. Can I start the virtual machine "in the cloud"?

Yes. It's possible to start the virtual machine on [Amazon AWS (plugin)](https://github.com/mitchellh/vagrant-aws)
or [DigitalOcean (plugin)](https://github.com/smdahlen/vagrant-digitalocean).




