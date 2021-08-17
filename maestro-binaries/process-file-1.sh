#!/bin/bash
# $1 Input file
# $2 Output file
# $3 Sleep Time

time=$(date +"%H:%M:%S")
echo "$time - process-file-1 $1 $2 $3" >> ~/commands.txt

echo "$time - Copying $1 to $2" >> $2
cat $1 >> $2

sleep $3

time=$(date +"%H:%M:%S")
echo "$time - process-file-1 $1 $2 $3" >> ~/commands.txt
