# Configuration

When using Nominatim through the library, it can be configured in exactly
the same way as when running as a service. This means that you should have
created a [project directory](../admin/Import.md#creating-the-project-directory)
which contains all files belonging to the Nominatim instance. It can also contain
an `.env` file with configuration options. Setting configuration parameters
via environment variables works as well.

Configuration options are resolved in the following order:

* from the OS environment (or the dictionary given in `environ`,
  (see NominatimAPI.md#nominatim.api.core.NominatimAPI.__init__)
* from the .env file in the project directory of the installation
* from the default installation in the configuration directory

For more information on configuration via dotenv and a list of possible
configuration parameters, see the [Configuration page](../customize/Settings.md).


## `Configuration` class

::: nominatim.config.Configuration
    options:
        members:
            - get_bool
            - get_int
            - get_str_list
            - get_path
        heading_level: 6
        show_signature_annotations: True
