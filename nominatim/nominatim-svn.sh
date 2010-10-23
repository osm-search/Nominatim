#!/bin/sh

DATE=$(date +%Y%m%d)
MODULE="$(basename $0 -svn.sh)"
SVNROOT=http://svn.openstreetmap.org/applications/utils/nominatim/

set -x
rm -rf $MODULE

svn export $SVNROOT $MODULE/

## tar it up
tar cjf $MODULE-${DATE}svn.tar.bz2 $MODULE

## cleanup
rm -rf $MODULE

