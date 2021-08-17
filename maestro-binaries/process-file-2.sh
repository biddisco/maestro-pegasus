#!/bin/bash
# $1 Input file
# $2 Output file 1
# $3 Output file 2
# $4 Sleep Time

time=$(date +"%H:%M:%S")
echo "$time - process-file-2 $1 $2 $3 $4" >> ~/commands.txt

echo "$time - Copying $1 to $2 (L)" >> $2
cat $1 >> $2
echo "$time - Copying $1 to $3 (R)" >> $3
cat $1 >> $3

sleep $4

time=$(date +"%H:%M:%S")
echo "$time - process-file-2 $1 $2 $3 $4" >> ~/commands.txt
