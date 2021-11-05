#!/usr/bin/env python3

import subprocess
import time
import concurrent.futures

class task:
    _task_id = -1
    _command = "ls -1"
    _dependent_task_array = []
    _provider_task_array = []

    def __init__(self, task_id, command, dependent_task_array):
        self._task_id = task_id
        self._command = command
        # convert any file objects to string pathnames in arg list
        self._dependent_task_array = dependent_task_array

    def dependent_task_array(self):
        return self._dependent_task_array

    def command(self):
        return self._command

    def task_id(self):
        return self._task_id


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


class splinter_workflow:
    _task_array = []
    _pending_task_array = []
    _completed_task_array = []
    _task_status_array = []
    _njob = 0

    def add_task(self, task):
        self._task_array.append(task)

    def find_next_task(self):
        n_pending_task = len(self._pending_task_array)
        if n_pending_task != 0:
            for i in range(0, n_pending_task):
                if self.are_task_dependencies_satisfied(self._pending_task_array[i]):
                    return self._pending_task_array[i]
        return None

    def completed_task_status(self):
        for task_status in self._task_status_array:
            if task_status.future().done():
                return task_status
        return None

    def is_workflow_active(self):
        if len(self._pending_task_array) != 0:
            return True

        if len(self._task_status_array) != 0:
            return True

        return False

    def are_task_dependencies_satisfied(self, task):
        # race? : if a task completes whilst we are iterating this list?
        completed_task_id_array = [task.task_id() for task in self._completed_task_array]
        pending_task_id_array = [task.task_id() for task in self._pending_task_array]
        # for every parent of this task
        for dependent_task in task.dependent_task_array():
            # if a parent task isn't marked as completed, we cannot run
            if not dependent_task in completed_task_id_array:
                return False
            # if a parent task has not run yet, we cannot run
            if dependent_task in pending_task_id_array:
                return False
        return True

    def is_worker_available(self):
        if len(self._task_status_array) < self._njob:
            return True
        return False

    def execute_workflow(self, njob, poll_frequency):
        self._pending_task_array = self._task_array
        self._njob = njob

        with concurrent.futures.ThreadPoolExecutor(max_workers=njob) as executor:
            poll_loop = 0
            while self.is_workflow_active():
                print()
                completed_task_id_array = [task.task_id() for task in self._completed_task_array]
                pending_task_id_array = [task.task_id() for task in self._pending_task_array]
                print('Poll loop', poll_loop, ' : Completed tasks', completed_task_id_array,
                    ' : Pending tasks', pending_task_id_array)
                if self.is_worker_available():
                    # Launch as many tasks as possible in each polling window
                    task = self.find_next_task()
                    while task is not None:
                        self._pending_task_array.remove(task)
                        print("Submitting Job", task.task_id(), task.command())
                        future = executor.submit(subprocess.run, task.command(), stdout=subprocess.PIPE)
                        self._task_status_array.append(task_status(task, future))
                        # any more tasks ready to execute
                        task = self.find_next_task()

                # Clear as many tasks as possible in each polling window
                completed_task_status = self.completed_task_status()                        
                while completed_task_status is not None:
                    print("Job Completed", completed_task_status.task().task_id())
                    self._completed_task_array.append(
                        completed_task_status.task())
                    self._task_status_array.remove(completed_task_status)
                    # any more completed tasks?
                    completed_task_status = self.completed_task_status()                        

                time.sleep(poll_frequency)
                poll_loop += 1


if __name__ == "__main__":
    wf = splinter_workflow()
    wf.add_task(task(1, ["./test/tester", "10"], []))
    wf.add_task(task(2, ["./test/tester", "1"], []))
    wf.add_task(task(3, ["./test/tester", "5"], [2]))
    wf.add_task(task(4, ["./test/tester", "1"], [1]))

    wf.execute_workflow(2, 1)
