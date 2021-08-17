#!/bin/bash
# $1 Input file
# $2 Input file 2
# $3 Output file
# $4 Sleep Time

time=$(date +"%H:%M:%S")
echo "$time - reduce-file-2 $1 $2 $3 $4" >> ~/commands.txt

echo "Reducing $1 to Output" >> $3
cat $1 >> $3
echo "Reducing $2 to Output" >> $3
cat $2 >> $3

sleep $4

time=$(date +"%H:%M:%S")
echo "$time - reduce-file-2 $1 $2 $3 $4" >> ~/commands.txt
