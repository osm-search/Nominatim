"""
Implementation of the 'replication' sub-command.
"""
import datetime as dt
import logging
import socket
import time

from nominatim.db import status
from nominatim.db.connection import connect
from nominatim.errors import UsageError

LOG = logging.getLogger()

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to make pyosmium optional for replication only.
# pylint: disable=E0012,C0415

class UpdateReplication:
    """\
    Update the database using an online replication service.

    An OSM replication service is an online service that provides regular
    updates (OSM diff files) for the planet or update they provide. The OSMF
    provides the primary replication service for the full planet at
    https://planet.osm.org/replication/ but there are other providers of
    extracts of OSM data who provide such a service as well.

    This sub-command allows to set up such a replication service and download
    and import updates at regular intervals. You need to call '--init' once to
    set up the process or whenever you change the replication configuration
    parameters. Without any arguments, the sub-command will go into a loop and
    continuously apply updates as they become available. Giving `--once` just
    downloads and imports the next batch of updates.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Arguments for initialisation')
        group.add_argument('--init', action='store_true',
                           help='Initialise the update process')
        group.add_argument('--no-update-functions', dest='update_functions',
                           action='store_false',
                           help="Do not update the trigger function to "
                                "support differential updates (EXPERT)")
        group = parser.add_argument_group('Arguments for updates')
        group.add_argument('--check-for-updates', action='store_true',
                           help='Check if new updates are available and exit')
        group.add_argument('--once', action='store_true',
                           help="Download and apply updates only once. When "
                                "not set, updates are continuously applied")
        group.add_argument('--catch-up', action='store_true',
                           help="Download and apply updates until no new "
                                "data is available on the server")
        group.add_argument('--no-index', action='store_false', dest='do_index',
                           help=("Do not index the new data. Only usable "
                                 "together with --once"))
        group.add_argument('--osm2pgsql-cache', metavar='SIZE', type=int,
                           help='Size of cache to be used by osm2pgsql (in MB)')
        group = parser.add_argument_group('Download parameters')
        group.add_argument('--socket-timeout', dest='socket_timeout', type=int, default=60,
                           help='Set timeout for file downloads')

    @staticmethod
    def _init_replication(args):
        from ..tools import replication, refresh

        LOG.warning("Initialising replication updates")
        with connect(args.config.get_libpq_dsn()) as conn:
            replication.init_replication(conn, base_url=args.config.REPLICATION_URL)
            if args.update_functions:
                LOG.warning("Create functions")
                refresh.create_functions(conn, args.config, True, False)
        return 0


    @staticmethod
    def _check_for_updates(args):
        from ..tools import replication

        with connect(args.config.get_libpq_dsn()) as conn:
            return replication.check_for_updates(conn, base_url=args.config.REPLICATION_URL)

    @staticmethod
    def _report_update(batchdate, start_import, start_index):
        def round_time(delta):
            return dt.timedelta(seconds=int(delta.total_seconds()))

        end = dt.datetime.now(dt.timezone.utc)
        LOG.warning("Update completed. Import: %s. %sTotal: %s. Remaining backlog: %s.",
                    round_time((start_index or end) - start_import),
                    "Indexing: {} ".format(round_time(end - start_index))
                    if start_index else '',
                    round_time(end - start_import),
                    round_time(end - batchdate))


    @staticmethod
    def _compute_update_interval(args):
        if args.catch_up:
            return 0

        update_interval = args.config.get_int('REPLICATION_UPDATE_INTERVAL')
        # Sanity check to not overwhelm the Geofabrik servers.
        if 'download.geofabrik.de' in args.config.REPLICATION_URL\
           and update_interval < 86400:
            LOG.fatal("Update interval too low for download.geofabrik.de.\n"
                      "Please check install documentation "
                      "(https://nominatim.org/release-docs/latest/admin/Import-and-Update#"
                      "setting-up-the-update-process).")
            raise UsageError("Invalid replication update interval setting.")

        return update_interval


    @staticmethod
    def _update(args):
        from ..tools import replication
        from ..indexer.indexer import Indexer
        from ..tokenizer import factory as tokenizer_factory

        update_interval = UpdateReplication._compute_update_interval(args)

        params = args.osm2pgsql_options(default_cache=2000, default_threads=1)
        params.update(base_url=args.config.REPLICATION_URL,
                      update_interval=update_interval,
                      import_file=args.project_dir / 'osmosischange.osc',
                      max_diff_size=args.config.get_int('REPLICATION_MAX_DIFF'),
                      indexed_only=not args.once)

        if not args.once:
            if not args.do_index:
                LOG.fatal("Indexing cannot be disabled when running updates continuously.")
                raise UsageError("Bad argument '--no-index'.")
            recheck_interval = args.config.get_int('REPLICATION_RECHECK_INTERVAL')

        tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)

        while True:
            with connect(args.config.get_libpq_dsn()) as conn:
                start = dt.datetime.now(dt.timezone.utc)
                state = replication.update(conn, params)
                if state is not replication.UpdateState.NO_CHANGES:
                    status.log_status(conn, start, 'import')
                batchdate, _, _ = status.get_status(conn)
                conn.commit()

            if state is not replication.UpdateState.NO_CHANGES and args.do_index:
                index_start = dt.datetime.now(dt.timezone.utc)
                indexer = Indexer(args.config.get_libpq_dsn(), tokenizer,
                                  args.threads or 1)
                indexer.index_full(analyse=False)

                with connect(args.config.get_libpq_dsn()) as conn:
                    status.set_indexed(conn, True)
                    status.log_status(conn, index_start, 'index')
                    conn.commit()
            else:
                index_start = None

            if state is replication.UpdateState.NO_CHANGES and \
               args.catch_up or update_interval > 40*60:
                while indexer.has_pending():
                    indexer.index_full(analyse=False)

            if LOG.isEnabledFor(logging.WARNING):
                UpdateReplication._report_update(batchdate, start, index_start)

            if args.once or (args.catch_up and state is replication.UpdateState.NO_CHANGES):
                break

            if state is replication.UpdateState.NO_CHANGES:
                LOG.warning("No new changes. Sleeping for %d sec.", recheck_interval)
                time.sleep(recheck_interval)


    @staticmethod
    def run(args):
        socket.setdefaulttimeout(args.socket_timeout)

        if args.init:
            return UpdateReplication._init_replication(args)

        if args.check_for_updates:
            return UpdateReplication._check_for_updates(args)

        UpdateReplication._update(args)
        return 0
