#!/bin/bash

# A typo in the Tiger 2016 data. Russel Way in the county Belnap should have
# the zip code 03089.

BELKNAP_FILE="$1/33001.sql"

if [[ ! -e $BELKNAP_FILE ]]; then
    echo "$BELKNAP_FILE not found"
    exit 1
fi

# change file inline
sed -i -- "s/'Russel Way', 'Belknap, NH', '83809'/'Russel Way', 'Belknap, NH', '03809'/" $BELKNAP_FILE

# doublecheck
if [[ `grep 83809 $BELKNAP_FILE` -ne '0' ]]; then
    echo "Patching $BELKNAP_FILE failed"
    exit 1
fi

exit 0