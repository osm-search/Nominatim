#!/bin/bash -e
#
# hacks for broken vagrant box      #DOCS:
sudo rm -f /var/lib/dpkg/lock       #DOCS:
export APT_LISTCHANGES_FRONTEND=none #DOCS:
export DEBIAN_FRONTEND=noninteractive #DOCS:

# *Note:* these installation instructions are also available in executable
#         form for use with vagrant under vagrant/Install-on-Ubuntu-20.sh.
#
# Installing the Required Software
# ================================
#
# These instructions expect that you have a freshly installed Ubuntu 20.04.
#
# Make sure all packages are up-to-date by running:
#

    sudo apt-get update -qq

# Now you can install all packages needed for Nominatim:

    sudo apt-get install -y build-essential cmake g++ libboost-dev libboost-system-dev \
                        libboost-filesystem-dev libexpat1-dev zlib1g-dev \
                        libbz2-dev libpq-dev liblua5.3-dev lua5.3 lua-dkjson \
                        nlohmann-json3-dev postgresql-12-postgis-3 \
                        postgresql-contrib-12 postgresql-12-postgis-3-scripts \
                        libicu-dev python3-dotenv \
                        python3-psycopg2 python3-psutil python3-jinja2 python3-pip \
                        python3-icu python3-datrie python3-yaml

# Some of the Python packages that come with Ubuntu 20.04 are too old, so
# install the latest version from pip:

    pip3 install --user sqlalchemy asyncpg


#
# System Configuration
# ====================
#
# The following steps are meant to configure a fresh Ubuntu installation
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
# The following instructions assume you are logged in as this user.
# You can also switch to the user with:
#
#     sudo -u nominatim bash
#
# To be able to copy and paste instructions from this manual, export
# user name and home directory now like this:
#
if [ "x$USERNAME" == "x" ]; then #DOCS:
    export USERNAME=vagrant        #DOCS:    export USERNAME=nominatim
    export USERHOME=/home/vagrant  #DOCS:    export USERHOME=/srv/nominatim
fi                                 #DOCS:
#
# **Never, ever run the installation as a root user.** You have been warned.
#
# Make sure that system servers can read from the home directory:

    chmod a+x $USERHOME

# Setting up PostgreSQL
# ---------------------
#
# Tune the postgresql configuration, which is located in 
# `/etc/postgresql/12/main/postgresql.conf`. See section *Tuning the PostgreSQL database*
# in [the installation page](../admin/Installation.md#tuning-the-postgresql-database)
# for the parameters to change.
#
# Restart the postgresql service after updating this config file.

if [ "x$NOSYSTEMD" == "xyes" ]; then  #DOCS:
    sudo pg_ctlcluster 12 main start  #DOCS:
else                                  #DOCS:
    sudo systemctl restart postgresql
fi                                    #DOCS:
#
# Finally, we need to add two postgres users: one for the user that does
# the import and another for the webserver which should access the database
# for reading only:
#

    sudo -u postgres createuser -s $USERNAME
    sudo -u postgres createuser www-data

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
    wget https://nominatim.org/release/Nominatim-4.4.0.tar.bz2
    tar xf Nominatim-4.4.0.tar.bz2
else                               #DOCS:
    cd $USERHOME/Nominatim         #DOCS:
fi                                 #DOCS:

# The code must be built in a separate directory. Create this directory,
# then configure and build Nominatim in there:

    mkdir $USERHOME/build
    cd $USERHOME/build
    cmake $USERHOME/Nominatim-4.4.0
    make
    sudo make install

# Nominatim is now ready to use. You can continue with
# [importing a database from OSM data](../admin/Import.md). If you want to set up
# the API frontend first, continue reading.
#
# Setting up the Python frontend
# ==============================
#
# Some of the Python packages in Ubuntu are too old. Therefore run the
# frontend from a Python virtualenv with current packages.
#
# To set up the virtualenv, run:

#DOCS:```sh
sudo apt-get install -y virtualenv
virtualenv $USERHOME/nominatim-venv
$USERHOME/nominatim-venv/bin/pip install SQLAlchemy PyICU psycopg[binary] \
              psycopg2-binary python-dotenv PyYAML falcon uvicorn gunicorn
#DOCS:```

# Next you need to create a systemd job that runs Nominatim on gunicorn.
# First create a systemd job that manages the socket file:

#DOCS:```sh
sudo tee /etc/systemd/system/nominatim.socket << EOFSOCKETSYSTEMD
[Unit]
Description=Gunicorn socket for Nominatim

[Socket]
ListenStream=/run/nominatim.sock
SocketUser=www-data

[Install]
WantedBy=multi-user.target
EOFSOCKETSYSTEMD
#DOCS:```

# Then create the service for Nominatim itself.

#DOCS:```sh
sudo tee /etc/systemd/system/nominatim.service << EOFNOMINATIMSYSTEMD
[Unit]
Description=Nominatim running as a gunicorn application
After=network.target
Requires=nominatim.socket

[Service]
Type=simple
Environment="PYTHONPATH=/usr/local/lib/nominatim/lib-python/"
User=www-data
Group=www-data
WorkingDirectory=$USERHOME/nominatim-project
ExecStart=$USERHOME/nominatim-venv/bin/gunicorn -b unix:/run/nominatim.sock -w 4 -k uvicorn.workers.UvicornWorker nominatim.server.falcon.server:run_wsgi
ExecReload=/bin/kill -s HUP \$MAINPID
StandardOutput=append:/var/log/gunicorn-nominatim.log
StandardError=inherit
PrivateTmp=true
TimeoutStopSec=5
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOFNOMINATIMSYSTEMD
#DOCS:```

# Activate the services:

if [ "x$NOSYSTEMD" != "xyes" ]; then  #DOCS:
    sudo systemctl daemon-reload
    sudo systemctl enable nominatim.socket
    sudo systemctl start nominatim.socket
    sudo systemctl enable nominatim.service
fi                                    #DOCS:


# Setting up a webserver
# ======================
#
# The webserver is only needed as a proxy between the public interface
# and the gunicorn service.
#
# The frontend will need configuration information from the project
# directory, which will be populated later
# [during the import process](../admin/Import.md#creating-the-project-directory)
# Already create the project directory itself now:


    mkdir $USERHOME/nominatim-project


# Option 1: Using Apache
# ----------------------
#
if [ "x$2" == "xinstall-apache" ]; then #DOCS:
# First install apache itself and enable the proxy module:

    sudo apt-get install -y apache2
    sudo a2enmod proxy_http

# To set up proxying for Apache add the following configuration:

#DOCS:```sh
sudo tee /etc/apache2/conf-available/nominatim.conf << EOFAPACHECONF
ProxyPass /nominatim "unix:/run/nominatim.sock|http://localhost/"
EOFAPACHECONF
#DOCS:```

#
# Then enable the configuration and restart apache
#

    sudo a2enconf nominatim
if [ "x$NOSYSTEMD" == "xyes" ]; then  #DOCS:
    sudo apache2ctl start             #DOCS:
else                                  #DOCS:
    sudo systemctl restart apache2
fi                                    #DOCS:

# The Nominatim API is now available at `http://localhost/nominatim/`.

fi   #DOCS:

#
# Option 2: Using nginx
# ---------------------
#
if [ "x$2" == "xinstall-nginx" ]; then #DOCS:

# First install nginx itself:

    sudo apt-get install -y nginx

# Then create a Nginx configuration to forward http requests to that socket.

#DOCS:```sh
sudo tee /etc/nginx/sites-available/default << EOF_NGINX_CONF
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root $USERHOME/nominatim-project/website;
    index /search;

    location /nominatim/ {
            proxy_set_header Host \$http_host;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_redirect off;
            proxy_pass http://unix:/run/nominatim.sock:/;
    }
}
EOF_NGINX_CONF
#DOCS:```

# Enable the configuration and restart Nginx
#

if [ "x$NOSYSTEMD" == "xyes" ]; then  #DOCS:
    sudo /usr/sbin/nginx &            #DOCS:
else                                  #DOCS:
    sudo systemctl restart nginx
fi                                    #DOCS:

# The Nominatim API is now available at `http://localhost/`.



fi   #DOCS:
