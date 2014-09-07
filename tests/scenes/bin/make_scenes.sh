#/bin/bash -e
#
# Regenerates wkts for scenarios.
#

datadir="$( cd "$( dirname "$0" )" && cd ../data && pwd )"

if [! -d "$datadir" ]; then
 echo "Cannot find data dir."; 
 exit -1;
fi

echo "Using datadir $datadir"
pushd $datadir

# remove old wkts
rm $datadir/*.wkt

# create wkts from SQL scripts
for fl in *.sql; do
    echo "Processing $fl.."
    cat $fl | psql -d nominatim -t -o ${fl/.sql/.wkt}
done

# create wkts from .osm files
for fl in *.osm; do
    echo "Processing $fl.."
    ../bin/osm2wkt $fl
done

popd
