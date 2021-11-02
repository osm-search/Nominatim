#!/bin/bash -ex
#
# *Note:* these installation instructions are also available in executable
#         form for use with vagrant under `vagrant/Install-on-Centos-8.sh`.
#
# Installing the Required Software
# ================================
#
# These instructions expect that you have a freshly installed CentOS version 8.
# Make sure all packages are up-to-date by running:
#
    sudo dnf update -y

# The standard CentOS repositories don't contain all the required packages,
# you need to enable the EPEL repository as well. For example for SELinux
# related redhat-hardened-cc1 package. To enable it on CentOS run:

    sudo dnf install -y epel-release redhat-rpm-config

# EPEL contains Postgres 9.6 and 10, but not PostGIS. Postgres 9.4+/10/11/12
# and PostGIS 2.4/2.5/3.0 are availble from postgresql.org. Enable these
# repositories and make sure, the binaries can be found:

    sudo dnf -qy module disable postgresql
    sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
    export PATH=/usr/pgsql-12/bin:$PATH

# Now you can install all packages needed for Nominatim:

#DOCS:    :::sh
    sudo dnf --enablerepo=powertools install -y postgresql12-server \
                        postgresql12-contrib postgresql12-devel postgis30_12 \
                        wget cmake make gcc gcc-c++ libtool policycoreutils-python-utils \
                        llvm-toolset ccache clang-tools-extra \
                        php-pgsql php php-intl php-json libpq-devel \
                        bzip2-devel proj-devel boost-devel \
                        python3-pip python3-setuptools python3-devel \
                        python3-psycopg2 \
                        expat-devel zlib-devel libicu-devel

    pip3 install --user python-dotenv psutil Jinja2 PyICU datrie pyyaml


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
#     sudo useradd -d /srv/nominatim -s /bin/bash -m nominatim
#
# You may find a more suitable location if you wish.
#
# To be able to copy and paste instructions from this manual, export
# user name and home directory now like this:
#
if [ "x$USERNAME" == "x" ]; then       #DOCS:
    export USERNAME=vagrant            #DOCS:    export USERNAME=nominatim
    export USERHOME=/srv/nominatim
    sudo mkdir -p /srv/nominatim       #DOCS:
    sudo chown vagrant /srv/nominatim  #DOCS:
fi                                     #DOCS:
#
# **Never, ever run the installation as a root user.** You have been warned.
#
# Make sure that system servers can read from the home directory:

    chmod a+x $USERHOME

# Setting up PostgreSQL
# ---------------------
#
# CentOS does not automatically create a database cluster. Therefore, start
# with initializing the database:

if [ "x$NOSYSTEMD" == "xyes" ]; then                               #DOCS:
    sudo -u postgres /usr/pgsql-12/bin/pg_ctl initdb -D /var/lib/pgsql/12/data     #DOCS:
    sudo mkdir /var/log/postgresql                                 #DOCS:
    sudo chown postgres. /var/log/postgresql                       #DOCS:
else                                                               #DOCS:
    sudo /usr/pgsql-12/bin/postgresql-12-setup initdb
fi                                                                 #DOCS:
#
# Next tune the postgresql configuration, which is located in
# `/var/lib/pgsql/12/data/postgresql.conf`. See section *Postgres Tuning* in
# [the installation page](../admin/Installation.md#postgresql-tuning)
# for the parameters to change.
#
# Now start the postgresql service after updating this config file:

if [ "x$NOSYSTEMD" == "xyes" ]; then  #DOCS:
    sudo -u postgres /usr/pgsql-12/bin/pg_ctl -D /var/lib/pgsql/12/data -l /var/log/postgresql/postgresql-12.log start  #DOCS:
else                                  #DOCS:
    sudo systemctl enable postgresql-12
    sudo systemctl restart postgresql-12
fi                                    #DOCS:

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
# Get the source code from Github and change into the source directory
#
if [ "x$1" == "xyes" ]; then  #DOCS:    :::sh
    cd $USERHOME
    wget https://nominatim.org/release/Nominatim-4.0.0.tar.bz2
    tar xf Nominatim-4.0.0.tar.bz2
else                               #DOCS:
    cd $USERHOME/Nominatim         #DOCS:
fi                                 #DOCS:

# The code must be built in a separate directory. Create this directory,
# then configure and build Nominatim in there:

#DOCS:    :::sh
    mkdir $USERHOME/build
    cd $USERHOME/build
    cmake $USERHOME/Nominatim-4.0.0
    make
    sudo make install

#
# Setting up the Apache Webserver
# -------------------------------
#
# The webserver should serve the php scripts from the website directory of your
# [project directory](../admin/Import.md#creating-the-project-directory).
# This directory needs to exist when the webserver is configured.
# Therefore set up a project directory and create the website directory:
#
    mkdir $USERHOME/nominatim-project
    mkdir $USERHOME/nominatim-project/website
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
# Then reload apache:
#

if [ "x$NOSYSTEMD" == "xyes" ]; then  #DOCS:
    sudo httpd                        #DOCS:
else                                  #DOCS:
    sudo systemctl enable httpd
    sudo systemctl restart httpd
fi                                    #DOCS:

#
# Adding SELinux Security Settings
# --------------------------------
#
# It is a good idea to leave SELinux enabled and enforcing, particularly
# with a web server accessible from the Internet. At a minimum the
# following SELinux labeling should be done for Nominatim:

if [ "x$HAVE_SELINUX" != "xno" ]; then  #DOCS:
    sudo semanage fcontext -a -t httpd_sys_content_t "/usr/local/nominatim/lib/lib-php(/.*)?"
    sudo semanage fcontext -a -t httpd_sys_content_t "$USERHOME/nominatim-project/website(/.*)?"
    sudo semanage fcontext -a -t lib_t "$USERHOME/nominatim-project/module/nominatim.so"
    sudo restorecon -R -v /usr/local/lib/nominatim
    sudo restorecon -R -v $USERHOME/nominatim-project
fi                                 #DOCS:

# You need to create a minimal configuration file that tells nominatim
# the name of your webserver user:

#DOCS:```sh
echo NOMINATIM_DATABASE_WEBUSER="apache" | tee $USERHOME/nominatim-project/.env
#DOCS:```


# Nominatim is now ready to use. Continue with
# [importing a database from OSM data](../admin/Import.md).
