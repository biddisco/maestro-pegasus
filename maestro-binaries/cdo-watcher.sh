#!/bin/bash

file_to_watch_for=$1
echo "Watching for $1"

inotifywait -m /home/scitech/shared-data/maestro-binaries/data -e create -e moved_to |
    while read dir action file; do
        echo "The file '$file' appeared in directory '$dir' via '$action'"
        # we can now shut down the cdo-watcher
	if [ "$file_to_watch_for" = "$file" ]; then
    	    echo "Shutting down CDO."
	     kill $$
	     break
	else
	    echo "Not the file we are looking for" $file $file_to_watch_for
        fi
    done
echo "CDO watcher terminating"
