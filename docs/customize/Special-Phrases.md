# Special phrases

## Importing OSM user-maintained special phrases

As described in the [Import section](../admin/Import.md), it is possible to
import special phrases from the wiki with the following command:

```sh
nominatim special-phrases --import-from-wiki
```

## Importing custom special phrases

But, it is also possible to import some phrases from a csv file. 
To do so, you have access to the following command:

```sh
nominatim special-phrases --import-from-csv <csv file>
```

Note that the two previous import commands will update the phrases from your database.
This means that if you import some phrases from a csv file, only the phrases
present in the csv file will be kept into the database. All other phrases will
be removed.

If you want to only add new phrases and not update the other ones you can add
the argument `--no-replace` to the import command. For example:

```sh
nominatim special-phrases --import-from-csv <csv file> --no-replace
```

This will add the phrases present in the csv file into the database without
removing the other ones.
