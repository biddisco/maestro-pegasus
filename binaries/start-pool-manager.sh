#!/bin/bash
# $1 log-directory
# $2 pm-info-filename

time=$(date +"%H:%M:%S")
echo "$time - starting pool-manager" >> ~/commands.txt

pname="$1/pool_manager.stop"
tname="$1/pool-manager-terminated"

if [[ -f "$pname" ]]; then
    rm -f "$pname"
fi

echo "$time   ./cdo-watcher.sh $pname $tname" > ~/commands.txt
/home/scitech/shared-data/maestro-test/binaries/cdo-watcher.sh "$pname" "$tname"

time=$(date +"%H:%M:%S")
echo "$time - terminating pool-manager" >> ~/commands.txt
