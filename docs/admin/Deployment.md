# Deploying Nominatim

The Nominatim API is implemented as a PHP application. The `website/` directory
in the project directory contains the configured website. You can serve this
in a production environment with any web server that is capable to run
PHP scripts.

This section gives a quick overview on how to configure Apache and Nginx to
serve Nominatim. It is not meant as a full system administration guide on how
to run a web service. Please refer to the documentation of
[Apache](http://httpd.apache.org/docs/current/) and
[Nginx](https://nginx.org/en/docs/)
for background information on configuring the services.

!!! Note
    Throughout this page, we assume that your Nominatim project directory is
    located in `/srv/nominatim-project` and that you have installed Nominatim
    using the default installation prefix `/usr/local`. If you have put it
    somewhere else, you need to adjust the commands and configuration
    accordingly.

    We further assume that your web server runs as user `www-data`. Older
    versions of CentOS may still use the user name `apache`. You also need
    to adapt the instructions in this case.

## Making the website directory accessible

You need to make sure that the `website` directory is accessible for the
web server user. You can check that the permissions are correct by accessing
on of the php files as the web server user:

``` sh
sudo -u www-data head -n 1 /srv/nominatim-project/website/search.php
```

If this shows a permission error, then you need to adapt the permissions of
each directory in the path so that it is executable for `www-data`.

If you have SELinux enabled, further adjustments may be necessary to give the
web server access. At a minimum the following SELinux labelling should be done
for Nominatim:

``` sh
sudo semanage fcontext -a -t httpd_sys_content_t "/usr/local/nominatim/lib/lib-php(/.*)?"
sudo semanage fcontext -a -t httpd_sys_content_t "/srv/nominatim-project/website(/.*)?"
sudo semanage fcontext -a -t lib_t "/srv/nominatim-project/module/nominatim.so"
sudo restorecon -R -v /usr/local/lib/nominatim
sudo restorecon -R -v /srv/nominatim-project
```

## Nominatim with Apache

### Installing the required packages

With Apache you can use the PHP module to run Nominatim.

Under Ubuntu/Debian install them with:

``` sh
sudo apt install apache2 libapache2-mod-php
```

### Configuring Apache

Make sure your Apache configuration contains the required permissions for the
directory and create an alias:

``` apache
<Directory "/srv/nominatim-project/website">
  Options FollowSymLinks MultiViews
  AddType text/html   .php
  DirectoryIndex search.php
  Require all granted
</Directory>
Alias /nominatim /srv/nominatim-project/website
```

After making changes in the apache config you need to restart apache.
The website should now be available on `http://localhost/nominatim`.

## Nominatim with Nginx

### Installing the required packages

Nginx has no built-in PHP interpreter. You need to use php-fpm as a daemon for
serving PHP cgi.

On Ubuntu/Debian install nginx and php-fpm with:

``` sh
sudo apt install nginx php-fpm
```

### Configure php-fpm and Nginx

By default php-fpm listens on a network socket. If you want it to listen to a
Unix socket instead, change the pool configuration
(`/etc/php/<php version>/fpm/pool.d/www.conf`) as follows:

``` ini
; Replace the tcp listener and add the unix socket
listen = /var/run/php-fpm.sock

; Ensure that the daemon runs as the correct user
listen.owner = www-data
listen.group = www-data
listen.mode = 0666
```

Tell nginx that php files are special and to fastcgi_pass to the php-fpm
unix socket by adding the location definition to the default configuration.

``` nginx
root /srv/nominatim-project/website;
index search.php;
location / {
    try_files $uri $uri/ @php;
}

location @php {
    fastcgi_param SCRIPT_FILENAME "$document_root$uri.php";
    fastcgi_param PATH_TRANSLATED "$document_root$uri.php";
    fastcgi_param QUERY_STRING    $args;
    fastcgi_pass unix:/var/run/php-fpm.sock;
    fastcgi_index index.php;
    include fastcgi_params;
}

location ~ [^/]\.php(/|$) {
    fastcgi_split_path_info ^(.+?\.php)(/.*)$;
    if (!-f $document_root$fastcgi_script_name) {
        return 404;
    }
    fastcgi_pass unix:/var/run/php-fpm.sock;
    fastcgi_index search.php;
    include fastcgi.conf;
}
```

Restart the nginx and php-fpm services and the website should now be available
at `http://localhost/`.

## Nominatim with other webservers

Users have created instructions for other webservers:

* [Caddy](https://github.com/osm-search/Nominatim/discussions/2580)

