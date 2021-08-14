#!/bin/bash -xv

# Script to set up Nominatim database for multiple countries

# Steps to follow:

#     *) Get the pbf files from server

#     *) Set up sequence.state for updates

#     *) Setup nominatim db using 'setup.php --osm-file'

# Hint:
#
# Use "bashdb ./update_database.sh" and bashdb's "next" command for step-by-step
# execution.

# ******************************************************************************

touch2() { mkdir -p "$(dirname "$1")" && touch "$1" ; }

# ******************************************************************************
# Configuration section: Variables in this section should be set according to your requirements

# REPLACE WITH LIST OF YOUR "COUNTRIES":

COUNTRIES="europe/monaco europe/andorra"

# SET TO YOUR replication server URL:

BASEURL="https://download.geofabrik.de"
DOWNCOUNTRYPOSTFIX="-latest.osm.pbf"

# End of configuration section
# ******************************************************************************

UPDATEDIR=update
IMPORT_CMD="nominatim import"

mkdir -p ${UPDATEDIR}
pushd ${UPDATEDIR}
rm -rf tmp
mkdir -p tmp
popd

for COUNTRY in $COUNTRIES;
do
    echo "===================================================================="
    echo "$COUNTRY"
    echo "===================================================================="
    DIR="$UPDATEDIR/$COUNTRY"
    DOWNURL="$BASEURL/$COUNTRY$DOWNCOUNTRYPOSTFIX"
    IMPORTFILE=$COUNTRY$DOWNCOUNTRYPOSTFIX
    IMPORTFILEPATH=${UPDATEDIR}/tmp/${IMPORTFILE}

    touch2 $IMPORTFILEPATH
    wget ${DOWNURL} -O $IMPORTFILEPATH

    touch2 ${DIR}/sequence.state
    pyosmium-get-changes -O $IMPORTFILEPATH -f ${DIR}/sequence.state -v

    IMPORT_CMD="${IMPORT_CMD} --osm-file ${IMPORTFILEPATH}"
    echo $IMPORTFILE
    echo "===================================================================="
done

echo "===================================================================="
echo "Setting up nominatim db"
${IMPORT_CMD} 2>&1
echo "===================================================================="
