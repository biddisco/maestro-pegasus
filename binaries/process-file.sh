#!/bin/bash
# $1 Input file
# $2 Output file
# $3 Sleep Time

dname="/home/scitech/scratch/"

time=$(date +"%H:%M:%S")
echo "$time + process-file $1 $2 $3" >> ~/commands.txt

echo "$time   process-file $1 writing $2" >> ~/commands.txt
echo "Copying $1 to $2" >> $2
cat $1 >> $2
cp $2 "$dname/$2"

sleep 5
 #sleep $3

time=$(date +"%H:%M:%S")
echo "$time - process-file $1 $2 $3" >> ~/commands.txt
