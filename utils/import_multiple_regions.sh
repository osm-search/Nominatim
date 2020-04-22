#!/bin/bash -xv

# Script to set up Nominatim database for multiple countries

# Steps to follow:

#     *) Get the pbf files from server

#     *) Set up sequence.state for updates

#     *) Merge the pbf files into a single file.

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

# SET TO YOUR NOMINATIM build FOLDER PATH:

NOMINATIMBUILD="/srv/nominatim/build"
SETUPFILE="$NOMINATIMBUILD/utils/setup.php"
UPDATEFILE="$NOMINATIMBUILD/utils/update.php"

# SET TO YOUR update FOLDER PATH:

UPDATEDIR="/srv/nominatim/update"

# SET TO YOUR replication server URL:

BASEURL="https://download.geofabrik.de"
DOWNCOUNTRYPOSTFIX="-latest.osm.pbf"

# End of configuration section
# ******************************************************************************

COMBINEFILES="osmium merge"

mkdir -p ${UPDATEDIR}
cd ${UPDATEDIR}
rm -rf tmp
mkdir -p tmp
cd tmp

for COUNTRY in $COUNTRIES;
do
    
    echo "===================================================================="
    echo "$COUNTRY"
    echo "===================================================================="
    DIR="$UPDATEDIR/$COUNTRY"
    FILE="$DIR/configuration.txt"
    DOWNURL="$BASEURL/$COUNTRY$DOWNCOUNTRYPOSTFIX"
    IMPORTFILE=$COUNTRY$DOWNCOUNTRYPOSTFIX
    IMPORTFILEPATH=${UPDATEDIR}/tmp/${IMPORTFILE}
    FILENAME=${COUNTRY//[\/]/_}
    

    touch2 $IMPORTFILEPATH
    wget ${DOWNURL} -O $IMPORTFILEPATH

    touch2 ${DIR}/sequence.state
    pyosmium-get-changes -O $IMPORTFILEPATH -f ${DIR}/sequence.state -v

    COMBINEFILES="${COMBINEFILES} ${IMPORTFILEPATH}"
    echo $IMPORTFILE
    echo "===================================================================="
done


echo "${COMBINEFILES} -o combined.osm.pbf"
${COMBINEFILES} -o combined.osm.pbf

echo "===================================================================="
echo "Setting up nominatim db"
${SETUPFILE} --osm-file ${UPDATEDIR}/tmp/combined.osm.pbf --all 2>&1

# ${UPDATEFILE} --import-file ${UPDATEDIR}/tmp/combined.osm.pbf 2>&1
echo "===================================================================="