# Deploying the Nominatim Python frontend

Nominatim can be run as a Python-based
[ASGI web application](https://asgi.readthedocs.io/en/latest/). You have the
choice between [Falcon](https://falcon.readthedocs.io/en/stable/)
and [Starlette](https://www.starlette.io/) as the ASGI framework.

This section gives a quick overview on how to configure Nginx to serve
Nominatim. Please refer to the documentation of
[Nginx](https://nginx.org/en/docs/) for background information on how
to configure it.

### Installing the required packages

!!! warning
    ASGI support in gunicorn requires at least version 25.0. If you need
    to work with an older version of gunicorn, please refer to
    [older Nominatim deployment documentation](https://nominatim.org/release-docs/5.2/admin/Deployment-Python/)
    to learn how to run gunicorn with uvicorn.

The Nominatim frontend is best run from its own virtual environment. If
you have already created one for the database backend during the
[installation](Installation.md#building-nominatim), you can use that. Otherwise
create one now with:

```sh
sudo apt-get install virtualenv
virtualenv /srv/nominatim-venv
```

The Nominatim frontend is contained in the 'nominatim-api' package. To
install directly from the source tree run:

```sh
cd Nominatim
/srv/nominatim-venv/bin/pip install packaging/nominatim-api
```

The recommended way to deploy a Python ASGI application is to run
the [gunicorn](https://gunicorn.org/) HTTP server. We use
Falcon here as the web framework.

Add the necessary packages to your virtual environment:

``` sh
/srv/nominatim-venv/bin/pip install falcon gunicorn
```

### Setting up Nominatim as a systemd job

!!! Note
    These instructions assume your Nominatim project directory is
    located in `/srv/nominatim-project`. If you have put it somewhere else,
    you need to adjust the commands and configuration accordingly.

Next you need to set up the service that runs the Nominatim frontend. This is
easiest done with a systemd job.

First you need to tell systemd to create a socket file to be used by
gunicorn. Create the following file `/etc/systemd/system/nominatim.socket`:

``` systemd
[Unit]
Description=Gunicorn socket for Nominatim

[Socket]
ListenStream=/run/nominatim.sock
SocketUser=www-data

[Install]
WantedBy=multi-user.target
```

Now you can add the systemd service for Nominatim itself.
Create the following file `/etc/systemd/system/nominatim.service`:

``` systemd
[Unit]
Description=Nominatim running as a gunicorn application
After=network.target
Requires=nominatim.socket

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/srv/nominatim-project
ExecStart=/srv/nominatim-venv/bin/gunicorn -b unix:/run/nominatim.sock -w 4 --worker-class asgi --protocol uwsgi --worker-connections 1000 "nominatim_api.server.falcon.server:run_wsgi()"
ExecReload=/bin/kill -s HUP $MAINPID
PrivateTmp=true
TimeoutStopSec=5
KillMode=mixed

[Install]
WantedBy=multi-user.target
```

This sets up gunicorn with 4 workers (`-w 4` in ExecStart). Each worker runs
its own Python process using
[`NOMINATIM_API_POOL_SIZE`](../customize/Settings.md#nominatim_api_pool_size)
connections to the database to serve requests in parallel. The parameter
`--worker-connections` restricts how many requests gunicorn will queue for
each worker. This can help distribute work better when the server is under
high load.

Make the new services known to systemd and start it:

``` sh
sudo systemctl daemon-reload
sudo systemctl enable nominatim.socket
sudo systemctl start nominatim.socket
sudo systemctl enable nominatim.service
sudo systemctl start nominatim.service
```

This sets the service up so that Nominatim is automatically started
on reboot.

### Configuring nginx

To make the service available to the world, you need to proxy it through
nginx. We use the binary uwsgi protocol to speed up communication
between nginx and gunicorn. Add the following definition to the default
configuration:

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
        uwsgi_pass nominatim_service;
        include uwsgi_params;
    }
}
```

Reload nginx with

```
sudo systemctl reload nginx
```

and you should be able to see the status of your server under
`http://localhost/status`.


### Proposed Documentation Update: Troubleshooting the Python Frontend

If you are setting up the Python frontend for the first time or in a development environment (like a local home directory), you may encounter the following issues.

### 1. Essential System Dependencies
The `nominatim-api` package depends on `pyicu`, which requires C++ development headers and `pkg-config` to build correctly from source.

**Error you might see:**
* Error: `RuntimeError: Please install pkg-config on your system`
* Error: `KeyError: 'ICU_VERSION'`

**Solution:**
Install the missing system libraries before running `pip install`:
```bash
sudo apt-get install pkg-config libicu-dev
```
### 2. Permissions & Directory Setup
The guide assumes a global /srv/ directory. If you are a standard user, you will face "Permission Denied" errors when creating the virtual environment.

**Error you might see:**
* Error: `virtualenv: error: argument dest: the destination . is not write-able at /srv`

**Solution:**
```bash
sudo mkdir -p /srv/nominatim-venv
sudo chown $USER:$USER /srv/nominatim-venv
virtualenv /srv/nominatim-venv
```

### 3. Proper Pathing for Installation
When installing from the local source tree (./packaging/nominatim-api), you must be in the root directory of the cloned repository.

**Error you might see:**
* Error: `Invalid requirement: 'packaging/nominatim-api' ... File does not exist.`

**Solution:**
Verify your location with ls. You should see the packaging and src folders. If your path contains spaces, wrap it in quotes:

```Bash

cd "/home/user/Downloads/Nominatim-master"
pip install ./packaging/nominatim-api
```

### 4. Nginx Directory Readiness
On fresh Ubuntu/Debian installs, the `sites-available` folder might not exist, causing Nginx configuration saves to fail.

**Error you might see:**
* Error: `Error writing /etc/nginx/sites-available/default: No such file or directory`

**Solution:**
Create the directory structure manually before opening the editor:
```Bash
sudo mkdir -p /etc/nginx/sites-available
sudo nano /etc/nginx/sites-available/default
```

### 5. Final Permission Check (The "403 Forbidden" Fix)
If you run Nominatim from your /home/user/Downloads folder, the Nginx user (www-data) cannot see your files, resulting in a 403 Forbidden error.

**Solution:**
Grant "Execute" permissions to your home and project folders so the web server can access the directory tree:
```Bash
chmod +x /home/your-username
chmod +x /home/your-username/Downloads
```
