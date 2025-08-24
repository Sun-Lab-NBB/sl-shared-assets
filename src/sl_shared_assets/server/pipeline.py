"""This module provides tools used to run complex data processing pipelines on remote compute servers. A processing
pipeline represents a higher unit of abstraction relative to the Job class, often leveraging multiple sequential or
parallel jobs to process the data."""

import copy
from enum import IntEnum, StrEnum
from random import randint
import shutil as sh
from pathlib import Path
from dataclasses import field, dataclass

from xxhash import xxh3_64
from filelock import FileLock
from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig
from ataraxis_time.time_helpers import get_timestamp

from .job import Job
from .server import Server


class TrackerFileNames(StrEnum):
    """Stores the names of the processing tacker .yaml files used by the Sun lab data preprocessing, processing, and
    dataset formation pipelines to track the pipeline's progress.

     Notes:
        The elements in this enumeration match the elements in the ProcessingPipelines enumeration, since each valid
        ProcessingPipeline instance has an associated ProcessingTracker file instance.
    """

    MANIFEST = "manifest_generation_tracker.yaml"
    """This file is used to track the state of the project manifest generation pipeline."""
    CHECKSUM = "checksum_resolution_tracker.yaml"
    """This file is used to track the state of the checksum resolution pipeline."""
    PREPARATION = "processing_preparation_tracker.yaml"
    """This file is used to track the state of the data processing preparation pipeline."""
    BEHAVIOR = "behavior_processing_tracker.yaml"
    """This file is used to track the state of the behavior log processing pipeline."""
    SUITE2P = "suite2p_processing_tracker.yaml"
    """This file is used to track the state of the single-day suite2p processing pipeline."""
    VIDEO = "video_processing_tracker.yaml"
    """This file is used to track the state of the video (DeepLabCut) processing pipeline."""
    FORGING = "dataset_forging_tracker.yaml"
    """This file is used to track the state of the dataset creation (forging) pipeline."""
    MULTIDAY = "multiday_processing_tracker.yaml"
    """This file is used to track the state of the multiday suite2p processing pipeline."""
    ARCHIVING = "data_archiving_tracker.yaml"
    """This file is used to track the state of the data archiving pipeline."""


class ProcessingPipelines(StrEnum):
    """Stores the names of the data processing pipelines currently used in the lab.

    Notes:
        The elements in this enumeration match the elements in the TrackerFileNames enumeration, since each valid
        ProcessingPipeline instance has an associated ProcessingTracker file instance.

        The order of pipelines in this enumeration loosely follows the sequence in which they are executed during the
        Sun lab data workflow.
    """

    MANIFEST = "manifest generation"
    """Project manifest generation pipeline. This pipeline is generally not used in most runtime contexts. It allows 
    manually regenerating the project manifest .feather file, which is typically only used during testing. All other 
    pipeline automatically conduct the manifest (re)generation at the end of their runtime."""
    CHECKSUM = "checksum resolution"
    """Checksum resolution pipeline. Primarily, it is used to verify that the raw data has been transferred to the 
    remote storage server from the main acquisition system PC intact. This pipeline is also used to regenerate 
    (re-checksum) the data stored on the remote compute server."""
    PREPARATION = "processing preparation"
    """Data processing preparation pipeline. Since the compute server uses a two-volume design with a slow (HDD) storage
    volume and a fast (NVME) working volume, to optimize data processing performance, the data needs to be transferred 
    to the working volume before processing. This pipeline copies the raw data for the target session from the storage 
    volume to the working volume."""
    BEHAVIOR = "behavior processing"
    """Behavior processing pipeline. This pipeline is used to process .npz log files to extract animal behavior data 
    acquired during a single session (day)."""
    SUITE2P = "single-day suite2p processing"
    """Single-day suite2p pipeline. This pipeline is used to extract the cell activity data from 2-photon imaging data 
    acquired during a single session (day)."""
    VIDEO = "video processing"
    """DeepLabCut (Video) processing pipeline. This pipeline is used to extract animal pose estimation data from the 
    behavior video frames acquired during a single session (day)."""
    MULTIDAY = "multi-day suite2p processing"
    """Multi-day suite2p processing (cell tracking) pipeline. This pipeline is used to track cells processed with the 
    single-day suite2p pipelines across multiple days."""
    FORGING = "dataset forging"
    """Dataset creation (forging) pipeline. This pipeline typically runs after the multi-day pipeline. It extracts and 
    integrates the processed data from all sources into a unified dataset."""
    ARCHIVING = "data archiving"
    """Data archiving pipeline. To conserve the (limited) space on the remote compute server's fast working volume, 
    once the data has been processed and integrated into a stable dataset, the processed data folder is moved to the 
    storage volume. After the data is moved, all folders under the root session folder on the processed data volume are 
    deleted to free up the processing volume space."""


class ProcessingStatus(IntEnum):
    """Maps integer-based processing pipeline status (state) codes to human-readable names.

    The codes from this enumeration are used by the ProcessingPipeline class to communicate the status of the managed
    pipelines to manager processes that oversee the execution of each pipeline.

    Notes:
        The status codes from this enumeration track the state of the pipeline as a whole, instead of tracking the
        state of each job that comprises the pipeline.
    """

    RUNNING = 0
    """The pipeline is currently running on the remote server. It may be executed (in progress) or waiting for 
    the required resources to become available (queued)."""
    SUCCEEDED = 1
    """The server has successfully completed the processing pipeline."""
    FAILED = 2
    """The server has failed to complete the pipeline due to a runtime error."""
    ABORTED = 3
    """The pipeline execution has been aborted prematurely, either by the manager process or due to an overriding 
    request from another user."""


@dataclass()
class ProcessingTracker(YamlConfig):
    """Wraps the .yaml file that tracks the state of a data processing pipeline and provides tools for communicating
    this state between multiple processes in a thread-safe manner.

    This class is used by all data processing pipelines running on the remote compute server(s) to prevent race
    conditions. It is also used to evaluate the status (success / failure) of each pipeline as they are executed by the
    remote server.

    Note:
        This instance frequently refers to the 'manager process' in method documentation. A 'manager process' is the
        highest-level process that manages the tracked pipeline. When a pipeline runs on remote compute servers, the
        manager process is typically the process running on the non-server machine (user PC) that submits the remote
        processing jobs to the compute server. The worker process(es) that run the processing job(s) on the remote
        compute servers are not considered manager processes.

        The processing trackers work similar to 'lock' files. When a pipeline starts running on the remote server, its
        tracker is switched into the 'running' (locked) state until the pipeline completes, aborts, or encounters an
        error. When the tracker is locked, all modifications to the tracker have to originate from the same manager
        process that started the pipeline. This feature supports running complex processing pipelines that use multiple
        concurrent and / or sequential processing jobs on the remote server.
    """

    file_path: Path
    """Stores the path to the .yaml file used to cache the tracker data on disk. The class instance functions as a 
    wrapper around the data stored inside the specified .yaml file."""
    _complete: bool = False
    """Tracks whether the processing pipeline managed by this tracker has finished successfully."""
    _encountered_error: bool = False
    """Tracks whether the processing pipeline managed by this tracker has encountered an error and has finished 
    unsuccessfully."""
    _running: bool = False
    """Tracks whether the processing pipeline managed by this tracker is currently running."""
    _manager_id: int = -1
    """Stores the xxHash3-64 hash value that represents the unique identifier of the manager process that started the 
    pipeline. The manager process is typically running on a remote control machine (computer) and is used to 
    support processing runtimes that are distributed over multiple separate batch jobs on the compute server. This 
    ID should be generated using the 'generate_manager_id()' function exposed by this library."""
    _lock_path: str = field(init=False)
    """Stores the path to the .lock file used to ensure that only a single process can simultaneously access the data 
    stored inside the tracker file."""
    _job_count: int = 1
    """Stores the total number of jobs to be executed as part of the tracked pipeline. This is used to 
    determine when the tracked pipeline is fully complete when tracking intermediate job outcomes."""
    _completed_jobs: int = 0
    """Stores the total number of jobs completed by the tracked pipeline. This is used together with the '_job_count' 
    field to determine when the tracked pipeline is fully complete."""

    def __post_init__(self) -> None:
        # Generates the .lock file path for the target tracker .yaml file.
        if self.file_path is not None:
            self._lock_path = str(self.file_path.with_suffix(self.file_path.suffix + ".lock"))

            # Ensures that the input processing tracker file name is supported.
            if self.file_path.name not in tuple(TrackerFileNames):
                message = (
                    f"Unsupported processing tracker file encountered when instantiating a ProcessingTracker "
                    f"instance: {self.file_path}. Currently, only the following tracker file names are "
                    f"supported: {', '.join(tuple(TrackerFileNames))}."
                )
                console.error(message=message, error=ValueError)

        else:
            self._lock_path = ""

    def _load_state(self) -> None:
        """Reads the current processing state from the wrapped .YAML file."""
        if self.file_path.exists():
            # Loads the data for the state values but does not replace the file path or lock attributes.
            instance: ProcessingTracker = self.from_yaml(self.file_path)  # type: ignore
            self._complete = copy.copy(instance._complete)
            self._encountered_error = copy.copy(instance._encountered_error)
            self._running = copy.copy(instance._running)
            self._manager_id = copy.copy(instance._manager_id)
        else:
            # Otherwise, if the tracker file does not exist, generates a new .yaml file using default instance values
            # and saves it to disk using the specified tracker file path.
            self._save_state()

    def _save_state(self) -> None:
        """Saves the current processing state stored inside instance attributes to the specified .YAML file."""
        # Resets the _lock_path and file_path to None before dumping the data to .YAML to avoid issues with loading it
        # back.
        original = copy.deepcopy(self)
        original.file_path = None  # type: ignore
        original._lock_path = None  # type: ignore
        original.to_yaml(file_path=self.file_path)

    def start(self, manager_id: int, job_count: int = 1) -> None:
        """Configures the tracker file to indicate that a manager process is currently executing the tracked processing
        pipeline.

        Calling this method locks the tracked session and processing pipeline combination to only be accessible from the
        manager process that calls this method. Calling this method for an already running pipeline managed by the same
        process does not have any effect, so it is safe to call this method at the beginning of each processing job that
        makes up the pipeline.

        Args:
            manager_id: The unique identifier of the manager process which attempts to start the pipeline tracked by
                this tracker file.
            job_count: The total number of jobs to be executed as part of the tracked pipeline.

        Raises:
            TimeoutError: If the .lock file for the target .YAML file cannot be acquired within the timeout period.
        """
        # Acquires the lock
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()

            # If the pipeline is already running from a different process, aborts with an error.
            if self._running and manager_id != self._manager_id:
                message = (
                    f"Unable to start the processing pipeline from the manager process with id {manager_id}. The "
                    f"{self.file_path.name} tracker file indicates that the manager process with id {self._manager_id} "
                    f"is currently executing the tracked pipeline. Only a single manager process is allowed to execute "
                    f"the pipeline at the same time."
                )
                console.error(message=message, error=RuntimeError)
                raise RuntimeError(message)  # Fallback to appease mypy, should not be reachable

            # Otherwise, if the pipeline is already running for the current manager process, returns without modifying
            # the tracker data.
            elif self._running and manager_id == self._manager_id:
                return

            # Otherwise, locks the pipeline for the current manager process and updates the cached tracker data
            self._running = True
            self._manager_id = manager_id
            self._complete = False
            self._encountered_error = False
            self._job_count = job_count
            self._save_state()

    def error(self, manager_id: int) -> None:
        """Configures the tracker file to indicate that the tracked processing pipeline encountered an error and failed
        to complete.

        This method unlocks the pipeline, allowing other manager processes to interface with the tracked pipeline. It
        also updates the tracker file to reflect that the pipeline was interrupted due to an error, which is used by the
        manager processes to detect and handle processing failures.

        Args:
            manager_id: The unique identifier of the manager process which attempts to report that the pipeline tracked
                by this tracker file has encountered an error.

        Raises:
            TimeoutError: If the .lock file for the target .YAML file cannot be acquired within the timeout period.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()

            # If the pipeline is not running, returns without doing anything
            if not self._running:
                return

            # Ensures that only the active manager process can report pipeline errors using the tracker file
            if manager_id != self._manager_id:
                message = (
                    f"Unable to report that the processing pipeline has encountered an error from the manager process "
                    f"with id {manager_id}. The {self.file_path.name} tracker file indicates that the pipeline is "
                    f"managed by the process with id {self._manager_id}, preventing other processes from interfacing "
                    f"with the pipeline."
                )
                console.error(message=message, error=RuntimeError)
                raise RuntimeError(message)  # Fallback to appease mypy, should not be reachable

            # Indicates that the pipeline aborted with an error
            self._running = False
            self._manager_id = -1
            self._complete = False
            self._encountered_error = True
            self._save_state()

    def stop(self, manager_id: int) -> None:
        """Configures the tracker file to indicate that the tracked processing pipeline has been completed successfully.

        This method unlocks the pipeline, allowing other manager processes to interface with the tracked pipeline. It
        also configures the tracker file to indicate that the pipeline has been completed successfully, which is used
        by the manager processes to detect and handle processing completion.

        Notes:
            This method tracks how many jobs executed as part of the tracked pipeline have been completed and only
            marks the pipeline as complete if all it's processing jobs have been completed.

        Args:
            manager_id: The unique identifier of the manager process which attempts to report that the pipeline tracked
                by this tracker file has been completed successfully.

        Raises:
            TimeoutError: If the .lock file for the target .YAML file cannot be acquired within the timeout period.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()

            # If the pipeline is not running, does not do anything
            if not self._running:
                return

            # Ensures that only the active manager process can report pipeline completion using the tracker file
            if manager_id != self._manager_id:
                message = (
                    f"Unable to report that the processing pipeline has completed successfully from the manager "
                    f"process with id {manager_id}. The {self.file_path.name} tracker file indicates that the pipeline "
                    f"is managed by the process with id {self._manager_id}, preventing other processes from "
                    f"interfacing with the pipeline."
                )
                console.error(message=message, error=RuntimeError)
                raise RuntimeError(message)  # Fallback to appease mypy, should not be reachable

            # Increments completed job tracker
            self._completed_jobs += 1

            # If the pipeline has completed all required jobs, marks the pipeline as complete (stopped)
            if self._completed_jobs >= self._job_count:
                self._running = False
                self._manager_id = -1
                self._complete = True
                self._encountered_error = False
                self._save_state()

    def abort(self) -> None:
        """Resets the pipeline tracker file to the default state.

        This method can be used to reset the pipeline tracker file, regardless of the current pipeline state. Unlike
        other instance methods, this method can be called from any manager process, even if the pipeline is already
        locked by another process. This method is only intended to be used in the case of emergency to unlock a
        deadlocked pipeline.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file.
            self._load_state()

            # Resets the tracker file to the default state. Note, does not indicate that the pipeline completed nor
            # that it has encountered an error.
            self._running = False
            self._manager_id = -1
            self._completed_jobs = 0
            self._job_count = 1
            self._complete = False
            self._encountered_error = False
            self._save_state()

    @property
    def is_complete(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing pipeline has been completed
        successfully and that the pipeline is not currently ongoing."""
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._complete

    @property
    def encountered_error(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing pipeline has aborted due
        to encountering an error."""
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._encountered_error

    @property
    def is_running(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing pipeline is currently
        ongoing."""
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._running


@dataclass()
class ProcessingPipeline:
    """Provides an interface to construct and execute data processing pipelines on the target remote compute server.

    This class functions as an interface for all data processing pipelines running on Sun lab compute servers. It is
    pipeline-type-agnostic and works for all data processing pipelines used in the lab. After instantiation, the class
    automatically handles all interactions with the server necessary to run the remote processing pipeline and
    verify the runtime outcome via the runtime_cycle() method that has to be called cyclically until the pipeline is
    complete.

    Notes:
        Each pipeline is executed as a series of one or more stages with each stage using one or more parallel jobs.
        Therefore, each pipeline can be seen as an execution graph that sequentially submits batches of jobs to the
        remote server. The processing graph for each pipeline is fully resolved at the instantiation of this class, so
        each instance contains the necessary data to run the entire processing pipeline.

        The minimum self-contained unit of the processing pipeline is a single job. Since jobs can depend on the output
        of other jobs, they are organized into stages based on the dependency graph between jobs. Combined with cluster
        management software, such as SLURM, this class can efficiently execute processing pipelines on scalable compute
        clusters.
    """

    pipeline_type: ProcessingPipelines
    """Stores the name of the processing pipeline managed by this instance. Primarily, this is used to identify the 
    pipeline to the user in terminal messages and logs."""
    server: Server
    """Store the reference to the Server object used to interface with the remote server running the pipeline."""
    manager_id: int
    """The unique identifier for the manager process that constructs and manages the runtime of the tracked pipeline."""
    jobs: dict[int, tuple[tuple[Job, Path], ...]]
    """Stores the dictionary that maps the pipeline processing stage integer-codes to two-element tuples. Each tuple
    stores the Job object and the path to its remote working directory to be submitted to the server as part of that 
    executing that stage."""
    remote_tracker_path: Path
    """Stores the path to the pipeline's processing tracker .yaml file stored on the remote compute server."""
    local_tracker_path: Path
    """Stores the path to the pipeline's processing tracker .yaml file on the local machine. The remote file is 
    pulled to this location when the instance verifies the outcome of the tracked processing pipeline."""
    session: str
    """Stores the ID of the session whose data is being processed by the tracked pipeline."""
    animal: str
    """Stores the ID of the animal whose data is being processed by the tracked pipeline."""
    project: str
    """Stores the name of the project whose data is being processed by the tracked pipeline."""
    keep_job_logs: bool = False
    """Determines whether to keep the logs for the jobs making up the pipeline execution graph or (default) to remove 
    them after pipeline successfully ends its runtime. If the pipeline fails to complete its runtime, the logs are kept 
    regardless of this setting."""
    pipeline_status: ProcessingStatus | int = ProcessingStatus.RUNNING
    """Stores the current status of the tracked remote pipeline. This field is updated each time runtime_cycle() 
    instance method is called."""
    _pipeline_stage: int = 0
    """Stores the current stage of the tracked pipeline. This field is monotonically incremented by the runtime_cycle()
    method to sequentially submit batches of jobs to the server in a processing-stage-driven fashion."""

    def __post_init__(self) -> None:
        """Carries out the necessary filesystem setup tasks to support pipeline execution."""

        # Ensures that the input processing tracker file name is supported.
        if self.pipeline_type not in tuple(ProcessingPipelines):
            message = (
                f"Unsupported processing pipeline type encountered when instantiating a ProcessingPipeline "
                f"instance: {self.pipeline_type}. Currently, only the following pipeline types are "
                f"supported: {', '.join(tuple(ProcessingPipelines))}."
            )
            console.error(message=message, error=ValueError)

        ensure_directory_exists(self.local_tracker_path)  # Ensures that the local temporary directory exists

    def runtime_cycle(self) -> None:
        """Checks the current status of the tracked pipeline and, if necessary, submits additional batches of jobs to
        the remote server to progress the pipeline.

        This method is the main entry point for all interactions with the processing pipeline managed by this instance.
        It checks the current state of the pipeline, advances the pipeline's processing stage, and submits the necessary
        jobs to the remote server. The runtime manager process should call this method repeatedly (cyclically) to run
        the pipeline until the 'is_running' property of the instance returns True.

        Notes:
            While the 'is_running' property can be used to determine whether the pipeline is still running, to resolve
            the final status of the pipeline (success or failure), the manager process should access the
            'status' instance property.
        """

        # This clause is executed the first time the method is called for the newly initialized pipeline tracker
        # instance. It submits the first batch of processing jobs (first stage) to the remote server. For one-stage
        # pipelines, this is the only time when pipeline jobs are submitted to the server.
        if self._pipeline_stage == 0:
            self._pipeline_stage += 1
            self._submit_jobs()

        # Waits until all jobs submitted to the server as part of the current processing stage are completed before
        # advancing further.
        for job, _ in self.jobs[self._pipeline_stage]:  # Ignores working directories as part of this iteration.
            if not self.server.job_complete(job=job):
                return

        # If all jobs for the current processing stage have completed, checks the pipeline's processing tracker file to
        # determine if all jobs completed successfully.
        self.server.pull_file(remote_file_path=self.remote_tracker_path, local_file_path=self.local_tracker_path)
        tracker = ProcessingTracker(self.local_tracker_path)

        # If the stage failed due to encountering an error, removes the local tracker copy and marks the pipeline
        # as 'failed'. It is expected that the pipeline state is then handed by the manager process to notify the
        # user about the runtime failure.
        if tracker.encountered_error:
            sh.rmtree(self.local_tracker_path.parent)  # Removes local temporary data
            self.pipeline_status = ProcessingStatus.FAILED  # Updates the processing status to 'failed'

        # If this was the last processing stage, the tracker indicates that the processing has been completed. In this
        # case, initializes the shutdown sequence:
        elif tracker.is_complete:
            sh.rmtree(self.local_tracker_path.parent)  # Removes local temporary data
            self.pipeline_status = ProcessingStatus.SUCCEEDED  # Updates the job status to 'succeeded'

            # If the pipeline was configured to remove logs after completing successfully, removes the runtime log for
            # each job submitted as part of this pipeline from the remote server.
            if not self.keep_job_logs:
                for stage_jobs in self.jobs.values():
                    for _, directory in stage_jobs:  # Ignores job objects as part of this iteration.
                        self.server.remove(remote_path=directory, recursive=True, is_dir=True)

        # If the processing is not complete (according to the tracker), this indicates that the pipeline has more
        # stages to execute. In this case, increments the processing stage tracker and submits the next batch of jobs
        # to the server.
        elif tracker.is_running:
            self._pipeline_stage += 1
            self._submit_jobs()

        # The final and the rarest state: the pipeline was aborted before it finished the runtime. Generally, this state
        # should not be encountered during most runtimes.
        else:
            self.pipeline_status = ProcessingStatus.ABORTED

    def _submit_jobs(self) -> None:
        """This worker method submits the processing jobs for the currently active processing stage to the remote
        server.

        It is used internally by the runtime_cycle() method to iteratively execute all stages of the managed processing
        pipeline on the remote server.
        """
        for job, _ in self.jobs[self._pipeline_stage]:
            self.server.submit_job(job=job, verbose=False)  # Silences terminal printouts

    @property
    def is_running(self) -> bool:
        """Returns True if the pipeline is currently running, False otherwise."""
        if self.pipeline_status == ProcessingStatus.RUNNING:
            return True
        return False

    @property
    def status(self) -> ProcessingStatus:
        """Returns the current status of the pipeline packaged into a ProcessingStatus instance."""
        return ProcessingStatus(self.pipeline_status)


def generate_manager_id() -> int:
    """Generates and returns a unique integer value that can be used to identify the manager process that calls
    this function.

    The identifier is generated based on the current timestamp, accurate to microseconds, and a random number between 1
    and 9999999999999. This ensures that the identifier is unique for each function call. The generated identifier
    string is converted to a unique integer value using the xxHash-64 algorithm before it is returned to the caller.

    Notes:
        This function should be used to generate manager process identifiers for working with ProcessingTracker
        instances from sl-shared-assets version 4.0.0 and above.
    """
    timestamp = get_timestamp()
    random_number = randint(1, 9999999999999)
    manager_id = f"{timestamp}_{random_number}"
    id_hash = xxh3_64()
    id_hash.update(manager_id)
    return id_hash.intdigest()
