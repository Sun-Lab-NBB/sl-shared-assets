"""This module provides the assets for running data processing pipelines on the Sun lab's compute servers."""

import copy
from enum import IntEnum, StrEnum
from pathlib import Path
from dataclasses import field, dataclass

from filelock import FileLock
from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig


class TrackerFiles(StrEnum):
    """Defines the set of files used by Sun lab's data processing pipelines to track their runtime progress."""

    MANIFEST = "manifest_generation_tracker.yaml"
    """Tracks the state of the project manifest generation pipeline."""
    CHECKSUM = "checksum_resolution_tracker.yaml"
    """Tracks the state of the session's checksum resolution pipeline."""
    TRANSFER = "data_transfer_tracker.yaml"
    """Tracks the state of the session's transfer (migration) pipeline."""
    BEHAVIOR = "behavior_processing_tracker.yaml"
    """Tracks the state of the session's behavior log processing pipeline."""
    SUITE2P = "suite2p_processing_tracker.yaml"
    """Tracks the state of the session's single-day suite2p processing pipeline."""
    VIDEO = "video_processing_tracker.yaml"
    """Tracks the state of the session's video (DeepLabCut) processing pipeline."""
    MULTIDAY = "multiday_processing_tracker.yaml"
    """Tracks the state of the dataset's multiday suite2p processing pipeline."""
    FORGING = "dataset_forging_tracker.yaml"
    """Tracks the state of the dataset's creation (forging) pipeline."""


class ProcessingPipelines(StrEnum):
    """Defines the set of data processing pipelines currently used in the Sun lab."""

    MANIFEST = "manifest generation"
    """Regenerates the target project's manifest .feather file."""
    CHECKSUM = "checksum resolution"
    """Generates or verifies the target session's data integrity checksum."""
    TRANSFER = "data transfer"
    """Transfers the target session's data directory from the source directory to the target directory."""
    BEHAVIOR = "behavior processing"
    """Extracts the session's behavior data from the .npz log archives generated during the target session's runtime."""
    SUITE2P = "single-day suite2p processing"
    """Extracts the cell activity data from the 2-photon imaging TIFF files generated during the target session's 
    runtime."""
    VIDEO = "video processing"
    """Extracts the animal pose estimation data from the MP4 video frames acquired during the target session's 
    runtime."""
    MULTIDAY = "multi-day suite2p processing"
    """Tracks the cells imaged during every session that makes up the dataset across days."""
    FORGING = "dataset forging"
    """Extracts and integrates the processed data from all sources and sessions making up the dataset into the unified 
    dataset.feather file."""


class ProcessingStatus(IntEnum):
    """Defines the status codes used to communicate the runtime state of all Sun lab processing pipelines.

    Notes:
        The status codes from this enumeration track the state of the pipeline as a whole, instead of tracking the
        state of the individual jobs that make up the pipeline.
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
    """Tracks the state of a data processing pipeline and provides tools for communicating this state between multiple
    processes in a thread-safe manner.

    Note:
        A 'manager process' is the highest-level process that manages the tracked pipeline. When a pipeline runs on
        remote compute servers, the manager process is typically the process running on the user PC that submits the
        remote processing jobs to the compute server.

        The processing trackers work similar to '.lock' files. When a pipeline starts running on the remote server, its
        tracker is switched to the 'running' (locked) state until the pipeline completes, aborts, or encounters an
        error. When the tracker is locked, all modifications to the tracker have to originate from the manager process
        that started the pipeline.
    """

    file_path: Path
    """The path to the .YAML file used to cache the tracker data on disk."""
    _complete: bool = False
    """Tracks whether the processing pipeline managed by this tracker has finished successfully."""
    _encountered_error: bool = False
    """Tracks whether the processing pipeline managed by this tracker has encountered a runtime error."""
    _running: bool = False
    """Tracks whether the processing pipeline managed by this tracker is currently running."""
    _manager_id: int = -1
    """The unique identifier of the manager process that started the pipeline's execution."""
    lock_path: str = field(init=False)
    """The path to the .LOCK file used to ensure thread-safe access to the tracker's data."""
    _job_count: int = 1
    """The total number of jobs to be executed as part of the tracked pipeline."""
    _completed_jobs: int = 0
    """The total number of jobs completed by the tracked pipeline."""

    def __post_init__(self) -> None:
        """Resolves the .LOCK file for the managed tracker .YAML file."""
        # Generates the .lock file path for the target tracker .yaml file.
        if self.file_path is not None:
            self.lock_path = str(self.file_path.with_suffix(self.file_path.suffix + ".lock"))

            # Ensures that the input processing tracker file name is supported.
            if self.file_path.name not in tuple(TrackerFiles):
                message = (
                    f"Unsupported processing tracker file encountered when instantiating a ProcessingTracker "
                    f"instance: {self.file_path}. Currently, only the following tracker filenames are "
                    f"supported: {', '.join(tuple(TrackerFiles))}."
                )
                console.error(message=message, error=ValueError)

        else:
            self.lock_path = ""

    def _load_state(self) -> None:
        """Reads the current processing state from the wrapped .YAML file."""
        if self.file_path.exists():
            # Loads the data for the state values but does not replace the file path or lock attributes.
            instance: ProcessingTracker = self.from_yaml(self.file_path)
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
        """Caches the current processing state stored inside the instance's attributes as a.YAML file."""
        # Resets the lock_path and file_path to None before dumping the data to .YAML to avoid issues with loading it
        # back.
        temp_file_path, temp_lock_path = self.file_path, self.lock_path
        try:
            self.file_path = None  # type: ignore[assignment]
            self.lock_path = None  # type: ignore[assignment]
            self.to_yaml(file_path=temp_file_path)
        finally:
            self.file_path, self.lock_path = temp_file_path, temp_lock_path

    def start(self, manager_id: int, job_count: int = 1) -> None:
        """Configures the tracker file to indicate that the tracked processing pipeline is currently running.

        Args:
            manager_id: The unique identifier of the manager process starting the pipeline execution.
            job_count: The total number of jobs to be executed as part of the tracked pipeline's runtime.

        Raises:
            TimeoutError: If the .LOCK file for the tracker .YAML file cannot be acquired within the timeout period.
            PermissionError: If another manager process is currently holding exclusive access to the pipeline's tracker.
        """
        # Acquires the lock
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()

            # If the pipeline is already running from a different process, aborts with an error.
            if self._running and manager_id != self._manager_id:
                message = (
                    f"Unable to start the processing pipeline from the manager process with id {manager_id}. The "
                    f"{self.file_path.name} tracker file indicates that the manager process with id {self._manager_id} "
                    f"is currently executing the pipeline. Only a single manager process is allowed to execute "
                    f"the pipeline at the same time."
                )
                console.error(message=message, error=PermissionError)
                # Fallback to appease mypy, should not be reachable
                raise PermissionError(message)  # pragma: no cover

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
        """Configures the tracker file to indicate that the tracked processing pipeline encountered a runtime error.

        Args:
            manager_id: The unique identifier of the manager process reporting the pipeline's runtime error.

        Raises:
            TimeoutError: If the .Lock file for the tracker .YAML file cannot be acquired within the timeout period.
            PermissionError: If another manager process is currently holding exclusive access to the pipeline's tracker.
        """
        lock = FileLock(self.lock_path)
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
                console.error(message=message, error=PermissionError)
                # Fallback to appease mypy, should not be reachable
                raise PermissionError(message)  # pragma: no cover

            # Indicates that the pipeline aborted with an error
            self._running = False
            self._manager_id = -1
            self._complete = False
            self._encountered_error = True
            self._save_state()

    def stop(self, manager_id: int) -> None:
        """Configures the tracker file to increment the completed job counter and, if all jobs have been completed,
        indicate that the tracked processing pipeline has been completed.

        Args:
            manager_id: The unique identifier of the manager process reporting the pipeline's progress.

        Raises:
            TimeoutError: If the .Lock file for the tracker .YAML file cannot be acquired within the timeout period.
            PermissionError: If another manager process is currently holding exclusive access to the pipeline's tracker.
        """
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()

            # If the pipeline is not running, does not do anything
            if not self._running:
                return

            # Ensures that only the active manager process can report pipeline completion using the tracker file
            if manager_id != self._manager_id:
                message = (
                    f"Unable to report that the processing pipeline has completed from the manager "
                    f"process with id {manager_id}. The {self.file_path.name} tracker file indicates that the pipeline "
                    f"is managed by the process with id {self._manager_id}, preventing other processes from "
                    f"interfacing with the pipeline."
                )
                console.error(message=message, error=PermissionError)
                # Fallback to appease mypy, should not be reachable
                raise PermissionError(message)  # pragma: no cover

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
        """Resets the tracker file to the default state, clearing all state and ownership information.

        Notes:
            This method should only be used for emergency recovery from improper processing shutdowns. It can be called
            by any process to reset any tracker file, but it does not attempt to terminate the processes that the
            current tracker's owner might have deployed to work with the session's data.
        """
        lock = FileLock(self.lock_path)
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
    def complete(self) -> bool:
        """Returns True if the tracked processing pipeline has been completed successfully."""
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._complete

    @property
    def encountered_error(self) -> bool:
        """Returns True if the tracked processing pipeline has been terminated due to a runtime error."""
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._encountered_error

    @property
    def running(self) -> bool:
        """Returns True if the tracked processing pipeline is currently running."""
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()
            return self._running
