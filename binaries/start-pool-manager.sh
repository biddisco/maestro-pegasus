#!/bin/bash
# $1 log-directory
# $2 stop file name

pname="$1/$2"
tname="$1/pool-manager-stopped"

time=$(date +"%H:%M:%S")
echo "$time + pool-manager     START" >> ~/commands.txt

if [[ -f "$pname" ]]; then
    rm -f "$pname"
fi

echo "$time   ./cdo-watcher.sh $pname $tname" >> ~/commands.txt
/home/scitech/shared-data/binaries/cdo-watcher.sh "$pname" "$tname"

time=$(date +"%H:%M:%S")
echo "$time - pool-manager     STOP" >> ~/commands.txt
