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
nominatim import --continue indexing
```

If the reported rank is 26 or higher, you can also safely add `--index-noanalyse`.


### PostgreSQL crashed "invalid page in block"

Usually serious problem, can be a hardware issue, not all data written to disc
for example. Check PostgreSQL log file and search PostgreSQL issues/mailing
list for hints.

If it happened during index creation you can try rerunning the step with

```sh
nominatim import --continue indexing
```

Otherwise it's best to start the full setup from the beginning.


### PHP "open_basedir restriction in effect" warnings

    PHP Warning:  file_get_contents(): open_basedir restriction in effect.

You need to adjust the
[open_basedir](https://www.php.net/manual/en/ini.core.php#ini.open-basedir)
setting in your PHP configuration (`php.ini` file). By default this setting may
look like this:

    open_basedir = /srv/http/:/home/:/tmp/:/usr/share/pear/

Either add reported directories to the list or disable this setting temporarily
by adding ";" at the beginning of the line. Don't forget to enable this setting
again once you are done with the PHP command line operations.


### PHP timezeone warnings

The Apache log may contain lots of PHP warnings like this:
    `PHP Warning:  date_default_timezone_set() function.`

You should set the default time zone as instructed in the warning in
your `php.ini` file. Find the entry about timezone and set it to
something like this:

    ; Defines the default timezone used by the date functions
    ; https://php.net/date.timezone
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
server development libraries (`postgresql-server-dev-13` on Ubuntu)
and recompile (`cmake .. && make`).


### I see the error "ERROR: permission denied for language c"

`nominatim.so`, written in C, is required to be installed on the database
server. Some managed database (cloud) services like Amazon RDS do not allow
this. There is currently no work-around other than installing a database
on a non-managed machine.


### I see the error: "function transliteration(text) does not exist"

Reinstall the nominatim functions with `nominatim refresh --functions`
and check for any errors, e.g. a missing `nominatim.so` file.

### I see the error: "ERROR: mmap (remap) failed"

This may be a simple out-of-memory error. Try reducing the memory used
for `--osm2pgsql-cache`. Also make sure that overcommitting memory is
allowed: `cat /proc/sys/vm/overcommit_memory` should print 0 or 1.

If you are using a flatnode file, then it may also be that the underlying
filesystem does not fully support 'mmap'. A notable candidate is virtualbox's
vboxfs.

### nominatim UPDATE failed: ERROR: buffer 179261 is not owned by resource owner Portal

Several users [reported this](https://github.com/openstreetmap/Nominatim/issues/1168)
during the initial import of the database. It's
something PostgreSQL internal Nominatim doesn't control. And PostgreSQL forums
suggest it's threading related but definitely some kind of crash of a process.
Users reported either rebooting the server, different hardware or just trying
the import again worked.

### The website shows: "Could not get word tokens"

The server cannot access your database. Add `&debug=1` to your URL
to get the full error message.


### Website reports "DB Error: insufficient permissions"

The user the webserver, e.g. Apache, runs under needs to have access to the
Nominatim database. You can find the user like
[this](https://serverfault.com/questions/125865/finding-out-what-user-apache-is-running-as),
for default Ubuntu operating system for example it's `www-data`.

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

The PostgreSQL database, i.e. user `postgres`, needs to have access to that file.

The permission need to be read & executable by everybody, but not writeable
by everybody, e.g.

```
   -rwxr-xr-x 1 nominatim nominatim 297984 build/module/nominatim.so
```

Try `chmod a+r nominatim.so; chmod a+x nominatim.so`.

When you recently updated your operating system, updated PostgreSQL to
a new version or moved files (e.g. the build directory) you should
recreate `nominatim.so`. Try

```
   cd build
   rm -r module/
   cmake $main_Nominatim_path && make
```

### Setup.php fails with "DB Error: extension not found"

Make sure you have the PostgreSQL extensions "hstore" and "postgis" installed.
See the installation instructions for a full list of required packages.


### I forgot to delete the flatnodes file before starting an import.

That's fine. For each import the flatnodes file get overwritten.
See [https://help.openstreetmap.org/questions/52419/nominatim-flatnode-storage](https://help.openstreetmap.org/questions/52419/nominatim-flatnode-storage)
for more information.


## Running your own instance

### Can I import negative OSM ids into Nominatim?

See [this question of Stackoverflow](https://help.openstreetmap.org/questions/64662/nominatim-flatnode-with-negative-id).
