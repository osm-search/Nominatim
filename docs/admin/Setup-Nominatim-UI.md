# Setting up the Nominatim UI

Nominatim is a search API, it does not provide a website interface on its
own. [nominatim-ui](https://github.com/osm-search/nominatim-ui) offers a
small website for testing your setup and inspecting the database content.

This section provides a quick start how to use nominatim-ui with your
installation. For more details, please also have a look at the
[README of nominatim-ui](https://github.com/osm-search/nominatim-ui/blob/master/README.md).

## Installing nominatim-ui

We provide regular releases of nominatim-ui that contain the packaged website.
They do not need any special installation. Just download, configure
and run it. Grab the latest release from
[nominatim-ui's Github release page](https://github.com/osm-search/nominatim-ui/releases)
and unpack it. You can use `nominatim-ui-x.x.x.tar.gz` or `nominatim-ui-x.x.x.zip`.

Next you need to adapt the UI to your installation. Custom settings need to be
put into `dist/theme/config.theme.js`. At a minimum you need to
set `Nominatim_API_Endpoint` to point to your Nominatim installation:

    cd nominatim-ui
    echo "Nominatim_Config.Nominatim_API_Endpoint='https://myserver.org/nominatim/';" > dist/theme/config.theme.js

For the full set of available settings, have a look at `dist/config.defaults.js`.

Then you can just test it locally by spinning up a webserver in the `dist`
directory. For example, with Python:

    cd nominatim-ui/dist
    python3 -m http.server 8765

The website is now available at `http://localhost:8765`.

## Forwarding searches to nominatim-ui

Nominatim used to provide the search interface directly by itself when
`format=html` was requested. For the `/search` endpoint this even used
to be the default.

The following section describes how to set up Apache or nginx, so that your
users are forwarded to nominatim-ui when they go to a URL that formerly presented
the UI.

### Setting up forwarding in Nginx

First of all make nominatim-ui available under `/ui` on your webserver:

``` nginx
server {

    # Here is the Nominatim setup as described in the Installation section

    location /ui/ {
        alias <full path to the nominatim-ui directory>/dist/;
        index index.html;
    }
}
```

Now we need to find out if a URL should be forwarded to the UI. Add the
following `map` commands *outside* the server section:

``` nginx
# Inspect the format parameter in the query arguments. We are interested
# if it is set to html or something else or if it is missing completely.
map $args $format {
    default                  default;
    ~(^|&)format=html(&|$)   html;
    ~(^|&)format=            other;
}

# Determine from the URI and the format parameter above if forwarding is needed.
map $uri/$format $forward_to_ui {
    default               0;  # no forwarding by default
    ~/search.*/default    1;  # Use this line only, if search should go to UI by default.
    ~/reverse.*/html      1;  # Forward API calls that UI supports, when
    ~/status.*/html       1;  #   format=html is explicitly requested.
    ~/search.*/html       1;
    ~/details.*/html      1;
}
```

The `$forward_to_ui` parameter can now be used to conditionally forward the
calls:

``` nginx
location / {
    if ($forward_to_ui) {
        rewrite ^(/[^/.]*) https://$http_host/ui$1.html redirect;
    }

    # proxy_pass commands
}
```

Reload nginx and the UI should be available.

### Setting up forwarding in Apache

First of all make nominatim-ui available in the `ui/` subdirectory where
Nominatim is installed. For example, given you have set up an alias under
`nominatim` like this:

``` apache
Alias /nominatim /home/vagrant/build/website
```

you need to insert the following rules for nominatim-ui before that alias:

```
<Directory "/home/vagrant/nominatim-ui/dist">
  DirectoryIndex search.html
  Require all granted
</Directory>

Alias /nominatim/ui /home/vagrant/nominatim-ui/dist
```

Replace `/home/vagrant/nominatim-ui` with the directory where you have cloned
nominatim-ui.

!!! important
    The alias for nominatim-ui must come before the alias for the Nominatim
    website directory.

To set up forwarding, the Apache rewrite module is needed. Enable it with:

``` sh
sudo a2enmod rewrite
```

Then add rewrite rules to the `Directory` directive of the Nominatim website
directory like this:

``` apache
<Directory "/home/vagrant/build/website">
  Options FollowSymLinks MultiViews
  AddType text/html   .php
  Require all granted

  RewriteEngine On

  # This must correspond to the URL where nominatim can be found.
  RewriteBase "/nominatim/"

  # If no endpoint is given, then use search.
  RewriteRule ^(/|$)   "search"

  # If format-html is explicitly requested, forward to the UI.
  RewriteCond %{QUERY_STRING} "format=html"
  RewriteRule ^([^/.]+) ui/$1.html [R,END]

  # Optionally: if no format parameter is there then forward /search.
  RewriteCond %{QUERY_STRING} "!format="
  RewriteCond %{REQUEST_URI}  "/search"
  RewriteRule ^([^/.]+) ui/$1.html [R,END]
</Directory>
```

Restart Apache and the UI should be available.
