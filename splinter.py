# #!/usr/bin/env python3

import subprocess
import time
import concurrent.futures
import humanfriendly
import hostlist
import os

# -------------------------------------------------------------------
# execute a multiline command/script on a node using ssh in a dedicated bash shell
def execute_ssh_shell(host, script):
    commands = 'ssh -T ' + host + '\n' + script
    process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
    #print('Sending command', commands)
    out, err = process.communicate(commands)
    return out

# -------------------------------------------------------------------
# execute a multiline command/script locally in a dedicated bash shell
def execute_local_shell(script):
    process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
    out, err = process.communicate(script)
    return out

# -------------------------------------------------------------------
# execute srun command locally to launch job on node remotely
def execute_srun(executor, job_id, host, command):
    commands = f'srun --jobid={job_id} -w {host} -n 1 -c 1 --overcommit --overlap'
    commands = commands.split(' ') + command
    cstr1 = ' '.join(commands)
    print('SLURM executing', cstr1)
    future = executor.submit(subprocess.run, commands, stdout=subprocess.PIPE)
    return future

# -------------------------------------------------------------------
# get a SLURM nodelist and expand it into a list of node names
def get_slurm_nodelist():
    if os.getenv('SLURM_JOB_NODELIST_PACK_GROUP_0') is not None:
        slurm_node_list = os.getenv('SLURM_JOB_NODELIST_PACK_GROUP_0')
    else:        
        slurm_node_list = 'localhost'
        if os.getenv('SLURM_JOB_NODELIST') is not None:
            slurm_node_list = os.getenv('SLURM_JOB_NODELIST')
        if slurm_node_list=='':
            slurm_node_list = 'localhost'
        if slurm_node_list=='container':
            slurm_node_list = 'localhost'

    node_list = hostlist.expand_hostlist(slurm_node_list)
    print('Got node list', node_list)
    return node_list

# -------------------------------------------------------------------
# get a SLURM nodelist and expand it into a list of node names
def get_slurm_job():
    slurm_node_id = os.getenv('SLURM_JOB_ID')
    if slurm_node_id is None or slurm_node_id=='':
        return 0
    job_id = int(slurm_node_id)
    print('Got job_id', job_id)
    return job_id

# -------------------------------------------------------------------
def get_lstopo(node):
    # default lstopo location
    lstopo = '/usr/bin/lstopo-no-graphics'

    # override if env var set
    if os.getenv('LSTOPO') is not None:
        lstopo = os.getenv('LSTOPO')
        print('lstopo is', lstopo)
    else:
        if 'oryx' in node:
            lstopo = 'LSTOPO=/home/biddisco/opt/spack.git/var/spack/environments/dev/.spack-env/view/bin/lstopo-no-graphics'
        elif 'daint' in node or 'nid' in node:
            lstopo = 'LSTOPO=/apps/daint/UES/jenkins/7.0.UP02-20.11/mc/easybuild/software/hwloc/2.4.1/bin/lstopo-no-graphics'
        print('Please set env var LSTOPO : using :', lstopo)
    return lstopo

# -------------------------------------------------------------------
# get number of sockets, numa domains, cores, pus, memory for a node
# we should get hwloc paths from the remote environment, or radle, but for now - use hardcoded
def get_node_compute_data(node):
    # default lstopo location
    lstopo = get_lstopo(node)

    command = 'LSTOPO=' + lstopo + '''
    sockets=$( $LSTOPO | grep Package | wc -l )
    numanodes=$( $LSTOPO | grep NUMANode | wc -l )
    cores=$( $LSTOPO | grep Core | wc -l )
    pus=$( $LSTOPO | grep ' PU' | wc -l )
    memory=$( $LSTOPO -v | grep Machine | grep -oE "total=([0-9]+.B)" )
    echo "$( hostname ):$sockets:$numanodes:$cores:$pus:$memory"'''
    if node!='localhost':
        info = execute_ssh_shell(node, command)
    else:
        info = execute_local_shell(command)

    print('Node data', info)
    # get the last non empty string
    last = next(s for s in reversed(info.split('\n')) if s)
    data = last.split(':')
    data[5] = humanfriendly.parse_size(str(data[5]).replace('total=',''))
    return data

# -------------------------------------------------------------------
# get node information for a list of nodes, by ssh-ing into each
def get_all_node_data(node_list):
    node_info = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(node_list)) as executor:
        future_to_data = {executor.submit(get_node_compute_data, n): n for n in node_list}
        for future in concurrent.futures.as_completed(future_to_data):
            node = future_to_data[future]
            try:
                data = future.result()
                print('Node data is', data)
            except Exception as exc:
                print('%r generated an exception: %s' % (node, exc))
            else:
                if node!=data[0]:
                    print('Warning, node returned unexpected hostname', node, '!=', data[0])
                node_info[node] = data[1:]
    return node_info

# -------------------------------------------------------------------
# represents a graph node with dependencies on other tasks
class task:
    _task_id = -1
    _command = "ls -1"
    _cores   = 1
    _memory  = 1024*1024
    _node    = None
    _dependent_task_array = []
    _provider_task_array = []

    def __init__(self, task_id, command, dependent_task_array, cores, memory):
        self._task_id = task_id
        self._command = command
        self._cores   = cores
        self._memory  = memory
        # convert any file objects to string pathnames in arg list
        self._dependent_task_array = dependent_task_array

    def dependent_task_array(self):
        return self._dependent_task_array

    def command(self):
        return self._command

    def task_id(self):
        return self._task_id

    def cores(self):
        return self._cores

    def memory(self):
        return self._memory

    # when running, the node being used is stored in the task
    def set_node(self, node):
        self._node = node

    def node(self):
        return self._node

# -------------------------------------------------------------------
# represents an 'in flight' graph node executing that will complete and set
# a result in a future
class task_status:
    _task = None
    _future = None

    def __init__(self, task, future):
        self._future = future
        self._task = task

    def future(self):
        return self._future

    def task(self):
        return self._task

def mem_gb(memory):
    return int(memory/(1024*1024*1024))

# -------------------------------------------------------------------
# workflow object that represents a graph of nodes and has scheduling
# operations to execute the graph on a set of resources that are discovered
# at startup
class splinter_workflow:
    _task_array = []
    _pending_task_array = []
    _completed_task_array = []
    _task_status_array = []

    # these are the resources available on the system
    _resource_pool = {}

    # during execution, resources are consumed, we track availability here using node as key
    # to dicts of CPU and memory (others can be added)
    _cpu_avail = {}
    _mem_avail = {}
    _max_jobs  = 1;
    _job_id    = 0

    # -------------------------------------------------------------------
    # construct. Init the resource pool with whatever nodes we have
    def __init__(self):
        self._job_id = get_slurm_job()
        node_list = get_slurm_nodelist()
        node_info = get_all_node_data(node_list)
        for node, data in node_info.items():
            print('node', node, 'sockets {}, numa {}, cores {}, pus {}, memory(GB) {}'
                  .format(data[0], data[1], data[2], data[3], int(data[4]/(1024*1024*1024))))
            # we will store tuple(cpus, memory) in our resource list
            self._resource_pool[node] = (int(data[2]), data[4])


    # -------------------------------------------------------------------
    # This should be called before executing a new workflow to ensure
    # resources are reset to their initial state
    def init_resources(self):
        self._max_jobs  = 0;
        for node, data in self._resource_pool.items():
            self._cpu_avail[node] = data[0]
            self._mem_avail[node] = data[1]
            # to tell the executor the max number of "threads" we 'might' need
            self._max_jobs += data[0];

    # -------------------------------------------------------------------
    # method to add a task to the graph of work
    def add_task(self, task):
        self._task_array.append(task)

    # -------------------------------------------------------------------
    # a job that has been launched has a status object that knows
    # when it completes via a future and holds other information about the job
    def completed_task_status(self):
        for task_status in self._task_status_array:
            if task_status.future().done():
                task = task_status.task()
                node = task.node()
                self._cpu_avail[node] += task.cores()
                self._mem_avail[node] += task.memory()
                return task_status
        return None

    # -------------------------------------------------------------------
    # returns true if jobs still remain that need to be executed or
    # have not yet completed runnning
    def is_workflow_active(self):
        if len(self._pending_task_array) != 0:
            return True

        if len(self._task_status_array) != 0:
            return True

        return False

    # -------------------------------------------------------------------
    # returns true when a job can run because any other jobs it depends on
    # have completed (or it has no dependencies)
    def are_task_dependencies_satisfied(self, task):
        if len(task.dependent_task_array())==0:
            return True

        completed_task_id_array = [task.task_id() for task in self._completed_task_array]
        pending_task_id_array = [task.task_id() for task in self._pending_task_array]
        # race? : if a task completes whilst we are iterating this list? (should not matter)
        for dependent_task in task.dependent_task_array():
            # if a parent task isn't marked as completed, we cannot run
            if not dependent_task in completed_task_id_array:
                return False
            # if a parent task has not run yet, we cannot run
            if dependent_task in pending_task_id_array:
                return False
        return True

    # -------------------------------------------------------------------
    # return True if there is a worker available that can run this job
    # free workers might not have enough cpu/memory/other to run a particular job
    # This function changes resources available, so if it returns True,
    # you must launch the task, otherwise resources tracking will be incorrect
    def is_worker_available(self, task):
        for (node1,cpus), (node2,mem) in zip(self._cpu_avail.items(), self._mem_avail.items()):
            if node1!=node2:
                raise "Fatal : Nodes do not match in resource dictionaries"
            # if this task can run on this node
            if cpus>task.cores() and mem>task.memory():
                # decrement resources
                self._cpu_avail[node1] = self._cpu_avail[node1]-task.cores()
                self._mem_avail[node1] = self._mem_avail[node1]-task.memory()
                task.set_node(node1)
                print('node {}, cpus {}, GB {}'.format(node1, self._cpu_avail[node1], mem_gb(self._mem_avail[node1])))
                return True
        return False

    # -------------------------------------------------------------------
    # (greedy) method to get the next task to run, returns the next available
    # task that fits in available resources
    # Warning:
    # This function changes pending tasks and resources available, so if it returns a task,
    # you must launch it, otherwise resources will be lost and job tracking will fail
    def find_next_task(self):
        n_pending_task = len(self._pending_task_array)
        if n_pending_task != 0:
            for i in range(0, n_pending_task):
                task = self._pending_task_array[i]
                if self.are_task_dependencies_satisfied(task) and self.is_worker_available(task):
                    # update pending tasks
                    self._pending_task_array.remove(task)
                    return task
        return None

    # -------------------------------------------------------------------
    # this function will execute a graph of work
    # the user must create tasks, with dependencies and
    def execute_workflow(self, poll_frequency, srun):
        self._pending_task_array = self._task_array

        # initialize resource lists
        self.init_resources()
        last_now = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_jobs) as executor:
            poll_loop = 0
            while self.is_workflow_active():
                completed_task_id_array = [task.task_id() for task in self._completed_task_array]
                pending_task_id_array = [task.task_id() for task in self._pending_task_array]
                in_flight_id_array    = [status.task().task_id() for status in self._task_status_array]

                now = time.time()
                if (now-last_now>5):
                    print('Poll loop', poll_loop,
                          '\nCompleted tasks', completed_task_id_array,
                          '\nPending tasks', pending_task_id_array,
                          '\nIn flight', in_flight_id_array)
                    last_now = now

                # Launch as many tasks as possible in each polling window
                task = self.find_next_task()
                while task is not None:
                    print("Submitting Job", task.task_id(), task.command())
                    if srun:
                        future = execute_srun(executor, self._job_id, task.node(), task.command())
                    else:
                        future = executor.submit(subprocess.run, task.command(), stdout=subprocess.PIPE)
                    self._task_status_array.append(task_status(task, future))
                    # any more tasks ready to execute?
                    task = self.find_next_task()

                # Clear as many tasks as possible in each polling window
                completed_task_status = self.completed_task_status()
                while completed_task_status is not None:
                    node = completed_task_status.task().node()
                    print('Job {} Completed : node {}, cpus {}, GB {}'
                          .format(completed_task_status.task().task_id(), node, self._cpu_avail[node], mem_gb(self._mem_avail[node])))

                    self._completed_task_array.append(
                        completed_task_status.task())
                    self._task_status_array.remove(completed_task_status)
                    # any more completed tasks?
                    completed_task_status = self.completed_task_status()

                time.sleep(poll_frequency)
                poll_loop += 1


if __name__ == "__main__":
    gigabyte = 1024 * 1024 * 1024
    wf = splinter_workflow()

    wf.add_task(task(1, ["./test/tester", "10"], [],  1, 1*gigabyte))
    wf.add_task(task(2, ["./test/tester", "1"],  [],  1, 1*gigabyte))
    wf.add_task(task(3, ["./test/tester", "5"],  [2], 1, 1*gigabyte))
    wf.add_task(task(4, ["./test/tester", "1"],  [1], 1, 1*gigabyte))

    wf.execute_workflow(2,True)
