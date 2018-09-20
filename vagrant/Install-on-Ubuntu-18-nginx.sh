#!/bin/bash

#
# This is variation of Install-on-Ubuntu.sh showcasing how to use the
# nginx webserver instead of Apache2. We might eventually merge both
# files. Right now expect this file to become outdated/unmaintained
# over time.
#
# This file lacks many comments found in Install-on-Ubuntu.sh, you
# should check that file first to get a basic understanding.
#

# hacks for broken vagrant box
sudo rm -f /var/lib/dpkg/lock
sudo update-locale LANG=en_US.UTF-8
export APT_LISTCHANGES_FRONTEND=none
export DEBIAN_FRONTEND=noninteractive

    sudo apt-get update -qq
    sudo apt-get install -y build-essential cmake g++ libboost-dev libboost-system-dev \
                            libboost-filesystem-dev libexpat1-dev zlib1g-dev libxml2-dev\
                            libbz2-dev libpq-dev libproj-dev \
                            postgresql-server-dev-10 postgresql-10-postgis-2.4 \
                            postgresql-contrib-10 \
                            nginx php-fpm php php-pgsql php-pear php-db \
                            php-intl git

    export USERNAME=vagrant
    export USERHOME=/home/vagrant

    chmod a+x $USERHOME

# Setting up PostgreSQL
# ---------------------
#
# Tune the postgresql configuration, see same section in Install-on-Ubuntu.sh

    sudo systemctl restart postgresql

    sudo -u postgres createuser -s $USERNAME
    sudo -u postgres createuser www-data

#
# Setting up the Nginx Webserver
# -------------------------------
#
# You need to configure php-fpm to listen on a Unix socket. Then create Nginx
# configuration to forward localhost:80 requests to that socket.
#


sudo tee /etc/php/7.2/fpm/pool.d/www.conf << EOF_PHP_FPM_CONF
[www]
; Comment out the tcp listener and add the unix socket
;listen = 127.0.0.1:9000
listen = /var/run/php7.2-fpm.sock

; Ensure that the daemon runs as the correct user
listen.owner = www-data
listen.group = www-data
listen.mode = 0666

; Unix user of FPM processes
user = www-data
group = www-data

; Choose process manager type (static, dynamic, ondemand)
pm = ondemand
pm.max_children = 5
EOF_PHP_FPM_CONF




sudo tee /etc/nginx/sites-available/default << EOF_NGINX_CONF
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root $USERHOME/build/website;
    index search.php index.html;
    location / {
        try_files \$uri \$uri/ @php;
    }

    location @php {
        fastcgi_param SCRIPT_FILENAME "\$document_root\$uri.php";
        fastcgi_param PATH_TRANSLATED "\$document_root\$uri.php";
        fastcgi_param QUERY_STRING    \$args;
        fastcgi_pass unix:/var/run/php/php7.2-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
    }

    location ~ [^/]\.php(/|$) {
        fastcgi_split_path_info ^(.+?\.php)(/.*)$;
        if (!-f \$document_root\$fastcgi_script_name) {
            return 404;
        }
        fastcgi_pass unix:/var/run/php7.2-fpm.sock;
        fastcgi_index search.php;
        include fastcgi.conf;
    }
}
EOF_NGINX_CONF


sudo sed -i 's:#.*::' /etc/nginx/sites-available/default


#
# Enable the configuration and restart Nginx
#

    sudo systemctl stop apache2 # just in case it's installed as well
    sudo systemctl restart php7.2-fpm nginx

# From here continue in the 'Installing Nominatim' section in
# Install-on-Ubuntu.sh

