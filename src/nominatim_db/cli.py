# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Command-line interface to the Nominatim functions for import, update,
database administration and querying.
"""
from typing import Optional, Any
import importlib
import logging
import os
import sys
import argparse
import asyncio
from pathlib import Path

from .config import Configuration
from .errors import UsageError
from .tools.exec_utils import run_php_server
from . import clicmd
from . import version
from .clicmd.args import NominatimArgs, Subcommand

LOG = logging.getLogger()

class CommandlineParser:
    """ Wraps some of the common functions for parsing the command line
        and setting up subcommands.
    """
    def __init__(self, prog: str, description: Optional[str]):
        self.parser = argparse.ArgumentParser(
            prog=prog,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter)

        self.subs = self.parser.add_subparsers(title='available commands',
                                               dest='subcommand')

        # Global arguments that only work if no sub-command given
        self.parser.add_argument('--version', action='store_true',
                                 help='Print Nominatim version and exit')

        # Arguments added to every sub-command
        self.default_args = argparse.ArgumentParser(add_help=False)
        group = self.default_args.add_argument_group('Default arguments')
        group.add_argument('-h', '--help', action='help',
                           help='Show this help message and exit')
        group.add_argument('-q', '--quiet', action='store_const', const=0,
                           dest='verbose', default=1,
                           help='Print only error messages')
        group.add_argument('-v', '--verbose', action='count', default=1,
                           help='Increase verboseness of output')
        group.add_argument('--project-dir', metavar='DIR', default='.',
                           help='Base directory of the Nominatim installation (default:.)')
        group.add_argument('-j', '--threads', metavar='NUM', type=int,
                           help='Number of parallel threads to use')


    def nominatim_version_text(self) -> str:
        """ Program name and version number as string
        """
        text = f'Nominatim version {version.NOMINATIM_VERSION!s}'
        if version.GIT_COMMIT_HASH is not None:
            text += f' ({version.GIT_COMMIT_HASH})'
        return text


    def add_subcommand(self, name: str, cmd: Subcommand) -> None:
        """ Add a subcommand to the parser. The subcommand must be a class
            with a function add_args() that adds the parameters for the
            subcommand and a run() function that executes the command.
        """
        assert cmd.__doc__ is not None

        parser = self.subs.add_parser(name, parents=[self.default_args],
                                      help=cmd.__doc__.split('\n', 1)[0],
                                      description=cmd.__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter,
                                      add_help=False)
        parser.set_defaults(command=cmd)
        cmd.add_args(parser)


    def run(self, **kwargs: Any) -> int:
        """ Parse the command line arguments of the program and execute the
            appropriate subcommand.
        """
        args = NominatimArgs()
        try:
            self.parser.parse_args(args=kwargs.get('cli_args'), namespace=args)
        except SystemExit:
            return 1

        if args.version:
            print(self.nominatim_version_text())
            return 0

        if args.subcommand is None:
            self.parser.print_help()
            return 1

        args.project_dir = Path(args.project_dir).resolve()

        if 'cli_args' not in kwargs:
            logging.basicConfig(stream=sys.stderr,
                                format='%(asctime)s: %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S',
                                level=max(4 - args.verbose, 1) * 10)

        args.config = Configuration(args.project_dir,
                                    environ=kwargs.get('environ', os.environ))
        args.config.set_libdirs(module=kwargs['module_dir'],
                                osm2pgsql=kwargs['osm2pgsql_path'])

        log = logging.getLogger()
        log.warning('Using project directory: %s', str(args.project_dir))

        try:
            return args.command.run(args)
        except UsageError as exception:
            if log.isEnabledFor(logging.DEBUG):
                raise # use Python's exception printing
            log.fatal('FATAL: %s', exception)

        # If we get here, then execution has failed in some way.
        return 1


# Subcommand classes
#
# Each class needs to implement two functions: add_args() adds the CLI parameters
# for the subfunction, run() executes the subcommand.
#
# The class documentation doubles as the help text for the command. The
# first line is also used in the summary when calling the program without
# a subcommand.
#
# No need to document the functions each time.
# pylint: disable=C0111
class AdminServe:
    """\
    Start a simple web server for serving the API.

    This command starts a built-in webserver to serve the website
    from the current project directory. This webserver is only suitable
    for testing and development. Do not use it in production setups!

    There are different webservers available. The default 'php' engine
    runs the classic PHP frontend. The other engines are Python servers
    which run the new Python frontend code. This is highly experimental
    at the moment and may not include the full API.

    By the default, the webserver can be accessed at: http://127.0.0.1:8088
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Server arguments')
        group.add_argument('--server', default='127.0.0.1:8088',
                           help='The address the server will listen to.')
        group.add_argument('--engine', default='falcon',
                           choices=('php', 'falcon', 'starlette'),
                           help='Webserver framework to run. (default: falcon)')


    def run(self, args: NominatimArgs) -> int:
        if args.engine == 'php':
            if args.config.lib_dir.php is None:
                raise UsageError("PHP frontend not configured.")
            run_php_server(args.server, args.project_dir / 'website')
        else:
            asyncio.run(self.run_uvicorn(args))

        return 0


    async def run_uvicorn(self, args: NominatimArgs) -> None:
        import uvicorn # pylint: disable=import-outside-toplevel

        server_info = args.server.split(':', 1)
        host = server_info[0]
        if len(server_info) > 1:
            if not server_info[1].isdigit():
                raise UsageError('Invalid format for --server parameter. Use <host>:<port>')
            port = int(server_info[1])
        else:
            port = 8088

        server_module = importlib.import_module(f'nominatim_api.server.{args.engine}.server')

        app = server_module.get_application(args.project_dir)

        config = uvicorn.Config(app, host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()


def get_set_parser() -> CommandlineParser:
    """\
    Initializes the parser and adds various subcommands for
    nominatim cli.
    """
    parser = CommandlineParser('nominatim', nominatim.__doc__)

    parser.add_subcommand('import', clicmd.SetupAll())
    parser.add_subcommand('freeze', clicmd.SetupFreeze())
    parser.add_subcommand('replication', clicmd.UpdateReplication())

    parser.add_subcommand('special-phrases', clicmd.ImportSpecialPhrases())

    parser.add_subcommand('add-data', clicmd.UpdateAddData())
    parser.add_subcommand('index', clicmd.UpdateIndex())
    parser.add_subcommand('refresh', clicmd.UpdateRefresh())

    parser.add_subcommand('admin', clicmd.AdminFuncs())

    try:
        exportcmd = importlib.import_module('nominatim_db.clicmd.export')
        apicmd = importlib.import_module('nominatim_db.clicmd.api')
        convertcmd = importlib.import_module('nominatim_db.clicmd.convert')

        parser.add_subcommand('export', exportcmd.QueryExport())
        parser.add_subcommand('convert', convertcmd.ConvertDB())
        parser.add_subcommand('serve', AdminServe())

        parser.add_subcommand('search', apicmd.APISearch())
        parser.add_subcommand('reverse', apicmd.APIReverse())
        parser.add_subcommand('lookup', apicmd.APILookup())
        parser.add_subcommand('details', apicmd.APIDetails())
        parser.add_subcommand('status', apicmd.APIStatus())
    except ModuleNotFoundError as ex:
        if not ex.name or 'nominatim_api' not in ex.name: # pylint: disable=E1135
            raise ex

        parser.parser.epilog = \
            '\n\nNominatim API package not found. The following commands are not available:'\
            '\n    export, convert, serve, search, reverse, lookup, details, status'\
            "\n\nRun 'pip install nominatim-api' to install the package."


    return parser


def nominatim(**kwargs: Any) -> int:
    """\
    Command-line tools for importing, updating, administrating and
    querying the Nominatim database.
    """
    return get_set_parser().run(**kwargs)
