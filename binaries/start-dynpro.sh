#!/bin/bash
# $1 log-directory
# $2 stop file name
# $3 optional : /path/to/real/CDO-enabled/pool-manager
# $4 optional : pminfo pool manager info file name (in $log_dir) 

pname="$1/$2"
tname="$1/pool-manager-stopped"

time=$(date +"%H:%M:%S")
echo "$time + pool-manager     START" >> ~/commands.txt

if [[ -f "$pname" ]]; then
    rm -f "$pname"
fi

if [ "$3" ]; then
    command="$3 $1 $4"
    echo "Starting CDO enabled pool manager : $command"
    $command
    echo "Done"
else
    echo "$time   ./cdo-watcher.sh $pname $tname" >> ~/commands.txt
    /home/scitech/shared-data/binaries/cdo-watcher.sh "$pname" "$tname"
fi

time=$(date +"%H:%M:%S")
echo "$time - pool-manager     STOP" >> ~/commands.txt
