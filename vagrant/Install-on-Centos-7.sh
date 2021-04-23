#!/bin/bash
#
# *Note:* these installation instructions are also available in executable
#         form for use with vagrant under `vagrant/Install-on-Centos-7.sh`.
#
# Installing the Required Software
# ================================
#
# These instructions expect that you have a freshly installed CentOS version 7.
# Make sure all packages are up-to-date by running:
#
    sudo yum update -y

# The standard CentOS repositories don't contain all the required packages,
# you need to enable the EPEL repository as well. To enable it on CentOS,
# install the epel-release RPM by running:

    sudo yum install -y epel-release

# More repositories for postgresql 11 (CentOS default 'postgresql' is 9.2), postgis
# and llvm-toolset (https://github.com/theory/pg-semver/issues/35)

    sudo yum install -y https://download.postgresql.org/pub/repos/yum/11/redhat/rhel-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
    sudo yum install -y centos-release-scl-rh

# More repositories for PHP 7 (default is PHP 5.4)

    sudo yum install -y http://rpms.remirepo.net/enterprise/remi-release-7.rpm
    sudo yum-config-manager --enable remi-php72
    sudo yum update -y

# Now you can install all packages needed for Nominatim:

#DOCS:    :::sh

    sudo yum install -y postgresql11-server postgresql11-contrib postgresql11-devel \
                        postgis25_11 postgis25_11-utils \
                        wget git cmake make gcc gcc-c++ libtool policycoreutils-python \
                        devtoolset-7 llvm-toolset-7 \
                        php-pgsql php php-intl libpqxx-devel \
                        proj-epsg bzip2-devel proj-devel boost-devel \
                        python3-pip python3-setuptools python3-devel \
                        expat-devel zlib-devel libicu-dev

    pip3 install --user psycopg2 python-dotenv psutil Jinja2 PyICU


#
# System Configuration
# ====================
#
# The following steps are meant to configure a fresh CentOS installation
# for use with Nominatim. You may skip some of the steps if you have your
# OS already configured.
#
# Creating Dedicated User Accounts
# --------------------------------
#
# Nominatim will run as a global service on your machine. It is therefore
# best to install it under its own separate user account. In the following
# we assume this user is called nominatim and the installation will be in
# /srv/nominatim. To create the user and directory run:
#
sudo mkdir -p /srv/nominatim       #DOCS:    sudo useradd -d /srv/nominatim -s /bin/bash -m nominatim
sudo chown vagrant /srv/nominatim  #DOCS:
#
# You may find a more suitable location if you wish.
#
# To be able to copy and paste instructions from this manual, export
# user name and home directory now like this:
#
    export USERNAME=vagrant        #DOCS:    export USERNAME=nominatim
    export USERHOME=/srv/nominatim
#
# **Never, ever run the installation as a root user.** You have been warned.
#
# Make sure that system servers can read from the home directory:

    chmod a+x $USERHOME

# Setting up PostgreSQL
# ---------------------
#
# CentOS does not automatically create a database cluster. Therefore, start
# with initializing the database, then enable the server to start at boot:

    sudo /usr/pgsql-11/bin/postgresql-11-setup initdb
    sudo systemctl enable postgresql-11

#
# Next tune the postgresql configuration, which is located in 
# `/var/lib/pgsql/data/postgresql.conf`. See section *Postgres Tuning* in
# [the installation page](../admin/Installation.md#postgresql-tuning)
# for the parameters to change.
#
# Now start the postgresql service after updating this config file.

    sudo systemctl restart postgresql-11

#
# Finally, we need to add two postgres users: one for the user that does
# the import and another for the webserver which should access the database
# only for reading:
#

    sudo -u postgres createuser -s $USERNAME
    sudo -u postgres createuser apache

#
# Installing Nominatim
# ====================
#
# Building and Configuration
# --------------------------
#
# Get the source for the release and unpack it
#
if [ "x$1" == "xyes" ]; then  #DOCS:    :::sh
    wget https://nominatim.org/release/Nominatim-3.7.0.tar.bz2
    tar xf Nominatim-3.7.0.tar.bz2
else                               #DOCS:
    cd $USERHOME/Nominatim         #DOCS:
fi                                 #DOCS:

# The code must be built in a separate directory. Create this directory,
# then configure and build Nominatim in there:

#DOCS:    :::sh
    mkdir $USERHOME/build
    cd $USERHOME/build
    cmake $USERHOME/Nominatim-3.7.0
    make
    sudo make install

#
# Setting up the Apache Webserver
# -------------------------------
#
# The webserver should serve the php scripts from the website directory of your
# [project directory](../admin/Import.md#creating-the-project-directory).
# Therefore set up a project directory and populate the website directory:
#
    mkdir $USERHOME/nominatim-project
    cd $USERHOME/nominatim-project
    nominatim refresh --website
#
# You need to create an alias to the website directory in your apache
# configuration. Add a separate nominatim configuration to your webserver:

#DOCS:```sh
sudo tee /etc/httpd/conf.d/nominatim.conf << EOFAPACHECONF
<Directory "$USERHOME/nominatim-project/website">
  Options FollowSymLinks MultiViews
  AddType text/html   .php
  DirectoryIndex search.php
  Require all granted
</Directory>

Alias /nominatim $USERHOME/nominatim-project/website
EOFAPACHECONF
#DOCS:```

sudo sed -i 's:#.*::' /etc/httpd/conf.d/nominatim.conf #DOCS:

#
# Then reload apache
#

    sudo systemctl enable httpd
    sudo systemctl restart httpd

#
# Adding SELinux Security Settings
# --------------------------------
#
# It is a good idea to leave SELinux enabled and enforcing, particularly
# with a web server accessible from the Internet. At a minimum the
# following SELinux labeling should be done for Nominatim:

    sudo semanage fcontext -a -t httpd_sys_content_t "/usr/local/nominatim/lib/lib-php(/.*)?"
    sudo semanage fcontext -a -t httpd_sys_content_t "$USERHOME/nominatim-project/website(/.*)?"
    sudo semanage fcontext -a -t lib_t "$USERHOME/nominatim-project/module/nominatim.so"
    sudo restorecon -R -v /usr/local/lib/nominatim
    sudo restorecon -R -v $USERHOME/nominatim-project


# You need to create a minimal configuration file that tells nominatim
# the name of your webserver user:

#DOCS:```sh
echo NOMINATIM_DATABASE_WEBUSER="apache" | tee .env
#DOCS:```


# Nominatim is now ready to use. Continue with
# [importing a database from OSM data](../admin/Import.md).
