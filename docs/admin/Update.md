# Updating the Database

There are many different ways to update your Nominatim database.
The following section describes how to keep it up-to-date with Pyosmium.
For a list of other methods see the output of `./utils/update.php --help`.

!!! important
    If you have configured a flatnode file for the import, then you
    need to keep this flatnode file around for updates.

#### Installing the newest version of Pyosmium

It is recommended to install Pyosmium via pip. Make sure to use python3.
Run (as the same user who will later run the updates):

```sh
pip3 install --user osmium
```

Nominatim needs a tool called `pyosmium-get-changes` which comes with
Pyosmium. You need to tell Nominatim where to find it. Add the
following line to your `.env`:

    NOMINATIM_PYOSMIUM_BINARY=/home/user/.local/bin/pyosmium-get-changes

The path above is fine if you used the `--user` parameter with pip.
Replace `user` with your user name.

#### Setting up the update process

Next the update needs to be initialised. By default Nominatim is configured
to update using the global minutely diffs.

If you want a different update source you will need to add some settings
to `.env`. For example, to use the daily country extracts
diffs for Ireland from Geofabrik add the following:

    # base URL of the replication service
    NOMINATIM_REPLICATION_URL="https://download.geofabrik.de/europe/ireland-and-northern-ireland-updates"
    # How often upstream publishes diffs
    NOMINATIM_REPLICATION_UPDATE_INTERVAL=86400
    # How long to sleep if no update found yet
    NOMINATIM_REPLICATION_RECHECK_INTERVAL=900

To set up the update process now run the following command:

    ./utils/update.php --init-updates

It outputs the date where updates will start. Recheck that this date is
what you expect.

The `--init-updates` command needs to be rerun whenever the replication service
is changed.

#### Updating Nominatim

The following command will keep your database constantly up to date:

    ./utils/update.php --import-osmosis-all

(Note that even though the old name "import-osmosis-all" has been kept for
compatibility reasons, Osmosis is not required to run this - it uses pyosmium
behind the scenes.)

If you have imported multiple country extracts and want to keep them
up-to-date, [Advanced installations section](Advanced-Installations.md) contains instructions 
to set up and update multiple country extracts.
