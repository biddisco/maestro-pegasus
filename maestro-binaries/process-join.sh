#!/bin/bash
# $1 Input file
# $2 Output file 1
# $... Output file 1+n
# $last Sleep Time

argc=$#
argv=("$@")
NUM_ARGS="$#"
fout="${@:(-2):1}"
last="${@:(-1):1}"

dname="/home/scitech/shared-data/scratch/"

arg_string=""
for (( j=0; j<((argc-2)); j++ )); do
    arg_string+="${argv[j]} "
done

time=$(date +"%H:%M:%S")
echo "$time + process-join $arg_string $fout $last" >> ~/commands.txt

for (( j=0; j<((argc-2)); j++ )); do
    echo $time - Reducing "${argv[j]}" to "$fout" >> "$fout"
    cat "${argv[j]}" >> $fout
    cp "$fout" "$dname/${argv[j]}"
done

sleep 5
# sleep $last

time=$(date +"%H:%M:%S")
echo "$time - process-join $arg_string $fout $last" >> ~/commands.txt
