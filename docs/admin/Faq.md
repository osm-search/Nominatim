# Troubleshooting Nominatim Installations

## Installation Issues

### Can a stopped/killed import process be resumed?

"I accidentally killed the import process after it has been running for many hours. Can it be resumed?"

It is possible if the import already got to the indexing stage.
Check the last line of output that was logged before the process
was killed. If it looks like this:


    Done 844 in 13 @ 64.923080 per second - Rank 26 ETA (seconds): 7.886255

then you can resume with the following command:

```sh
./utils/setup.php --index --create-search-indices --create-country-names
```

If the reported rank is 26 or higher, you can also safely add `--index-noanalyse`.


### PHP "open_basedir restriction in effect" warnings

    `PHP Warning:  file_get_contents(): open_basedir restriction in effect.`

You need to adjust the [open_basedir](http://www.php.net/manual/en/ini.core.php#ini.open-basedir) setting
in your PHP configuration (`php.ini file`). By default this setting may look like this:

    open_basedir = /srv/http/:/home/:/tmp/:/usr/share/pear/

Either add reported directories to the list or disable this setting temporarily by 
dding ";" at the beginning of the line. Don't forget to enable this setting again
once you are done with the PHP command line operations.


### PHP timzeone warnings

The Apache log may contain lots of PHP warnings like this:
    `PHP Warning:  date_default_timezone_set() function.`

You should set the default time zone as instructed in the warning in
your `php.ini` file. Find the entry about timezone and set it to
something like this:
  
    ; Defines the default timezone used by the date functions
    ; http://php.net/date.timezone
    date.timezone = 'America/Denver'

Or

```
echo "date.timezone = 'America/Denver'" > /etc/php.d/timezone.ini
```

### nominatim.so version mismatch

When running the import you may get a version mismatch:
`COPY_END for place failed: ERROR: incompatible library "/srv/Nominatim/nominatim/build/module/nominatim.so": version mismatch`

pg_config seems to use bad includes sometimes when multiple versions
of PostgreSQL are available in the system. Make sure you remove the
server development libraries (`postgresql-server-dev-9.5` on Ubuntu)
and recompile (`cmake .. && make`).


### I see the error: "function transliteration(text) does not exist"

Reinstall the nominatim functions with `setup.php --create--functions`
and check for any errors, e.g. a missing `nominatim.so` file.

### I see the error: "ERROR: mmap (remap) failed"

This may be a simple out-of-memory error. Try reducing the memory used
for `--osm2pgsql-cache`. Also make sure that overcommitting memory is
allowed: `cat /proc/sys/vm/overcommit_memory` should print 0 or 1.

If you are using a flatnode file, then it may also be that the underlying
filesystem does not fully support 'mmap'. A notable candidate is virtualbox's
vboxfs.

### The website shows: "Could not get word tokens"

The server cannot access your database. Add `&debug=1` to your URL
to get the full error message.


### On CentOS the website shows "Could not connect to server"

`could not connect to server: No such file or directory`

On CentOS v7 the PostgreSQL server is started with `systemd`.
Check if `/usr/lib/systemd/system/httpd.service` contains a line `PrivateTmp=true`.
If so then Apache cannot see the `/tmp/.s.PGSQL.5432` file. It's a good security feature,
so use the [preferred solution](../appendix/Install-on-Centos-7/#adding-selinux-security-settings).

However, you can solve this the quick and dirty way by commenting out that line and then run

    sudo systemctl daemon-reload
    sudo systemctl restart httpd


### "must be an array or an object that implements Countable" warning in /usr/share/pear/DB.php

As reported starting PHP 7.2. This external DB library is no longer maintained and will be replaced in future Nominatim versions. In the meantime you'd have to manually change the line near 774 from
`if (!count($dsn)) {` to  `if (!$dsn && !count($dsn))`. [More details](https://github.com/openstreetmap/Nominatim/issues/1184)




### Website reports "DB Error: insufficient permissions"

The user the webserver, e.g. Apache, runs under needs to have access to the Nominatim database. You can find the user like [this](https://serverfault.com/questions/125865/finding-out-what-user-apache-is-running-as), for default Ubuntu operating system for example it's `www-data`.

1. Repeat the `createuser` step of the installation instructions.

2. Give the user permission to existing tables

```
   GRANT usage ON SCHEMA public TO "www-data";
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO "www-data";
```

### Website reports "Could not load library "nominatim.so"

Example error message

```
   SELECT make_standard_name('3039 E MEADOWLARK LN') [nativecode=ERROR: could not
   load library "/srv/nominatim/Nominatim-3.1.0/build/module/nominatim.so":
   /srv/nominatim/Nominatim-3.1.0/build/module/nominatim.so: cannot open shared
   object file: Permission denied
   CONTEXT: PL/pgSQL function make_standard_name(text) line 5 at assignment]
```

The Postgresql database, i.e. user postgres, needs to have access to that file.

The permission need to be read & executable by everybody, e.g.

```
   -rwxr-xr-x 1 nominatim nominatim 297984 build/module/nominatim.so
```

Try `chmod a+r nominatim.so; chmod a+x nominatim.so`.

When running SELinux, make sure that the
[context is set up correctly](../appendix/Install-on-Centos-7/#adding-selinux-security-settings).

### Setup.php fails with "DB Error: extension not found"

Make sure you have the Postgres extensions hstore and postgis installed.
See the installation instruction for a full list of required packages.


### Setup.php reports "Cannot redeclare getDB()"

`Cannot redeclare getDB() (previously declared in /your/path/Nominatim/lib/db.php:4)`

The message is a bit misleading as PHP needs to load the file `DB.php` and
instead re-loads Nominatim's `db.php`. To solve this make sure you
have the [Pear module 'DB'](http://pear.php.net/package/DB/) installed.

    sudo pear install DB

### I forgot to delete the flatnodes file before starting an import.

That's fine. For each import the flatnodes file get overwritten.
See [https://help.openstreetmap.org/questions/52419/nominatim-flatnode-storage]()
for more information.


## Running your own instance

### Can I import multiple countries and keep them up to date?

You should use the extracts and updates from https://download.geofabrik.de.
For the initial import, download the countries you need and merge them.
See [OSM Help](https://help.openstreetmap.org/questions/48843/merging-two-or-more-geographical-areas-to-import-two-or-more-osm-files-in-nominatim)
for examples how to do that. Use the resulting single osm file when
running `setup.php`.

For updates you need to download the change files for each country
once per day and apply them **separately** using

    ./utils/update.php --import-diff <filename> --index
    
See [this issue](https://github.com/openstreetmap/Nominatim/issues/60#issuecomment-18679446)
for a script that runs the updates using osmosis.

### Can I import negative OSM ids into Nominatim?

See [this question of Stackoverflow](https://help.openstreetmap.org/questions/64662/nominatim-flatnode-with-negative-id).

### Missing XML or text declaration

The website might show: `XML Parsing Error: XML or text declaration not at start of entity Location.`

Make sure there are no spaces at the beginning of your `settings/local.php` file.


