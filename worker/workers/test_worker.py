from ..worker import Worker
import threading
from crscommon.jobs import TesterJob
import crscommon
import time

import logging
l = logging.getLogger('crs.worker.workers.test_worker')
l.setLevel('DEBUG')
LOITER_TIME = 300  # 5 - minutes
MAX_RETRY_TIMES = 10000  # maximum number of times to try for jobs to run


class CRSAPIWrapper:
    def __init__(self):
        # TODO: some common stuff
        pass

    def get_testjobs(self):
        """

        :return:
        """
        all_jobs = []
        for b in crscommon.api.get_all_binaries():
            for testcase_id in crscommon.api.get_testcases_for_testing(b.ct.id, b.binary_id):
                all_jobs.append(TesterJob(b, testcase_id))
        return all_jobs

    def mark_testjob_busy(self, busy_test_job):
        """

        :param busy_test_job:
        :return:
        """
        return crscommon.api.mark_testcase_busy(busy_test_job.binary.ct.ct_id, busy_test_job.binary.binary_id,
                                                busy_test_job.testcase_id)


class TestWorker(Worker):
    def __init__(self, number_of_vms=2):
        self.max_vms = number_of_vms
        self.free_vms = set()
        # TODO: Change this
        self.crshelper = CRSAPIWrapper()
        # Lock to access free VMs.
        self.vm_lock = threading.Lock()
        # TODO: Set up those number of VMs

    def get_free_vm(self):
        """

        :return:
        """
        to_ret = None
        if self.free_vms is not None:
            with self.vm_lock:
                if len(self.free_vms) > 0:
                    to_ret = self.free_vms.pop()
        else:
            l.error("Free VMs member is None. This should never happen.")
        return to_ret

    def put_free_vm(self, to_free_vm):
        """

        :param to_free_vm:
        :return:
        """
        if to_free_vm is not None:
            with self.vm_lock:
                if self.free_vms is None:
                    self.free_vms = set()
                self.free_vms.add(to_free_vm)

    def _run(self, job, test_vm):
        """

        :param job:
        :param test_vm:
        :return:
        """
        # TODO: finish this
        l.debug("Trying to run job:" + str(job) + " on VM:" + str(test_vm))
        # Run Job
        # Update the result to do.
        pass

    def run(self, job):
        """

        :param job:
        :return: None
        """
        try:
            l.debug("Starting Test Worker")
            # Get the free VM.
            target_free_vm = self.get_free_vm()
            # Schedule the job
            self._run(job, target_free_vm)
            # Restore the free VM
            self.put_free_vm(target_free_vm)
            tries_remaining = MAX_RETRY_TIMES
            idle_sleep_time = (LOITER_TIME*1.0) / MAX_RETRY_TIMES
            while tries_remaining > 0:
                to_run_jobs = self.crshelper.get_testjobs()
                if len(to_run_jobs) > 0:
                    # if there are jobs to run, reset the tries.
                    for curr_job in to_run_jobs:
                        target_free_vm = self.get_free_vm()
                        if self.crshelper.mark_testjob_busy(curr_job):
                            self._run(curr_job, target_free_vm)
                        self.put_free_vm(target_free_vm)
                    tries_remaining = MAX_RETRY_TIMES
                else:
                    # Sleep only if there are no jobs to run
                    time.sleep(idle_sleep_time)
                    tries_remaining -= 1
            l.debug("Exiting Test Worker as there are no jobs to run")

        except Exception as e:
            l.error("Error occurred while trying to run job:" + str(job) + ", Exception:" + str(e))