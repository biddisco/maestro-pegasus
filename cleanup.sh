rm -rf ~/commands.txt   
rm -rf wf-scratch wf-output scitech
find . -name \*.dot -delete
find . -name \*.pdf -delete
find . -name \*.png -delete
find . -name \*.yml -delete
rm -rf /home/scitech/shared-data/maestro-binaries/f*
rm -rf /home/scitech/shared-data/maestro-binaries/trigger*
rm -rf /home/scitech/shared-data/maestro-binaries/kill-pool-manager
rm -rf /home/scitech/shared-data/scratch/*
cp /home/scitech/shared-data/maestro-binaries/data/root-data.txt /home/scitech/shared-data/scratch/
