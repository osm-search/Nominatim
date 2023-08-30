# Deploying the Nominatim Python frontend

The Nominatim can be run as a Python-based 
[ASGI web application](https://asgi.readthedocs.io/en/latest/). You have the
choice between [Falcon](https://falcon.readthedocs.io/en/stable/)
and [Starlette](https://www.starlette.io/) as the ASGI framework.

This section gives a quick overview on how to configure Nginx to serve
Nominatim. Please refer to the documentation of
[Nginx](https://nginx.org/en/docs/) for background information on how
to configure it.

!!! Note
    Throughout this page, we assume your Nominatim project directory is
    located in `/srv/nominatim-project` and you have installed Nominatim
    using the default installation prefix `/usr/local`. If you have put it
    somewhere else, you need to adjust the commands and configuration
    accordingly.

    We further assume that your web server runs as user `www-data`. Older
    versions of CentOS may still use the user name `apache`. You also need
    to adapt the instructions in this case.

### Installing the required packages

The recommended way to deploy a Python ASGI application is to run
the ASGI runner [uvicorn](https://uvicorn.org/)
together with [gunicorn](https://gunicorn.org/) HTTP server. We use
Falcon here as the web framework.

Create a virtual environment for the Python packages and install the necessary
dependencies:

``` sh
sudo apt install virtualenv
virtualenv /srv/nominatim-venv
/srv/nominatim-venv/bin/pip install SQLAlchemy PyICU psycopg[binary] \
   psycopg2-binary python-dotenv PyYAML falcon uvicorn gunicorn
```

### Setting up Nominatim as a systemd job

Next you need to set up the service that runs the Nominatim frontend. This is
easiest done with a systemd job.

Create the following file `/etc/systemd/system/nominatim.service`:

``` systemd
[Unit]
Description=Nominatim running as a gunicorn application
After=network.target
Requires=nominatim.socket

[Service]
Type=simple
Environment="PYTHONPATH=/usr/local/lib/nominatim/lib-python/"
User=www-data
Group=www-data
WorkingDirectory=/srv/nominatim-project
ExecStart=/srv/nominatim-venv/bin/gunicorn -b unix:/run/nominatim.sock -w 4 -k uvicorn.workers.UvicornWorker nominatim.server.falcon.server:run_wsgi
ExecReload=/bin/kill -s HUP $MAINPID
StandardOutput=append:/var/log/gunicorn-nominatim.log
StandardError=inherit
PrivateTmp=true
TimeoutStopSec=5
KillMode=mixed

[Install]
WantedBy=multi-user.target
```

This sets up gunicorn with 4 workers (`-w 4` in ExecStart). Each worker runs
its own Python process using
[`NOMINATIM_API_POOL_SIZE`](../customize/Settings.md#nominatim_api_pool_size)
connections to the database to serve requests in parallel.

Make the new service known to systemd and start it:

``` sh
sudo systemctl daemon-reload
sudo systemctl enable nominatim
sudo systemctl start nominatim
```

This sets the service up, so that Nominatim is automatically started
on reboot.

### Configuring nginx

To make the service available to the world, you need to proxy it through
nginx. Add the following definition to the default configuration:

``` nginx
upstream nominatim_service {
  server unix:/run/nominatim.sock fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;

    root /var/www/html;
    index /search;

    location / {
            proxy_set_header Host $http_host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
            proxy_pass http://nominatim_service;
    }
}
```

Reload nginx with

```
sudo systemctl reload nginx
```

and you should be able to see the status of your server under
`http://localhost/status`.
