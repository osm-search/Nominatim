#!/bin/bash

INPATH=$1
OUTPATH=$2

if [[ ! -d "$INPATH" ]]; then
    echo "input path does not exist"
    exit 1
fi

if [[ ! -d "$OUTPATH" ]]; then
    echo "output path does not exist"
    exit 1
fi

INREGEX='_([0-9]{5})_edges.zip'
WORKPATH="$OUTPATH/tmp-workdir/"
mkdir -p "$WORKPATH"



INFILES=($INPATH/*.zip)
echo "Found ${#INFILES[*]} files."

for F in ${INFILES[*]}; do
    # echo $F

    if [[ "$F" =~ $INREGEX ]]; then
        COUNTYID=${BASH_REMATCH[1]}
        SHAPEFILE="$WORKPATH/$(basename $F '.zip').shp"
        SQLFILE="$OUTPATH/$COUNTYID.sql"

        unzip -o -q -d "$WORKPATH" "$F"
        if [[ ! -e "$SHAPEFILE" ]]; then
            echo "Unzip failed. $SHAPEFILE not found."
            exit 1
        fi

        ./tiger_address_convert.py "$SHAPEFILE" "$SQLFILE"

        rm $WORKPATH/*
    fi
done

OUTFILES=($OUTPATH/*.sql)
echo "Wrote ${#OUTFILES[*]} files."

rmdir $WORKPATH
