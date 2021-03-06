#!/usr/bin/env python
# coding: utf-8

# In[22]:


#! /usr/bin/env python3
import importlib
import inspect
import pprint
import os
import sys
from datetime import datetime

from pathlib import Path
#
from Pegasus.api import *

# splinter
import subprocess
import time
import concurrent.futures

splinter = importlib.import_module("splinter")
importlib.reload(splinter)

import timeit
import yaml as yaml
import itertools
import copy
import logging
import random
from shutil import copyfile
#logging.basicConfig(level=logging.INFO


# In[23]:


# =================================================================
# Returns true if running inside a jupyter notebook,
# false when running as a simple python script
# useful for handling command line options or
# setting up notebook defaults
# =================================================================
def is_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter

def save_notebook():
    if is_notebook():
        try:
            # save this notebook as a raw python file as well please
            get_ipython().system('jupyter nbconvert --to script CDO-workflow-slurm-splinter-workflow.ipynb')
        except:
            pass


# In[24]:


if not is_notebook:
    print(sys.argv)
    ARG_iterations = sys.argv[1]
    ARG_forks      = sys.argv[2]
    ARG_datasize   = sys.argv[3]
    ARG_cdo        = sys.argv[4]    


# In[25]:


hostname = os.getenv('HOSTNAME')
user     = os.getenv('USER')
if hostname is None:
    hostname = 'localhost'
if user is None:
    user = 'biddisco'
print(f'Hostname is {hostname}, User is {user}')

# default parths for container
BINARY_PATH  ='/home/scitech/shared-data/maestro-test/binaries/'
MOCKTAGE_PATH='/home/scitech/mocktage/build/bin/'
DATA_PATH    ='/home/scitech/shared-data/maestro-test/binaries/data/'
SCRATCH_PATH ='/home/scitech/scratch/'
BEEGFS_PATH  = ''

if ('oryx' in hostname or 'localhost' in hostname):
    BINARY_PATH  ='/home/biddisco/src/maestro/pegasus-workflow-development-environment/shared-data/maestro-test/binaries/'
    MOCKTAGE_PATH='/home/biddisco/build/maestro/mocktage/bin/'
    DATA_PATH    ='/home/biddisco/src/maestro/pegasus-workflow-development-environment/shared-data/maestro-test/binaries//data/'
    SCRATCH_PATH ='/home/biddisco/temp/maestro/'
    
if ('daint' in hostname) or ('nid' in hostname):
    BINARY_PATH  ='/scratch/snx3000/biddisco/shared-data/maestro-test/binaries/'
    MOCKTAGE_PATH='/scratch/snx3000/biddisco/maestro/mocktage/bin/'
    DATA_PATH    ='/scratch/snx3000/biddisco/shared-data/maestro-test/binaries/data/'
    SCRATCH_PATH =os.getcwd()
    BEEGFS_PATH  ='/users/' + user + '/beegfs/'


# In[26]:


def build_transformation_catalog(wf):
    
    tc = TransformationCatalog()
    trans = {}

    exes = {}
    binary_paths = [BINARY_PATH, MOCKTAGE_PATH]
    
    for base in binary_paths:
        base_dir = os.path.dirname(base)

        for fname in os.listdir(base_dir):
            transformation = None
            if fname[0] == '.':
                continue
            #print('Making transformation', os.path.join(base_dir, fname))
            transformation = Transformation(fname, 
                                            site='local',
                                            pfn=os.path.join(base_dir, fname), 
                                            is_stageable=False)
            transformation.add_env(PATH=MOCKTAGE_PATH + ':' 
                                   + BINARY_PATH + ':' + '/usr/bin:/bin:.')

            # memory requirement
            transformation.add_profiles(Namespace.CONDOR, 'request_memory', '1 GB')

            # some transformations can be clustered for effiency
            #if fname in ['gmProject', 'mDiff', 'mDiffFit', 'mBackground']:
            #    transformation.add_profiles(Namespace.PEGASUS, 'clusters.size', '3')

            # keep a handle to added ones, for use later
            trans[fname] = transformation

            tc.add_transformations(transformation)

    wf.add_transformation_catalog(tc)


# In[27]:


def build_site_catalog():
    # create a SiteCatalog object
    sc = SiteCatalog()

    # -----------------------------------------------
    # create a "local" site
    local = Site("local", arch=Arch.X86_64, os_type=OS.LINUX)

    #pprint(dir(Directory))
    # create and add a shared scratch and local storage directories to the site "local"
    local_shared_scratch_dir = Directory(Directory.SHARED_SCRATCH, path=SCRATCH_PATH)        .add_file_servers(FileServer("file://" + SCRATCH_PATH, Operation.ALL))

    #local_local_storage_dir = Directory(Directory.LOCAL_STORAGE, path="/tmp/pegasus/local")\
    #                            .add_file_servers(FileServer("file:///tmp/pegasus/local", Operation.ALL))
    local_shared_binary_dir = Directory(Directory.LOCAL_STORAGE, path=BINARY_PATH)        .add_file_servers(FileServer("file://" + BINARY_PATH, Operation.ALL))
    local_shared_binary_dir = Directory(Directory.LOCAL_STORAGE, path=MOCKTAGE_PATH)        .add_file_servers(FileServer("file://" + MOCKTAGE_PATH, Operation.ALL))

    local.add_directories(local_shared_scratch_dir, local_shared_binary_dir)

    
    # -----------------------------------------------
    # create a "condorpool" site
    condorpool = Site("condorpool")                    .add_pegasus_profile(style="condor")                    .add_pegasus_profile(auxillary_local="true")                    .add_condor_profile(universe="local")

    # create and add a shared scratch directory to the site "condorpool"
    condorpool_shared_scratch_dir = Directory(Directory.SHARED_SCRATCH, path=SCRATCH_PATH)        .add_file_servers(FileServer("file://" + SCRATCH_PATH, Operation.ALL))
#     condorpool_local_storage_dir = Directory(Directory.LOCAL_STORAGE, path=SCRATCH_PATH)\
#         .add_file_servers(FileServer("file://" + SCRATCH_PATH, Operation.ALL))
    condorpool_shared_binary_dir = Directory(Directory.LOCAL_STORAGE, path=BINARY_PATH)        .add_file_servers(FileServer("file://" + BINARY_PATH, Operation.ALL))
    condorpool_shared_binary_dir = Directory(Directory.LOCAL_STORAGE, path=MOCKTAGE_PATH)        .add_file_servers(FileServer("file://" + MOCKTAGE_PATH, Operation.ALL))
    
    condorpool.add_directories(condorpool_shared_scratch_dir, condorpool_shared_binary_dir)

    # -----------------------------------------------                
    # add the sites to the site catalog object
    sc.add_sites(local, condorpool)

    # write the site catalog to the default path "./sites.yml"
    #set_trace()
    sc.write()
    
    return sc


# In[28]:


def build_properties():
    props = Properties() 
    #props["pegasus.mode"] = "development"
    #props["pegasus.data.configuration"] = "sharedfs"
    #props["pegasus.code.generator"] = "Shell"
    props.write()
    return props


# In[29]:


def is_watcher(job):
    return ('cdo_watcher' in job.metadata)

def is_cache(job):
    return False
    return ('cdo_cache' in job.metadata)

def node_memory(job):
    if 'maestro_mem' in job.metadata:
        return int(float(job.metadata['maestro_mem']))
    return None

def node_cores(job):
    if 'maestro_cores' in job.metadata:
        return int(float(job.metadata['maestro_cores']))
    return None


# In[30]:


LOG_LEVEL = "0"
GB = 1024 * 1024 * 1024
        
global_component_id = 0
global_offset = 0

def current_milli_time():
    return round(time.time() * 1000)

def start_id_offset(enable_time):
    global global_offset
    if enable_time:
        now = current_milli_time()
        now = now % 100000
        return now
    else:
        temp = global_offset
        global_offset += 100
    return global_offset
        
def next_id_string(): 
    global global_component_id
    temp = global_component_id
    global_component_id += 1
    return 'ID-' + str(temp)

def cdo_name(file):
    return file # 'CDO-' + file


# In[31]:


class CDO:
    def __init__(self, filename: str):
        self.filename    = filename
        #self.cached_name = 'cdo-cache-' + filename
        self.input_count = 0
        #self.cache       = None

# -----------------------------------------------------------
# Define a subclass of the pegasus workflow object 
#
# Override pegasus job insertion, to customize for CDOs
#
class Maestro_Workflow(Workflow):
    
    def __init__(self, cdo_dependency, name: str, pool_manager=True, dynamic_provisioning=False, infer_dependencies: bool = True):
        print("This is the init function")
        super().__init__(name, infer_dependencies)
        self.parent_tasks         = {}
        self.cdo_dependency       = cdo_dependency
        self.pool_manager_startup = pool_manager
        self.dynpro_startup       = dynamic_provisioning
        
        if self.pool_manager_startup:
            pool_manager = Job("start-pool-manager.sh", node_label="start\npool\nmanager")                            .add_args(SCRATCH_PATH, "pool_manager.stop", MOCKTAGE_PATH + "/pool_manager", SCRATCH_PATH + "/pminfo")                             .add_metadata(maestro_mem=2*GB, 
                                          maestro_cores=4,
                                          maestro_workflow_core_backend="beegfs", 
                                          maestro_poolmanager='true')
            super().add_jobs(pool_manager)
        else:
            print('WARNING: pool manager startup was turned off')
        
        if self.dynpro_startup:
            dynpro = Job("start-dynpro.sh", node_label="start\ndynamic\nprovisioning")                            .add_metadata(maestro_mem=1*GB, 
                                          maestro_cores=1,
                                          maestro_workflow_core_backend="beegfs", 
                                          maestro_dynpro='true')
            super().add_jobs(dynpro)
        else:
            print('WARNING: pool manager startup was turned off')
        
    # find the input to a job that generates the named output
    def find_parent_dependency(self, output):
        for id, job in self.jobs.items():
            # if this output matches the request, find the first input
            for op in job.get_outputs():
                #print('testing', op.lfn, 'against',output)
                if op.lfn == output and len(job.get_inputs())>0:
                    # just get the filename of the first input
                    temp = next(iter(job.get_inputs())).lfn
                    #print('Found a match using', temp)                    
                    return next(iter(job.get_inputs())).lfn
        print('No parent for', output)
        return output

    def compute_memory_use(self):
        # Before we transform the graph and convert files to CDOs, we will tag
        # all jons with the amount of memory they 'should' need, based on their
        # input files sizes and output file sizes
        for id, job in self.jobs.items():
            mem = 0
            for ip in job.get_inputs():
                mem = mem + node_memory(ip)
            for op in job.get_outputs():
                mem = mem + node_memory(op)
            oldmem = node_memory(job)
            if oldmem is not None and oldmem!=mem and mem>0:
                print("Job memory mismatch : oldmem", oldmem, "new", mem)
            job.add_metadata(maestro_mem=int(mem*1.5))            
        
    #
    # This is the main routine that walks the graph and converts files to CDOs
    # inserts watchers and cache objects.
    #
    def insert_cdo_jobs(self):        
        # note that we must rename input and outputs using new file objects
        # to work around shared files that are both input and outputs
        # and are replaced by CDO objects
        i_replacements = {}
        o_replacements = {}
        
        # store watchers created to prevent creating 2 watchers for the same CDO
        # if it is consumed by more than one process
        watchers   = {}
        cdo_objs   = {}
        extra_jobs = []
        for id, job in self.jobs.items():                
            # For each input :      in -> P -> out
            #   replace with parent(in) -> watcher ->
            #                                   -> (in)' -> P -> out
            if len(job.get_inputs())>0:
                for ip in job.get_inputs():
                    cdo_enabled = True
                    if "cdo_disabled" in ip.metadata:
                        cdo_enabled = not ip.metadata['cdo_disabled'].lower() in ['true', '1', 't', 'y', 'yes']                    
                        #print(ip, "is cdo enabled", cdo_enabled)
                    if not cdo_enabled:
                        print('No substitution for non CDO enabled input', ip.lfn)
                        continue
                    
                    ip_name        = ip.lfn
                    trigger_name   = 'T-' + ip_name
                    node_label     = '' + ip_name
                    
                    # track how many consumers are taking this CDO as an input
                    if not ip_name in cdo_objs:
                        
                        cdo_objs[ip_name] = CDO(ip.lfn)
                        cdo_objs[ip_name].input_count = 1
                        
                        # if multiple processes consume the same CDO, we only need one watcher
                        # create a watcher for this CDO input
                        id_string = next_id_string()
                        watcher = Job("process-CDO", _id=id_string, node_label = id_string)
                        pseudo_parent = self.find_parent_dependency(ip_name)
                        watcher.add_env(MSTRO_LOG_LEVEL=LOG_LEVEL)
                        watcher.add_inputs(pseudo_parent)
                        watcher.add_outputs(File(trigger_name).add_metadata(dummy_file='true'), stage_out=True)
                        watcher.add_args('-l', SCRATCH_PATH,     # log directory 
                                         '-p', 'pminfo',         # pool manager info
                                         '-w',                   # watcher mode
                                         '-t', trigger_name,     # trigger_file for pegasus
                                         '-c', id_string,        # component name, must be unique
                                         '-i', ip_name)          # list of input CDOs to consume
                        watcher.add_metadata(cdo_watcher='true', maestro_mem=1*GB, maestro_cores=5)
                        watchers[node_label] = watcher
                                               
                        # Add these new jobs to the actual DAG
                        extra_jobs.append(watcher)
                        
                    else:
                        cdo_objs[ip_name].input_count += 1
                        #print('Count for', ip_name, cdo_objs[ip_name].input_count) 
                        
                    # any process that outputs this data will need to rename it to the new input name
                    o_replacements[ip_name] = ip_name
                    
                    # for dependencies that use files as input : rename it to the new trigger file name 
                    i_replacements[ip_name] = trigger_name
                
            if "final_job" in job.metadata:
                if self.pool_manager_startup:
                    # print ('final job', id, 'corresponds to', job.node_label)
                    stop_pm = Job("stop-pool-manager.sh", node_label="stop\npool\nmanager")
                    stop_pm.add_args(SCRATCH_PATH, 'pool_manager.stop')                         .add_metadata(maestro_poolmanager='true', 
                                      maestro_mem=0.5*GB, 
                                      maestro_cores=4)
                    for op in job.get_outputs():
                        stop_pm.add_inputs(op.lfn)
                    extra_jobs.append(stop_pm)
                    
        for job in extra_jobs:
            if job._id is None:
                job._id = self._get_next_job_id()
            self.jobs[job._id] = job
            job.node_label = job._id
        
        # when we replace an input to a job with a CDO version of it, we have to create a new "File" object
        # because if we simply change the path/name, we might modify the same 'file' object on different 
        # jobs and we can get links between tasks we were not expecting
        for id, job in self.jobs.items():
            # for each output, specify consumer count for each
            output_counts = []
            for op in job.get_outputs():
                if (op is not None) and op.lfn in cdo_objs:
                    output_counts += [cdo_objs[op.lfn].input_count]
                    job.add_args('-O', *output_counts)
                    #print('Set O for', op.lfn, cdo_objs[op.lfn].input_count) 
                    
            for u in job.uses:
                if u.file.lfn in i_replacements:
                    # Replace an input that we have changed to point to the dummy file
                    if u._type == "input":
                        u.file = File(i_replacements[u.file.lfn]).add_metadata(dummy_file='true')
                    # Replace an output that we have changed to point to the CDO
                    if u._type == "output":
                        # we add a watcher and a cache as dependencies of this CDO, but watcher is not counted
                        # output_counts += ['1'] 
                        # make sure the CDO cache is kept alive for N real consumers
                        # cdo_objs[u.file.lfn].cache.add_args('-O', cdo_objs[u.file.lfn].input_count)
                        # cdo_objs[u.file.lfn].cache.add_metadata(maestro_cores=2)                        

                        if u.file.lfn in cdo_objs:
                            if self.cdo_dependency :
                                u.file = File(o_replacements[u.file.lfn]).add_metadata(cdo_data='true') 
                            else:
                                u.file = None
                                
                
            # otherwise, assume 2 consumers (watcher + cache)
            # elif not is_cache(job) and not is_watcher(job):                    
            #     if job.transformation=='process-CDO':
            #         job.add_args('-O', '1')
            #     else:
            #         ...
                    #print(job)

            job.uses = [x for x in job.uses if x.file is not None]
                                    
        print('Substitution of command line filenames for cached CDOs')
        for id, job in self.jobs.items():                
            # watchers always watch for the original CDO (no name change)
            # cache's will output a CDO with a new name (name change handled by cache itself)
            # other objects must rename their inbput file/cdo names to the renamed version
            if is_watcher(job) or is_cache(job):
                ...
            else:
                new_args = []
                # we must only change input CDO names, as original output names go into the cache 
                input = False
                for a in job.args:
                    if a == '-i':
                        input = True
                    if a == '-o':
                        input = False
                    if input and isinstance(a, File):
                        cdo_name = a.lfn # 'cdo-cache-' + a.lfn
                        a = File(cdo_name)
                    new_args.append(a)
                job.args = new_args
            #
            # print(job.args)
                    
        for d, val in self.dependencies.items():
            print('Dependency', d, val)
            
    def insert_shutdown_jobs(self):
        if self.dynpro_startup:
            for id, job in self.jobs.items():                
                if "final_job" in job.metadata:
                    dynpro = Job("start-dynpro.sh", node_label="stop\ndynamic\nprovisioning")
                    dynpro.add_args(SCRATCH_PATH, 'dynpro.stop')                         .add_metadata(maestro_dynpro='true', 
                                      maestro_mem=0.5*GB, 
                                      maestro_cores=1)
                    for op in job.get_outputs():
                        dynpro.add_inputs(op.lfn)
            super().add_jobs(dynpro)
                    
        
    def execute_using_slurm(self):
        return        
    
    def build_dependencies(self):
        # buiod list of children for each task
        self.infer_dependencies = True
        self._infer_dependencies()
        
        # construct list of parents from child list
        for k,v in self.dependencies.items():
            for c in v.children_ids:
                if c in self.parent_tasks:
                    self.parent_tasks[c] = self.parent_tasks[c] + [k]
                else:
                    self.parent_tasks[c] = [k]
                    
        for task, parent in self.parent_tasks.items():
            #print('Task', task, 'Depends on', parent)
            ...
        return
        
    def execute_using_splinter(self, srun):
        # get the transformation catalog
        #print(dir(self.transformation_catalog))
        tc = self.transformation_catalog.transformations        
        # for x in tc:
        #     print (x)
            
        # build parent/child dependency lists 
        self.build_dependencies()
        # create a splinter workflow
        swf = splinter.splinter_workflow()
        
        for id, job in self.jobs.items():
            t_string = "None::" + job.transformation + "::None"
            t_path = tc[t_string].sites['local'].pfn            
            # convert any file objects to string pathnames in arg list
            command = [t_path] + [str(a) for a in job.args]
            parents = self.parent_tasks[id] if id in self.parent_tasks else []
            try:
                memory = node_memory(job)
                cores  = node_cores(job)
            except:
                print('Invalid JOB', job, job.args)
                memory = None
                cores  = None
            if memory is None:
                print('Invalid memory', job, job.args)
            if cores is None:
                print('Invalid cores', job, job.args)
            splinter_task = splinter.task(id, command, parents, cores, memory)
            swf.add_task(splinter_task)
            
        # poll freq, use srun
        swf.execute_workflow(0.1, srun)


# In[32]:


import re
def regex_increment_first(instring, N):
    # preceeded by "-" : followed by "-"
    out = instring
    for i in range(0,N):
        out = re.sub('(?<=-)(\d+)(?=-)', lambda x: str(int(x.group(0)) + 1).zfill(2), out)
    return out

def regex_increment_last(instring, N):
    # preceeded by "-" : followed by EOL
    out = instring
    for i in range(0,N):
        out = re.sub('(?<=-)(\d+$)', lambda x: str(int(x.group(0)) + 1).zfill(2), out)
    return out

# x = "f-04-05"
# print(regex_increment_first(x,2))
# print(regex_increment_last(x,3))


# In[33]:


def probability(p):
    return (random.randint(1,100) <= p)

# x0 = 0;
# x1 = 0;
# x2 = 0;
# for a in range(0,10000):
#     if probability(0):
#         x0 += 1
#     if probability(50):
#         x1 += 1
#     if probability(100):
#         x2 += 1
        
# print(x0, x1, x2)


# In[36]:


def generate_demo_workflow(wf, rc, maestro=False, data_size=65536, id_offset=0, iterations=2, forks=2, subforks=2):

    random.seed(a=123456)
    
    # ---------------------------------------------------------
    # Create a single input file that will start our graph
    fa = File("root-data.txt").add_metadata(creator="biddisco", 
                                            cdo_disabled="true", 
                                            maestro_enabled="false", 
                                            node_label='root',
                                            maestro_mem = data_size)
    rc.add_replica(
       site="local", lfn=fa, pfn=Path(DATA_PATH).resolve() / "root-data.txt"
    )
    
    # ---------------------------------------------------------
    # Create a single job that will fork into N new files
    # Names are xxx-FORK-ITERATION
    files = []    
    for f in range(0,forks): # originally N forks
        # create string "f-0N-00"
        files.append(File("f-" + f"{f:0>2}" + "-00").add_metadata(maestro_mem = data_size))
    
    arg_defaults = ['-l', SCRATCH_PATH,   # log directory 
                    '-p', 'pminfo',       # pool manager info
                    '-d', int(data_size)] # default cdo/file size
    
    if not maestro:
        arg_defaults += ['-b', BEEGFS_PATH]
        arg_defaults += ['-F'] # filemode - no CDOs to be generated in this mode, just HDF5 files
        
    id_string = next_id_string()
    node_label = "preprocess"
    
    job_preprocess = Job("process-CDO", _id=id_string, node_label=node_label)                             .add_env(MSTRO_LOG_LEVEL=LOG_LEVEL)                                   .add_inputs(fa)                                                       .add_outputs(*files, stage_out=True)                                  .add_metadata(node_colour='#e959d9', maestro_cores=4)                             .add_args(*arg_defaults,
                                      '-c', id_string,              # component name, must be unique
                                      '-o', *[x for x in files])    # list of output CDOs to produce
    # print('args are', job_preprocess.args) 
    
    
    # ---------------------------------------------------------
    # for each fork, produce a chain of iterations file_in->P->file_out processes
    job_iter = []
    for i in range(0, iterations):
        out_files = []
        for f in range(0,forks):
            
            if f<len(files):
                in_file = files[f]
                out_name = regex_increment_last(in_file.lfn, 1)
            else:
                in_file = files[f % len(files)]
                out_name = regex_increment_last(in_file.lfn, i+1)
                for ff in range(0, 1 + (f % len(files))):
                    out_name = regex_increment_first(out_name, f)
                
            in_name = in_file.lfn
            f_out = File(out_name).add_metadata(maestro_mem=node_memory(in_file))
            out_files.append(f_out)

            id_string = next_id_string()
            node_label = str(f)+"-process-" + str(i)
            job_iter.append(Job("process-CDO", _id=id_string, node_label=node_label)                            .add_metadata(node_colour='#ff7fb3', maestro_cores=5)                            .add_env(MSTRO_LOG_LEVEL=LOG_LEVEL)                             .add_inputs(in_file)                                           .add_outputs(f_out, stage_out=True)                             .add_args(*arg_defaults,
                                      '-c', id_string,              # component name, must be unique
                                      '-i', in_file,               # list of input CDOs to produce
                                      '-o', f_out))                 # output (default 1 consumer omitted)                
                                
        #print('Files',i, files, out_files) 
        files = out_files
            
            # on first iteration, add an extra fork+join to test our CDO stuff
#             if False and i==0 and subforks>1:
#                 subfiles = []
#                 # create a set of tasks that fork from a single input
#                 for sf in range(0,subforks):
                    
#                     #if random.randint(1,5)==1:                        
#                     #    sf_out.add_metadata(cdo_disabled="true")
                    
#                     sf_out = File(out_name + "-" + str(sf)).add_metadata(maestro_mem=node_memory(in_file))            
#                     subfiles.append(sf_out)
#                     id_string = next_id_string()
#                     node_label = sf_out.lfn
#                     forkjob = Job("process-CDO", _id=id_string, node_label=id_string)\
#                                 .add_metadata(node_colour='#1b9e77', maestro_cores=2) \
#                                 .add_env(MSTRO_LOG_LEVEL=LOG_LEVEL)  \
#                                 .add_inputs(in_file)                \
#                                 .add_outputs(sf_out, stage_out=True) \
#                                 .add_args(*arg_defaults,
#                                           '-c', id_string,        # component name, must be unique
#                                           '-i', in_file,         # (list of) input CDO(s) to consume
#                                           '-o', sf_out)           # output (default 1 consumer omitted)
#                     job_iter.append(forkjob)

#                 # join all the tasks back into a single output    
#                 id_string = next_id_string()
#                 node_label = str(f)+"-process-" + str(i)
#                 joinjob = Job("process-CDO", _id=id_string, node_label=id_string)\
#                                 .add_metadata(node_colour='#3b97be', maestro_cores=2)\
#                                 .add_env(MSTRO_LOG_LEVEL=LOG_LEVEL) \
#                                 .add_inputs(*subfiles)              \
#                                 .add_outputs(f_out, stage_out=True) \
#                                 .add_args(*arg_defaults,
#                                           '-c', id_string,              # component name, must be unique
#                                           '-i', *[x for x in subfiles], # (list of) input CDO(s) to produce
#                                           '-o', f_out)                  # output (default 1 consumer omitted)                
#                 job_iter.append(joinjob)
                
            # else:
        

    fd = File("Output").add_metadata(final_output="true", 
                                  cdo_disabled="true", 
                                  maestro_mem = data_size)
    id_string = next_id_string()
    node_label = "analyze"
    job_analyze = Job("process-CDO", _id=id_string, node_label=node_label)                                    .add_env(MSTRO_LOG_LEVEL="0")                                             .add_inputs(*files)                                                       .add_outputs(fd, stage_out=True)                                          .add_metadata(final_job='true', node_colour='#8a4f4f', maestro_cores=4)                    .add_args(*arg_defaults,
                              '-c', id_string,              # component name, must be unique
                              '-i', *[x for x in files],    # list of input CDOs to produce
                              '-t', fd.lfn)                 # output (default 1 consumer omitted)                

    wf.add_jobs(job_preprocess, job_analyze)
    for j in job_iter:
        wf.add_jobs(j)

    if isinstance(wf,Maestro_Workflow):
        wf.compute_memory_use()
        if maestro:
            wf.insert_cdo_jobs()
        else:
            wf.insert_shutdown_jobs()
        
    wf.add_replica_catalog(rc)
    wf.write(file=wf.name)
    print('Written workflow to', wf.name)
    return wf.path.name


# In[37]:


# ---------------------------------------
# cdo_dependencies : false, CDOs are not matched between in/out so CDO consumers do not depend on producers, the DAG is split
#                  : true, CDOs behave like files and trigger dependencies
# display_files : true, files appear as nodes in the graph, otherwise not
# transitive_reduction : true - remove links that are superfluous - transitive, between job-job bypassing files

# cdo_dependencies must be False when executing a CDO enabled workflow

cdo_dependencies     = False
display_files        = True
transitive_reduction = True
left_right           = True

if os.path.isfile("pegasus.properties"):
    os.remove("pegasus.properties")
if os.path.isfile("sites.yml"):
    os.remove("sites.yml")

rc1 = ReplicaCatalog()
rc2 = ReplicaCatalog()
rc3 = ReplicaCatalog()
sco = build_site_catalog()    
prp = build_properties()

# ---------------------------------------
# Convert workflow into nice DAG display
iterations = 3
forks = 5
subforks = 0

# ---------------------------------------
# Generate workflows, one original, one maestro enabled

TIME_OFFSETS = True

global_component_id = 0
print('Time/Id offset is', global_component_id)
wfo = Workflow(name="demo-orig.yml")
build_transformation_catalog(wfo)
file1 = generate_demo_workflow(wfo, rc1, iterations=iterations, forks=forks, subforks=subforks)

global_component_id = 0
print('Time/Id offset is', global_component_id)
wfm = Maestro_Workflow(cdo_dependencies, name="demo-maestro.yml", pool_manager=True, infer_dependencies=False)
build_transformation_catalog(wfm)
file2 = generate_demo_workflow(wfm, rc2, maestro=True,  iterations=iterations, forks=forks, subforks=subforks, data_size=1*GB)

global_component_id = 0
print('Time/Id offset is', global_component_id)
wff = Maestro_Workflow(cdo_dependencies, name="demo-beegfs.yml", pool_manager=False, dynamic_provisioning=True, infer_dependencies=False)
build_transformation_catalog(wff)
file3 = generate_demo_workflow(wff, rc3, maestro=False, iterations=iterations, forks=forks, subforks=subforks)

save_notebook()


# In[15]:


if ('daint' in hostname) or ('nid' in hostname):
    srun = True
else:
    srun = False

class GetOutOfLoop( Exception ):
    pass

count = 0

PATH1 ='/scratch/snx3000/' + user + '/maestro-scratch/'    
PATH2  ='/users/' + user + '/beegfs/'
TIME_OFFSETS = False

if not is_notebook():
    iterlist = [int(sys.argv[1])]
    forklist = [int(sys.argv[2])]
    sizelist = [int(sys.argv[3])]
    cdolist  = [sys.argv[4]]
else:
    iterlist = [5, 10, 15, 20]
    forklist = [2,4,6,8]
    sizelist = [1*GB, 2*GB, int(3.99*GB)]
    cdolist  = ['lustre'] # ['cdo','beegfs','lustre']

# iterlist = [10]
# forklist = [2]
# sizelist = [1*GB]
# cdolist  = ['lustre'] # ['cdo','beegfs','lustre']

rc1 = ReplicaCatalog()
    
try:
    for cdo in cdolist:
        for forks in forklist:
            for iterations in iterlist:
                for size in sizelist:
                    
                    # for fs in [PATH1, PATH2]:
                    subforks=0

                    print(f'Args size {size}, iterations {iterations}, forks {forks}') 
                    
                    global_component_id = 0
                    
                    if cdo == 'cdo':
                        SCRATCH_PATH =os.getcwd()
                        BEEGFS_PATH  =os.getcwd()                        
                        wff = Maestro_Workflow(cdo_dependencies, name="demo-cdo.yml", pool_manager=True , dynamic_provisioning=False, infer_dependencies=False)
                        build_transformation_catalog(wff)
                        file3 = generate_demo_workflow(wff, rc1, maestro=True, iterations=iterations, forks=forks, subforks=subforks, data_size=size)
                    elif cdo=='beegfs':                        
                        wff = Maestro_Workflow(cdo_dependencies, name="demo-beegfs.yml", pool_manager=False, dynamic_provisioning=False, infer_dependencies=False)
                        build_transformation_catalog(wff)
                        file3 = generate_demo_workflow(wff, rc1, maestro=False, iterations=iterations, forks=forks, subforks=subforks, data_size=size)
                    elif cdo=='lustre':
                        SCRATCH_PATH =os.getcwd()
                        BEEGFS_PATH  =os.getcwd()                        
                        # disabling dynamic provisioning to avoinf start/stopping it many times
                        wff = Maestro_Workflow(cdo_dependencies, name="demo-filemode.yml", pool_manager=False, dynamic_provisioning=False, infer_dependencies=False)
                        build_transformation_catalog(wff)
                        file3 = generate_demo_workflow(wff, rc1, maestro=False, iterations=iterations, forks=forks, subforks=subforks, data_size=size)
                    else:
                        print("Error, wrong cdo/beegfs/lustre param")
                        
                    start = time.time()
                    wff.execute_using_splinter(srun)
                    end = time.time()
                    elapsed = end-start
                                            
                    print(f'CSVData, Args_size, {size}, iterations, {iterations}, forks, {forks}, IO, {cdo}, Elapsed, {elapsed}')
                    # stime = time.strftime("%Y-%m-%d.%H:%M:%S", time.gmtime())
                    # os.rename('commands.txt', 'commands-' + stime + '.txt')

                    count += 1
                    # if count>=1:
                    #     raise GetOutOfLoop
except GetOutOfLoop:
    pass

print('Done')


# In[ ]:


#srun = True
#wfm.execute_using_splinter(srun)


# In[ ]:


#wfo.plan(submit=True, sites=['condorpool'], cleanup=False)\
# wfm.plan(submit=True, cleanup=False, sites=["condorpool"],verbose=0)\
#     .wait()\
#     .analyze()\
#     .statistics()


# In[ ]:


#wfm.halt()

