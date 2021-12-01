#!/bin/bash
# $1 log-directory
# $2 stop file name

pname="$1/$2"

time=$(date +"%H:%M:%S")
echo "$time + stop-pool-manager" >> ~/commands.txt

if [[ -f "$pname" ]]; then
    rm -rf "pkname"
fi

touch "$pname"
echo "stop" >> "$pname"

time=$(date +"%H:%M:%S")
echo "$time - stop-pool-manager" >> ~/commands.txt
