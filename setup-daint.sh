export LSTOPO=/apps/daint/UES/jenkins/7.0.UP02-20.11/mc/easybuild/software/hwloc/2.4.1/bin/lstopo-no-graphics
source /scratch/snx3000/biddisco/shared-data/maestro-test/daint-peg/bin/activate
module load craype-hugepages8M
module load HDF5/1.10.6-CrayGNU-20.11-serial
#module load sarus
unset MSTRO_LOG_LEVEL
export MSTRO_LOG_MODULES="all,^mamba"
export MSTRO_LOG_MODULES="^all"

echo "salloc -A csstaff -N 3 -C mc --tasks-per-node=36 --time=00:30:00 --partition=debug"
echo "salloc -A csstaff -N 2 -C mc --tasks-per-node=20 --time=00:30:00 --partition=debug : -N 1 -C ssd --time=00:30:00"
echo "salloc -A csstaff -N 4 -C ssd --time=08:00:00  : -N 2 -C ssd --time=08:00:00"
echo "salloc -A csstaff -N 8 -C ssd --tasks-per-node=18 --cpus-per-task=1 --mem=60GB --time=12:00:00"
echo ""
echo "srun -N 1 -n 1 -c 1 --mem-per-cpu=0 /scratch/snx3000/biddisco/maestro/mocktage/bin/pool_manager /scratch/snx3000/biddisco/maestro-scratch/ /scratch/snx3000/biddisco/maestro-scratch/pminfo -S &"
echo ""
echo "python ./CDO-workflow-slurm-splinter-workflow.py"
echo ""
echo "rm -rf /scratch/snx3000/biddisco/maestro-scratch/* /scratch/snx3000/biddisco/commands.txt T-f-0* f-0* f.o core.*"
echo ""
echo "# Mount beegfs on our nodes"
echo "./dynamic-resource-provisioning/dsrp_deploy.py start beegfs -t\$SLURM_CLUSTER_NAME -c\$SLURM_JOB_NODELIST_PACK_GROUP_0 -s\$SLURM_JOB_NODELIST_PACK_GROUP_1"

