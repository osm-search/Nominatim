#!/usr/bin/env python3

import osmium
import sys
import datetime


class Datecounter(osmium.SimpleHandler):

    filedate = None

    def date(self, o):
        ts = o.timestamp
        if self.filedate is None or ts > self.filedate:
            self.filedate = ts

    node = date
    way = date
    relation = date


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python osm_file_date.py <osmfile>")
        sys.exit(-1)

    h = Datecounter()

    h.apply_file(sys.argv[1])

    if h.filedate is None:
        exit(5)

    print(h.filedate)
