#!/bin/bash
# $1 Input file
# $2 Output file
# $3 Sleep Time

dname=$(dirname $1)
fname=$(basename $1)

echo "reading file $1"
sleep $3
echo "CDO cache of $2" > 2
cat $1 > $2.
echo "Finished creating $2"    
