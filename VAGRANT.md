# Install Nominatim in a virtual machine for development and testing

This document describes how you can install Nominatim inside a Ubuntu 14
virtual machine on your desktop/laptop (host machine). The goal is to give
you a development environment to easily edit code and run the test suite
without affecting the rest of your system. 

The installation can run largely unsupervised. You should expect 1-2h from
start to finish depending on how fast your computer and download speed
is.

## Prerequisites

1. [Virtualbox](https://www.virtualbox.org/wiki/Downloads)

2. [Vagrant](https://www.vagrantup.com/downloads.html)

3. Nominatim 

        git clone --recursive https://github.com/twain47/Nominatim.git

    If you haven't used `--recursive`, then you can load the submodules using
    
        git submodule init
        git submodule update



## Installation

1. Start the virtual machine

        vagrant up

2. Log into the virtual machine

        vagrant ssh

3. Import a small country (Monaco)

    You need to give the virtual machine more memory (2GB) for an import, see `Vagrantfile`.
    
    See the FAQ how to skip this step and point Nominatim to an existing database.

    # inside the virtual machine:
    cd Nominatim
        wget --no-verbose --output-document=data/monaco.osm.pbf http://download.geofabrik.de/europe/monaco-latest.osm.pbf
        utils/setup.php --osm-file data/monaco.osm.pbf --osm2pgsql-cache 1000 --all | tee monaco.$$.log
        ./utils/specialphrases.php --countries > data/specialphrases_countries.sql
        psql -d nominatim -f data/specialphrases_countries.sql

  To repeat an import you'd need to delete the database first

        psql postgres -c "DROP DATABASE IF EXISTS nominatim"



## Development

Vagrant maps the virtual machine's port 8089 to your host machine. Thus you can
see Nominatim in action on [locahost:8089](http://localhost:8089/nominatim/).

You edit code on your host machine in any editor you like. There is no need to
restart any software: just refresh your browser window.

In `settings/local.php` you can add `@define('CONST_Debug', false);` which will
print all the `echo` and `var_dump()` calls you see in the PHP code.

PHP errors are written to `/var/log/apache2/error.log`.



## Running functional tests

The full test suite requires planet-wide data. Sadly even if you have your own
planet-wide data there will be enough differences to the openstreetmap.org
installation to cause false positives (see FAQ).

To run the full test suite

    cd ~/Nominatim/tests
    NOMINATIM_SERVER=http://localhost:8089/nominatim lettuce features

To run a single file

    NOMINATIM_SERVER=http://localhost:8089/nominatim lettuce features/api/reverse.feature
    
To run specific tests you can add tags just before the 'Scenario line`, e.g.

    @bug-34
    Scenario: address lookup for non-existing or invalid node, way, relation

and then

    NOMINATIM_SERVER=http://localhost:8089/nominatim lettuce -t bug-34


## Running unit tests

    cd ~/Nominatim/tests
    phpunit



http://localhost:8089/nominatim/




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
of search results. See [Nominatim instllation](http://wiki.openstreetmap.org/wiki/Nominatim/Installation) for details.

##### Why Ubuntu, can I test CentOS/CoreOS/FreeBSD?

In general Nominatim will run in all these environment. The installation steps
are slightly different, e.g. the name of the package manager, Apache2 package
name, location of files. We chose Ubuntu because that is closest to the
nominatim.openstreetmap.org production environment.

You can configure/download other Vagrant boxes from [vagrantbox.es](http://www.vagrantbox.es/).


##### How can I connect to an existing database?

Let's say you have a Postgres database named `nominatim_it` on server `your-server.com` and port `5432`. The Postgres username is `postgres`. You can edit `settings/local.php` and point Nominatim to it.

    pgsql://postgres@your-server.com:5432/nominatim_it
    
No data import necessary, no restarting necessary.

If the Postgres installation is behind a firewall, you can try

    ssh -L 9999:localhost:5432 your-username@your-server.com

inside the virtual machine. It will map the port to `localhost:9999` and then
you edit `settings/local.php` with

    pgsql://postgres@localhost:9999/nominatim_it


##### My computer is slow and the import takes too long. Can I start the virtual machine "in the cloud"?

Yes. It's possible to start the virtual machine on [Amazon AWS (plugin)](https://github.com/mitchellh/vagrant-aws) or [DigitalOcean (plugin)](https://github.com/smdahlen/vagrant-digitalocean).




