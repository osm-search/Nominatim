This section provides a reference of all configuration parameters that can
be used with Nominatim.

# Configuring Nominatim

Nominatim uses [dotenv](https://github.com/theskumar/python-dotenv) to manage
its configuration settings. There are two means to set configuration
variables: through an `.env` configuration file or through an environment
variable.

The `.env` configuration file needs to be placed into the
[project directory](../admin/Import/#creating-the-project-directory). It
must contain configuration parameters in `<parameter>=<value>` format.
Please refer to the dotenv documentation for details.

The configuration options may also be set in the form of shell environment
variables. This is particularly useful, when you want to temporarily change
a configuration option. For example, to force the replication serve to
download the next change, you can temporarily disable the update interval:

    NOMINATIM_REPLICATION_UPDATE_INTERVAL=0 nominatim replication --once

If a configuration option is defined through .env file and environment
variable, then the latter takes precedence. 

# Configuration Parameter Reference

