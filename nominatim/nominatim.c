/*
#-----------------------------------------------------------------------------
# nominatim - [description]
#-----------------------------------------------------------------------------
# Copyright 2010, Brian Quinion
# Based on osm2pgsql
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#-----------------------------------------------------------------------------
*/

#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <getopt.h>
#include <libgen.h>
#include <pthread.h>
#include <time.h>

#include <libpq-fe.h>

#include "nominatim.h"
#include "postgresql.h"
#include "sprompt.h"
#include "index.h"
#include "export.h"
#include "import.h"

int verbose;

void exit_nicely(void)
{
    fprintf(stderr, "Error occurred, cleaning up\n");
    exit(1);
}

void short_usage(char *arg0)
{
    const char *name = basename(arg0);

    fprintf(stderr, "Usage error. For further information see:\n");
    fprintf(stderr, "\t%s -h|--help\n", name);
}

static void long_usage(char *arg0)
{
    const char *name = basename(arg0);

    fprintf(stderr, "Usage:\n");
    fprintf(stderr, "\t%s [options] planet.osms\n", name);
    fprintf(stderr, "\nThis will import the structured osm data into a PostgreSQL database\n");
    fprintf(stderr, "suitable for nominatim search engine\n");
    fprintf(stderr, "\nOptions:\n");
    fprintf(stderr, "   -d|--database\tThe name of the PostgreSQL database to connect\n");
    fprintf(stderr, "                \tto (default: nominatim).\n");
    fprintf(stderr, "   -U|--username\tPostgresql user name.\n");
    fprintf(stderr, "   -W|--password\tForce password prompt.\n");
    fprintf(stderr, "   -H|--host\t\tDatabase server hostname or socket location.\n");
    fprintf(stderr, "   -P|--port\t\tDatabase server port.\n");
    fprintf(stderr, "   -i|--index\t\tIndex the database.\n");
    fprintf(stderr, "   -e|--export\t\tGenerate a structured file.\n");
    fprintf(stderr, "   -I|--import\t\tImport a structured file.\n");
    fprintf(stderr, "   -r|--minrank\t\tMinimum / starting rank. (default: 0))\n");
    fprintf(stderr, "   -R|--maxrank\t\tMaximum / finishing rank. (default: 30)\n");
    fprintf(stderr, "   -t|--threads\t\tNumber of threads to create for indexing.\n");
    fprintf(stderr, "   -F|--file\t\tfile to use (either to import or export).\n");
    fprintf(stderr, "   -T|--tagfile\t\tfile containing 'special' tag pairs\n");
    fprintf(stderr, "                \t(default: partitionedtags.def).\n");
    fprintf(stderr, "   -h|--help\t\tHelp information.\n");
    fprintf(stderr, "   -v|--verbose\t\tVerbose output.\n");
    fprintf(stderr, "\n");

    if (sizeof(int*) == 4)
    {
        fprintf(stderr, "\n\nYou are running this on 32bit system - this will not work\n");
    }
}

int main(int argc, char *argv[])
{
    int long_usage_bool=0;
    int pass_prompt=0;
    const char *db = "nominatim";
    const char *username=NULL;
    const char *host=NULL;
    const char *password=NULL;
    const char *port = "5432";
    const char *conninfo = NULL;
    int index = 0;
    int export = 0;
    int import = 0;
    int minrank = 0;
    int maxrank = 30;
    int threads = 1;
    const char *file = NULL;
    const char *tagsfile = "partitionedtags.def";

    //import = 1;
    //structuredinputfile = "out.osms";

    PGconn *conn;

    fprintf(stderr, "nominatim version %s\n\n", NOMINATIM_VERSION);

    while (1)
    {
        int c, option_index = 0;
        static struct option long_options[] =
        {
            {"help",     0, 0, 'h'},

            {"verbose",  0, 0, 'v'},

            {"database", 1, 0, 'd'},
            {"username", 1, 0, 'U'},
            {"password", 0, 0, 'W'},
            {"host",     1, 0, 'H'},
            {"port",     1, 0, 'P'},

            {"index",  0, 0, 'i'},
            {"export",  0, 0, 'e'},
            {"import",  1, 0, 'I'},
            {"threads",  1, 0, 't'},
            {"file",  1, 0, 'F'},
            {"tagsfile",  1, 0, 'T'},

            {"minrank",  1, 0, 'r'},
            {"maxrank",  1, 0, 'R'},



            {0, 0, 0, 0}
        };

        c = getopt_long(argc, argv, "vhd:U:WH:P:ieIt:F:T:r:R:", long_options, &option_index);
        if (c == -1)
            break;

        switch (c)
        {
        case 'v':
            verbose=1;
            break;
        case 'd':
            db=optarg;
            break;
        case 'U':
            username=optarg;
            break;
        case 'W':
            pass_prompt=1;
            break;
        case 'H':
            host=optarg;
            break;
        case 'P':
            port=optarg;
            break;
        case 'h':
            long_usage_bool=1;
            break;
        case 'i':
            index=1;
            break;
        case 'e':
            export=1;
            break;
        case 'I':
            import=1;
            break;
        case 't':
            threads=atoi(optarg);
            break;
        case 'r':
            minrank=atoi(optarg);
            break;
        case 'R':
            maxrank=atoi(optarg);
            break;
        case 'F':
            file=optarg;
            break;
        case 'T':
            tagsfile=optarg;
            break;
        case '?':
        default:
            short_usage(argv[0]);
            exit(EXIT_FAILURE);
        }
    }

    if (long_usage_bool)
    {
        long_usage(argv[0]);
        exit(EXIT_FAILURE);
    }

    if (threads < 1) threads = 1;

    /*
        if (argc == optind) {  // No non-switch arguments
            short_usage(argv[0]);
            exit(EXIT_FAILURE);
        }
    */
    if (index && import)
    {
        fprintf(stderr, "Error: --index and --import options can not be used on the same database!\n");
        exit(EXIT_FAILURE);
    }

    if (pass_prompt)
        password = simple_prompt("Password:", 100, 0);
    else
    {
        password = getenv("PGPASS");
    }

    // Test the database connection
    conninfo = build_conninfo(db, username, password, host, port);
    conn = PQconnectdb(conninfo);
    if (PQstatus(conn) != CONNECTION_OK)
    {
        fprintf(stderr, "Connection to database failed: %s\n", PQerrorMessage(conn));
        exit(EXIT_FAILURE);
    }
    PQfinish(conn);

    if (!index && !export && !import)
    {
        fprintf(stderr, "Please select index, export or import.\n");
        exit(EXIT_FAILURE);
    }
    if (index) nominatim_index(minrank, maxrank, threads, conninfo, file);
    if (export) nominatim_export(minrank, maxrank, conninfo, file);
    if (import) nominatim_import(conninfo, tagsfile, file);

    return 0;
}
