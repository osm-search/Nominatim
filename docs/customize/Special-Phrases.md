# Special phrases

## Importing OSM user-maintained special phrases

As described in the [Import section](../admin/Import.md), it is possible to
import special phrases from the wiki with the following command:

```sh
nominatim special-phrases --import-from-wiki
```

## Importing custom special phrases

Special phrases may also be imported from any custom CSV file. The file needs
to have a header line, use comma as delimiter and define the following
columns:

 * **phrase**: the keyword to look for
 * **class**: key of the main tag of the place to find
   (see [principal tags in import style](Import-Styles.md#set_main_tags-principal-tags)
 * **type**: value of the main tag
 * **operator**: type of special phrase, may be one of:
     * *in*: place is within the place defined by the search term (e.g. "_Hotels in_ Berlin")
     * *near*: place is near the place defined by the search term (e.g. "_bus stops near_ Big Ben")
     * *named*: special phrase is a classifier (e.g. "_hotel_ California")
     * *-*: unspecified, can be any of the above

If the file contains any other columns, then they are silently ignored

To import the CSV file, use the following command:

```sh
nominatim special-phrases --import-from-csv <csv file>
```

Note that the two previous import commands will update the phrases from your database.
This means that if you import some phrases from a CSV file, only the phrases
present in the CSV file will be kept in the database. All other phrases will
be removed.

If you want to only add new phrases and not update the other ones you can add
the argument `--no-replace` to the import command. For example:

```sh
nominatim special-phrases --import-from-csv <csv file> --no-replace
```

This will add the phrases present in the CSV file into the database without
removing the other ones.
