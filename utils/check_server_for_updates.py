#!/usr/bin/python3

import sys
from osmium.replication import server

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python check_server_for_updates.py <server url> <sequence id>")
        sys.exit(254)

    seqid = int(sys.argv[2])

    state = server.ReplicationServer(sys.argv[1]).get_state_info()

    if state is None:
        print("ERROR: Cannot get state from URL %s." % (sys.argv[1], ))
        sys.exit(253)

    if state.sequence <= seqid:
        print("Database up to date.")
        sys.exit(1)

    print("New data available (%i => %i)." % (seqid, state.sequence))
    sys.exit(0)
