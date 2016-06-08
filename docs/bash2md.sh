#!/bin/sh
#
# Extract markdown-formatted documentation from a source file
#
# Usage: bash2md.sh <infile> <outfile>

sed '/^#!/d;s:^#\( \|$\)::;s/.*#DOCS://' $1 > $2
