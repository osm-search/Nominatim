# Documentation Pages

The [Nominatim documentation](https://nominatim.org/release-docs/develop/) is built using the [MkDocs](https://www.mkdocs.org/) static site generation framework. The master branch is automatically deployed every night on under [https://nominatim.org/release-docs/develop/]()

To preview local changes:

1. Install MkDocs

   ```
   pip3 install --user mkdocs 
   ```


2. In build directory run

   ```
   make doc
   INFO - Cleaning site directory
   INFO - Building documentation to directory: /home/vagrant/build/site-html 
   ```

   This runs `mkdocs build` plus extra transformion of some files and adds symlinks (see `CMakeLists.txt` for the exact steps).


3. Start webserver for local testing

   ```
   mkdocs serve
   [server:296] Serving on http://127.0.0.1:8000
   [handlers:62] Start watching changes
   ```

   If you develop inside a Vagrant virtual machine:
   * add port forwarding to your Vagrantfile, e.g. `config.vm.network "forwarded_port", guest: 8000, host: 8000`
   * use `mkdocs serve --dev-addr 0.0.0.0:8000` because the default localhost
      IP does not get forwarded.
