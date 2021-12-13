#!/usr/bin/env bash

Description="The purpose of this script is to collect system information for bug reports.\n
Submit issues to https://github.com/osm-search/Nominatim/issues"


####### Gather the Information ##################################################
# Separate the information gathering from the report generation.  Dividing these
# makes it easier to make trivial changes by not have to learn the other portion
# of this script.

# Nominatium version
# NOTE: Getting this version will NOT work if it is being ran from in another
# folder than Nominatim/utils.  It call python3 to import version.py locally and
# prints it in the version format. 
NominatimVersion=`cd ../nominatim/ && python3 -c "import version; print('{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(version.NOMINATIM_VERSION))"`

# PostgreSQL version
PostgreSQLVersion=`postgres --version`
if [ "$?" -ne "0" ]
then
  PostgreSQLVersion="Not installed"
fi

# - PostGIS version:
# The command for this should look something like this:
#       psql -U nominatim -d mydatabase -c 'SELECT PostGIS_full_version();'
# ASSUME the username is nominatim
# This needs to be ran under the account with the appropriate permissions.
# This has been left blank.
PostGISVersion=

# There are different ways to getting the Linux OS information.
# https://www.cyberciti.biz/faq/how-to-check-os-version-in-linux-command-line/
# /etc/os-release has a number of representations of the OS
# PRETTY_NAME is pity.
OperatingSystem=`grep '^PRETTY_NAME' /etc/os-release | cut -d'=' -f2`

RAM=`grep ^MemTotal /proc/meminfo | cut -d':' -f2`

# In /proc/cupinfo: siblings seems to refer to total cores like hyperthreaded cores.
# The hyperthreaded cores could be included if that is needed.
NumCPUs=`grep '^cpu cores' /proc/cpuinfo | head -1 | cut -d':' -f2`


# - type and size of disks:
# could use `sudo fdisk -l` or `mount` to print this, but snaps have made this
# worse than useless with loop devices on Ubuntu.  
# `df -h` - show the free space on drives
# `lsblk` - this tell you what the server has not necessarily this machine.  So in a container environment
#  (like docker) this wouldn't be the correct report.
# This guide shows ways to get various storage device information: https://www.cyberciti.biz/faq/find-hard-disk-hardware-specs-on-linux/

# - bare metal/AWS/other cloud service:
# Unsure of how to detect this, but it might be useful for reporting disk storage.
# One options would be to prompt the user something like this:
# Enter system configuration (1) bare metal (2) AWS (3) Other Cloud (4) Docker (5) Other: _

# ------ What do these commands do? -------------------------------------------
# "cut -d':' -f2"      command take the line and splits it at the semicolon(:)
#                      and returns the portion in the second (2nd) "field"
#
# "head -1"            returns the first line that matches
#

####### Print the Markdown Report ######################################################
# 1>&2 redirects echo to print to stderr instead of stdout

echo 1>&2
echo -e $Description 1>&2
echo Copy and paste or redirect the output of the file:  1>&2
echo "     \$ ./collect_os_info.sh > report.md" 1>&2
echo 1>&2


echo "**Software Environment (please complete the following information):**"
echo - Nominatim version: $NominatimVersion
echo - PostgreSQL version: $PostgreSQLVersion 
echo - PostGIS version: $PostGISVersion 
echo - OS: $OperatingSystem
echo
echo


echo "**Hardware Configuration (please correct the following information):**"
echo - RAM: $RAM
echo - number of CPUs: $NumCPUs
echo - type and size of disks:
echo - bare metal/AWS/other cloud service: 
echo
echo
echo **Postgresql Configuration:**
echo

