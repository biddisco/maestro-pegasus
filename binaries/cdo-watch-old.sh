#!/bin/bash

# $1 - File to watch for
# $2 - Dummy file to generate when done

trap "exit 0" SIGINT

dname=$(dirname $1)
fname=$(basename $1)
dname="/home/scitech/scratch/"

time=$(date +"%H:%M:%S")
echo "$time + cdo-watcher  $1 $2 Watching in $dname for $fname" >> ~/commands.txt

if [[ -f $2 ]]; then
  echo "$time   cdo-watcher  $fname (Pre)-Erasing $2" >> ~/commands.txt
  rm -f $2
fi


if [[ -f "$dname/$fname" ]]; then
    echo "$time   cdo-watcher  $fname exists" >> ~/commands.txt

    echo "$time   cdo-watcher  $fname Creating $2" >> ~/commands.txt
    echo "Ready" >> $2
    cp $2 "$dname/$2"

    time=$(date +"%H:%M:%S")
    echo "$time - cdo-watcher  $fname Completed Watching in $dname" >> ~/commands.txt

    sleep 5
    # this shuts down the script itself as we cannot exit cleanly otherwise it seems
    exit 0
fi


inotifywait $dname -m -e create |
    while read dir action file; do
        echo "The file '$file' appeared in directory '$dir' via '$action'"
        # we can now shut down the cdo-watcher 
        if [ "$fname" = "$file" ]; then

            time=$(date +"%H:%M:%S")

            echo "$time   cdo-watcher  $fname Creating $2" >> ~/commands.txt
            echo "Ready" >> $2
            cp $2 "$dname/$2"

            time=$(date +"%H:%M:%S")
            echo "$time - cdo-watcher  $fname Completed Watching in $dname" >> ~/commands.txt

            sleep 5
            # this shuts down the script itself as we cannot exit cleanly otherwise it seems
    	    kill -INT -$$ >/dev/null 2>&1
            exit 0
            break
        else
            time=$(date +"%H:%M:%S")
            echo "$time   cdo-watcher  $fname : WRONG file" $file >> ~/commands.txt
        fi
    done

time=$(date +"%H:%M:%S")
echo "$time - cdo-watcher  $fname exited notify loop" >> ~/commands.txt

