"""This module provides tools used to run complex data processing pipelines on remote compute servers. A processing
pipeline represents a higher unit of abstraction relative to the Job class, often leveraging multiple sequential or
parallel jobs to process the data.
"""

import copy
from enum import IntEnum, StrEnum
from pathlib import Path
from dataclasses import field, dataclass

from filelock import FileLock
from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig


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
            self._job_count = copy.copy(instance._job_count)
            self._completed_jobs = copy.copy(instance._completed_jobs)
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
            if self._running and manager_id == self._manager_id:
                return

            # Otherwise, locks the pipeline for the current manager process and updates the cached tracker data
            self._running = True
            self._manager_id = manager_id
            self._complete = False
            self._encountered_error = False
            self._job_count = job_count
            self._completed_jobs = 0
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
            else:
                # Otherwise, updates the completed job counter, but does not change any other state variables.
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
        successfully and that the pipeline is not currently ongoing.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._complete

    @property
    def encountered_error(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing pipeline has aborted due
        to encountering an error.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._encountered_error

    @property
    def is_running(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing pipeline is currently
        ongoing.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._running
