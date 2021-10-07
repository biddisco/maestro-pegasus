#!/bin/bash
# $1 log-directory
# $2 stop-file-name

kname="$1/$2"

time=$(date +"%H:%M:%S")
echo "$time + stop-pool-manager" >> ~/commands.txt

if [[ -f "$kname" ]]; then
    rm -rf "$kname"
fi

touch "$kname"
echo "stop" >> "$kname"

time=$(date +"%H:%M:%S")
echo "$time - stop-pool-manager" >> ~/commands.txt
