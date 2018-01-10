Frequently Asked Questions
==========================

Running Your Own Instance
-------------------------

### Can I import only a few countries and also keep them up to date?

You should use the extracts and updates from http://download.geofabrik.de.
For the intial import, download the countries you need and merge them.
See [OSM Help](https://help.openstreetmap.org/questions/48843/merging-two-or-more-geographical-areas-to-import-two-or-more-osm-files-in-nominatim)
for examples how to do that. Use the resulting single osm file when
running `setup.php`.

For updates you need to download the change files for each country
once per day and apply them **separately** using

    ./utils/update.php --import-diff <filename> --index
    
See [this issue](https://github.com/openstreetmap/Nominatim/issues/60#issuecomment-18679446)
for a script that runs the updates using osmosis.

### My website shows: `XML Parsing Error: XML or text declaration not at start of entity Location</code>.`

Make sure there are no spaces at the beginning of your `settings/local.php` file.


Installation
------------

### I accidentally killed the import process after it has been running for many hours. Can it be resumed?

It is possible if the import already got to the indexing stage.
Check the last line of output that was logged before the process
was killed. If it looks like this:

   Done 844 in 13 @ 64.923080 per second - Rank 26 ETA (seconds): 7.886255

then you can resume with the following command:

   ./utils/setup.php --index --create-search-indices --create-country-names

If the reported rank is 26 or higher, you can also safely add `--index-noanalyse`.


### When running the setup.php script I get a warning:
    `PHP Warning:  file_get_contents(): open_basedir restriction in effect.`

You need to adjust the [open_basedir](http://www.php.net/manual/en/ini.core.php#ini.open-basedir) setting
in your PHP configuration (php.ini file). By default this setting may look like this:

    open_basedir = /srv/http/:/home/:/tmp/:/usr/share/pear/

Either add reported directories to the list or disable this setting temporarily by 
dding ";" at the beginning of the line. Don't forget to enable this setting again
once you are done with the PHP command line operations.


### The Apache log contains lots of PHP warnings like this:
    `PHP Warning:  date_default_timezone_set() function.`

You should set the default time zone as instructed in the warning in
your `php.ini` file. Find the entry about timezone and set it to
something like this:
  
    ; Defines the default timezone used by the date functions
    ; http://php.net/date.timezone
    date.timezone = 'America/Denver'

Or

   echo "date.timezone = 'America/Denver'" > /etc/php.d/timezone.ini


### When running the import I get a version mismatch:
    `COPY_END for place failed: ERROR: incompatible library "/opt/Nominatim/module/nominatim.so": version mismatch`

pg_config seems to use bad includes sometimes when multiple versions
of PostgreSQL are available in the system. Make sure you remove the
server development libraries (`postgresql-server-dev-9.1` on Ubuntu)
and recompile (`cmake .. && make`).


### I see the error: `function transliteration(text) does not exist`

Reinstall the nominatim functions with `setup.php --create--functions`
and check for any errors, e.g. a missing `nominatim.so` file.


### The website shows: `Could not get word tokens`

The server cannot access your database. Add `&debug=1` to your URL
to get the full error message.


### On CentOS the website shows `could not connect to server: No such file or directory`

On CentOS v7 the PostgreSQL server is started with `systemd`.
Check if `/usr/lib/systemd/system/httpd.service` contains a line `PrivateTmp=true`.
If so then Apache cannot see the `/tmp/.s.PGSQL.5432` file. It's a good security feature,
so use the [[#PostgreSQL_UNIX_Socket_Location_on_CentOS|preferred solution]] 

However, you can solve this the quick and dirty way by commenting out that line and then run

    sudo systemctl daemon-reload
    sudo systemctl restart httpd


### Setup.php fails with the message: `DB Error: extension not found`

Make sure you have the Postgres extensions hstore and postgis installed.
See the installation instruction for a full list of required packages.

### When running the setup.php script I get a error:
    `Cannot redeclare getDB() (previously declared in /your/path/Nominatim/lib/db.php:4)`

The message is a bit misleading as PHP needs to load the file `DB.php` and
instead re-loads Nominatim's `db.php`. To solve this make sure you
have the [http://pear.php.net/package/DB/ Pear module 'DB'] installed.

    sudo pear install DB

### I forgot to delete the flatnodes file before starting an import

That's fine. For each import the flatnodes file get overwritten.
See https://help.openstreetmap.org/questions/52419/nominatim-flatnode-storage
for more information.
