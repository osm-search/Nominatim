# Documentation Pages

The [Nominatim documentation](https://nominatim.org/release-docs/develop/) is built using the [MkDocs](https://www.mkdocs.org/) static site generation framework. The master branch is automatically deployed every night on under [https://nominatim.org/release-docs/develop/](https://nominatim.org/release-docs/develop/)

To preview local changes, first install MkDocs

```
pip3 install --user mkdocs
```

If `mkdocs` can't be found after the installation, the $PATH might have not
be set correctly yet. Try opening a new terminal session.


Then go to the build directory and run

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

If you develop inside a Vagrant virtual machine:

 * add port forwarding to your Vagrantfile,
   e.g. `config.vm.network "forwarded_port", guest: 8000, host: 8000`
 * use `mkdocs serve --dev-addr 0.0.0.0:8000` because the default localhost
   IP does not get forwarded.
