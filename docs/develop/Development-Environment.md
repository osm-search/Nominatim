# Setting up Nominatim for Development

This chapter gives an overview how to set up Nominatim for developement
and how to run tests.

!!! Important
    This guide assumes that you develop under the latest version of Ubuntu. You
    can of course also use your favourite distribution. You just might have to
    adapt the commands below slightly, in particular the commands for installing
    additional software.

## Installing Nominatim

The first step is to install Nominatim itself. Please follow the installation
instructions in the [Admin section](../admin/Installation.md). You don't need
to set up a webserver for development, the webserver that is included with PHP
is sufficient.

If you want to run Nominatim in a VM via Vagrant, use the default `ubuntu` setup.
Vagrant's libvirt provider runs out-of-the-box under Ubuntu. You also need to
install an NFS daemon to enable directory sharing between host and guest. The
following packages should get you started:

    sudo apt install vagrant vagrant-libvirt libvirt-daemon nfs-kernel-server

## Prerequisites for testing and documentation

The Nominatim tests suite consists of behavioural tests (using behave) and
unit tests (using PHPUnit). It has the following additional requirements:

* [behave test framework](https://behave.readthedocs.io) >= 1.2.5
* [nose](https://nose.readthedocs.io)
* [phpunit](https://phpunit.de) >= 7.3
* [PHP CodeSniffer](https://github.com/squizlabs/PHP_CodeSniffer)

The documentation is built with mkdocs:

* [mkdocs](https://www.mkdocs.org/) >= 1.1.2

### Installing prerequisites on Ubuntu/Debian

Some of the Python packages require the newest version which is not yet
available with the current distributions. Therefore it is recommended to
install pip to get the newest versions.

To install all necessary packages run:

```sh
sudo apt install php-cgi phpunit php-codesniffer \
                 python3-pip python3-setuptools python3-dev

pip3 install --user behave nose mkdocs
```

The `mkdocs` executable will be located in `.local/bin`. You may have to add
this directory to your path, for example by running:

```
echo 'export PATH=~/.local/bin:$PATH' > ~/.profile
```

If your distribution does not have PHPUnit 7.3+, you can install it (as well
as CodeSniffer) via composer:

```
sudo apt-get install composer
composer global require "squizlabs/php_codesniffer=*"
composer global require "phpunit/phpunit=8.*"
```

The binaries are found in `.config/composer/vendor/bin`. You need to add this
to your PATH as well:

```
echo 'export PATH=~/.config/composer/vendor/bin:$PATH' > ~/.profile
```


## Executing Tests

All tests are located in the `\test` directory.

### Preparing the test database

Some of the behavioural test expect a test database to be present. You need at
least 2GB RAM and 10GB disk space to create the database.

First create a separate directory for the test DB and Fetch the test planet
data and the Tiger data for South Dakota:

```
mkdir testdb
cd testdb
wget https://www.nominatim.org/data/test/nominatim-api-testdata.pbf
wget -O - https://nominatim.org/data/tiger2018-nominatim-preprocessed.tar.gz | tar xz --wildcards --no-anchored '46*'
```

Configure and build Nominatim in the usual way:

```
cmake $USERNAME/Nominatim
make
```

Copy the test settings:

```
cp $USERNAME/Nominatim/test/testdb/local.php settings/
```

Inspect the file to check that all settings are correct for your local setup.

Now you can import the test database:

```
dropdb --if-exists test_api_nominatim
./utils/setup.php --all --osm-file nominatim-api-testdb.pbf 2>&1 | tee import.log
./utils/specialphrases.php --wiki-import | psql -d test_api_nominatim 2>&1 | tee -a import.log
./utils/setup.php --import-tiger-data 2>&1 | tee -a import.log
```

### Running the tests

To run all tests just go to the test directory and run make:

```sh
cd test
make
```

To skip tests that require the test database, run `make no-test-db` instead.

For more information about the structure of the tests and how to change and
extend the test suite, see the [Testing chapter](Testing.md).

## Documentation Pages

The [Nominatim documentation](https://nominatim.org/release-docs/develop/) is
built using the [MkDocs](https://www.mkdocs.org/) static site generation
framework. The master branch is automatically deployed every night on
[https://nominatim.org/release-docs/develop/](https://nominatim.org/release-docs/develop/)

To build the documentation, go to the build directory and run

```
make doc
INFO - Cleaning site directory
INFO - Building documentation to directory: /home/vagrant/build/site-html
```

This runs `mkdocs build` plus extra transformation of some files and adds
symlinks (see `CMakeLists.txt` for the exact steps).

Now you can start webserver for local testing

```
build> mkdocs serve
[server:296] Serving on http://127.0.0.1:8000
[handlers:62] Start watching changes
```

If you develop inside a Vagrant virtual machine, use a port that is forwarded
to your host:

```
build> mkdocs serve --dev-addr 0.0.0.0:8088
[server:296] Serving on http://0.0.0.0:8088
[handlers:62] Start watching changes
```
