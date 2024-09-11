# Configuration

When using Nominatim through the library, it can be configured in exactly
the same way as when running as a service. You may instantiate the library
against the [project directory](../admin/Import.md#creating-the-project-directory)
of your Nominatim installation. It contains all files belonging to the
Nominatim instance. This may include an `.env` file with configuration options.
Setting configuration parameters via environment variables works as well.
Alternatively to using the operating system's environment, a set of
configuration parameters may also be passed to the Nomiantim API object.

Configuration options are resolved in the following order:

* from the OS environment (or the dictionary given in `environ`,
  (see NominatimAPI.md#nominatim.api.core.NominatimAPI.__init__)
* from the .env file in the project directory of the installation
* from the default installation in the configuration directory

For more information on configuration via dotenv and a list of possible
configuration parameters, see the [Configuration page](../customize/Settings.md).


## `Configuration` class

::: nominatim_api.Configuration
    options:
        members:
            - get_bool
            - get_int
            - get_str_list
            - get_path
        heading_level: 6
        show_signature_annotations: True
