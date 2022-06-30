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

The Nominatim test suite consists of behavioural tests (using behave) and
unit tests (using PHPUnit for PHP code and pytest for Python code).
It has the following additional requirements:

* [behave test framework](https://behave.readthedocs.io) >= 1.2.6
* [phpunit](https://phpunit.de) (9.5 is known to work)
* [PHP CodeSniffer](https://github.com/squizlabs/PHP_CodeSniffer)
* [Pylint](https://pylint.org/) (CI always runs the latest version from pip)
* [mypy](http://mypy-lang.org/) (plus typing information for external libs)
* [pytest](https://pytest.org)

The documentation is built with mkdocs:

* [mkdocs](https://www.mkdocs.org/) >= 1.1.2
* [mkdocstrings](https://mkdocstrings.github.io/)

### Installing prerequisites on Ubuntu/Debian

Some of the Python packages require the newest version which is not yet
available with the current distributions. Therefore it is recommended to
install pip to get the newest versions.

To install all necessary packages run:

```sh
sudo apt install php-cgi phpunit php-codesniffer \
                 python3-pip python3-setuptools python3-dev

pip3 install --user behave mkdocs mkdocstrings pytest \
                    pylint mypy types-PyYAML types-jinja2 types-psycopg2
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

All tests are located in the `/test` directory.

To run all tests just go to the build directory and run make:

```sh
cd build
make test
```

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
build> make serve-doc
[server:296] Serving on http://127.0.0.1:8000
[handlers:62] Start watching changes
```

If you develop inside a Vagrant virtual machine, use a port that is forwarded
to your host:

```
build> PYTHONPATH=$SRCDIR mkdocs serve --dev-addr 0.0.0.0:8088
[server:296] Serving on http://0.0.0.0:8088
[handlers:62] Start watching changes
```
