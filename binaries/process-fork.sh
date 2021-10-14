#!/bin/bash
# $1 Input file
# $2 Output file 1
# $... Output file 1+n
# $last Sleep Time

argc=$#
argv=("$@")
NUM_ARGS="$#"
frst="${@:1:1}"
last="${@:(-1):1}"

dname="/home/scitech/scratch/"

arg_string=""
for (( j=1; j<((argc-1)); j++ )); do
    arg_string+="${argv[j]} "
done

time=$(date +"%H:%M:%S")
echo "$time + process-fork $frst $arg_string $last" >> ~/commands.txt

for (( j=1; j<((argc-1)); j++ )); do
    echo $time - Copying $frst to "${argv[j]}" >> "${argv[j]}"
    cat $frst >> "${argv[j]}"
    cp "${argv[j]}" "$dname/${argv[j]}"
done

sleep 5
# sleep $last

time=$(date +"%H:%M:%S")
echo "$time - process-fork $frst $arg_string $last" >> ~/commands.txt
