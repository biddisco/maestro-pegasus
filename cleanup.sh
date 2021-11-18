# kill off any pool manager instance still going
touch ~/scratch/pool-manager.stop
sleep 1
rm -rf ~/commands.txt   
rm -rf commands.txt
rm -rf wf-scratch wf-output scitech
rm -rf *.dot
rm -rf *.pdf
rm -rf *.png
rm -rf *.yml
rm -rf /home/scitech/shared-data/sites.yml
rm -rf /home/scitech/shared-data/pegasus.properties
rm -rf /home/scitech/shared-data/binaries/f*
rm -rf /home/scitech/shared-data/binaries/trigger*
rm -rf /home/scitech/shared-data/binaries/kill-pool-manager
rm -rf /home/scitech/shared-data/scratch/*
rm -rf /home/scitech/scratch/*
rm -rf ./core*

cp /home/scitech/shared-data/maestro-test/binaries/data/root-data.txt /home/scitech/scratch/
