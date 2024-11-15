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

### Setup fails with "DB Error: extension not found"

Make sure you have the PostgreSQL extensions "hstore" and "postgis" installed.
See the installation instructions for a full list of required packages.


### UnicodeEncodeError: 'ascii' codec can't encode character

Make sure that the operating system's locale is UTF-8. With some prebuilt
images (e.g. LXC containers from Proxmox, see
[discussion](https://github.com/osm-search/Nominatim/discussions/2343)) or
images that optimize for size it might be missing.

On Ubuntu you can check the locale is installed:

```
   grep UTF-8 /etc/default/locale
```

And install it using

```
   dpkg-reconfigure locales
```

### I forgot to delete the flatnodes file before starting an import.

That's fine. For each import the flatnodes file get overwritten.
See [https://help.openstreetmap.org/questions/52419/nominatim-flatnode-storage](https://help.openstreetmap.org/questions/52419/nominatim-flatnode-storage)
for more information.


## Running your own instance

### Can I import negative OSM ids into Nominatim?

No, negative IDs are no longer supported by osm2pgsql. You can use
large 64-bit IDs that are guaranteed not to clash with OSM IDs. However,
you will not able to use a flatnode file with them.
