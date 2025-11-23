"""This module provides the assets for running data processing pipelines."""

import os
import copy
from enum import IntEnum
from pathlib import Path  # noqa: TC003
from dataclasses import field, dataclass

import xxhash
from filelock import FileLock
from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig


class ProcessingStatus(IntEnum):
    """Defines the status codes used by the ProcessingTracker instances to communicate the runtime state of each
    job making up the managed data processing pipeline.
    """

    SCHEDULED = 0
    """The job is scheduled for execution."""
    RUNNING = 1
    """The job is currently being executed."""
    SUCCEEDED = 2
    """The job has been completed."""
    FAILED = 3
    """The job encountered a runtime error and was not completed."""


@dataclass
class JobState:
    """Stores the metadata and the current runtime status of a single job in the processing pipeline."""

    status: ProcessingStatus = ProcessingStatus.SCHEDULED
    """The current status of the job."""
    slurm_job_id: int | None = None
    """The SLURM-assigned job ID, if running on a SLURM cluster."""


@dataclass()
class ProcessingTracker(YamlConfig):
    """Tracks the state of a data processing pipeline and provides tools for communicating this state between multiple
    processes and host-machines.

    Note:
        All modifications to the tracker file require the acquisition of the .lock file, which ensures exclusive
        access to the tracker's data, allowing multiple independent processes (jobs) to safely work with the same
        tracker file.
    """

    file_path: Path
    """The path to the .YAML file used to cache the tracker's data on disk."""
    _jobs: dict[str, JobState] = field(default_factory=dict)
    """Maps the unique identifiers of the jobs that make up the processing pipeline to their current state and 
    metadata."""
    lock_path: str = field(init=False)
    """The path to the .LOCK file used to ensure thread-safe access to the tracker's data."""

    def __post_init__(self) -> None:
        """Resolves the .LOCK file for the managed tracker .YAML file."""
        # Generates the .lock file path for the target tracker .yaml file.
        if self.file_path is not None:
            self.lock_path = str(self.file_path.with_suffix(self.file_path.suffix + ".lock"))
        else:
            self.lock_path = ""

        # Converts integer status values back to ProcessingStatus enumeration instances. The conversion to integers is
        # necessary for .YAML saving compatibility.
        for job_state in self._jobs.values():
            if isinstance(job_state.status, int):
                job_state.status = ProcessingStatus(job_state.status)

    @staticmethod
    def generate_job_id(session_path: Path, job_name: str) -> str:
        """Generates a unique hexadecimal job identifier based on the session's data path and the job's name using the
        xxHash64 checksum generator.

        Args:
            session_path: The path to the processed session's data directory.
            job_name: The unique name for the processing job.

        Returns:
            The unique hexadecimal identifier for the target job.
        """
        # Combines session path and job name into a single string for hashing
        combined = f"{session_path.resolve()}:{job_name}"
        # Generates and returns the xxHash64 hash
        return xxhash.xxh64(combined.encode("utf-8")).hexdigest()

    @staticmethod
    def _get_slurm_job_id() -> int | None:
        """Retrieves the SLURM-assigned job's ID from the environment, if available.

        Returns:
            The SLURM-assigned job's ID if running in a SLURM environment, None otherwise.
        """
        slurm_id = os.environ.get("SLURM_JOB_ID") or os.environ.get("SLURM_JOBID")
        return int(slurm_id) if slurm_id else None

    def _load_state(self) -> None:
        """Reads the processing pipeline's runtime state from the cached .YAML file."""
        if self.file_path.exists():
            # Loads the data for the state values but does not replace the file path or lock attributes.
            instance: ProcessingTracker = self.from_yaml(self.file_path)
            self._jobs = copy.deepcopy(instance._jobs)
        else:
            # Otherwise, if the tracker file does not exist, generates a new .yaml file using default instance values
            # and saves it to disk using the specified tracker file path.
            self._save_state()

    def _save_state(self) -> None:
        """Caches the current processing state stored inside the instance's attributes as a.YAML file."""
        # Resets the lock_path and file_path to None and jobs to a dictionary of integers before dumping the data to
        # .YAML to avoid issues with loading it back.
        temp_file_path, temp_lock_path, temp_jobs = self.file_path, self.lock_path, self._jobs

        # Converts enums to int for YAML serialization
        converted_jobs = {}
        for job_id, job_state in self._jobs.items():
            converted_jobs[job_id] = JobState(
                status=int(job_state.status),  # type: ignore[arg-type]
                slurm_job_id=job_state.slurm_job_id,
            )

        try:
            self.file_path = None  # type: ignore[assignment]
            self.lock_path = None  # type: ignore[assignment]
            self._jobs = converted_jobs
            self.to_yaml(file_path=temp_file_path)
        finally:
            self.file_path, self.lock_path, self.jobs = temp_file_path, temp_lock_path, temp_jobs

    def initialize_jobs(self, job_ids: list[str]) -> None:
        """Configures the tracker with the list of jobs to be executed during the pipeline's runtime.

        Args:
            job_ids: The list of unique identifiers for all jobs that make up the tracked pipeline.

        Raises:
            TimeoutError: If the .LOCK file for the tracker .YAML file cannot be acquired within the timeout period.
        """
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker's state from the .yaml file
            self._load_state()

            # Initialize all jobs as SCHEDULED if they don't already exist
            for job_id in job_ids:
                if job_id not in self._jobs:
                    self._jobs[job_id] = JobState(status=ProcessingStatus.SCHEDULED)

            self._save_state()

    def start_job(self, job_id: str) -> None:
        """Marks the target job as running and captures the SLURM-assigned job's ID from the environment, if called
        under the SLURM job manager.

        Args:
            job_id: The unique identifier of the job mark as started.

        Raises:
            TimeoutError: If the .LOCK file for the tracker .YAML file cannot be acquired within the timeout period.
            ValueError: If the specified job ID is not found in the managed tracker file.
        """
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()

            # Verifies that the tracker is configured to track the specified job
            if job_id not in self._jobs:
                message = (
                    f"The ProcessingTracker instance is not configured to track the state of the job with ID "
                    f"'{job_id}'. The instance is currently configured to track jobs with IDs: "
                    f"{', '.join(self._jobs.keys())}."
                )
                console.error(message=message, error=ValueError)
                # Fallback to appease mypy, should not be reachable
                raise ValueError(message)  # pragma: no cover

            # Updates job status and captures the SLURM-assigned job ID
            job_info = self._jobs[job_id]
            job_info.status = ProcessingStatus.RUNNING
            job_info.slurm_job_id = self._get_slurm_job_id()

            self._save_state()

    def complete_job(self, job_id: str) -> None:
        """Marks a target job as successfully completed.

        Args:
            job_id: The unique identifier of the job to mark as complete.

        Raises:
            TimeoutError: If the .LOCK file for the tracker .YAML file cannot be acquired within the timeout period.
            ValueError: If the specified job ID is not found in the managed tracker file.
        """
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()

            # Verifies that the tracker is configured to track the specified job
            if job_id not in self._jobs:
                message = (
                    f"The ProcessingTracker instance is not configured to track the state of the job with ID "
                    f"'{job_id}'. The instance is currently configured to track jobs with IDs: "
                    f"{', '.join(self._jobs.keys())}."
                )
                console.error(message=message, error=ValueError)
                # Fallback to appease mypy, should not be reachable
                raise ValueError(message)  # pragma: no cover

            # Updates the job's status.
            job_info = self._jobs[job_id]
            job_info.status = ProcessingStatus.SUCCEEDED

            self._save_state()

    def fail_job(self, job_id: str) -> None:
        """Marks the target job as failed.

        Args:
            job_id: The unique identifier of the job to mark as failed.

        Raises:
            TimeoutError: If the .LOCK file for the tracker .YAML file cannot be acquired within the timeout period.
            ValueError: If the specified job ID is not found in the managed tracker file.
        """
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file
            self._load_state()

            # Verifies that the tracker is configured to track the specified job
            if job_id not in self._jobs:
                message = (
                    f"The ProcessingTracker instance is not configured to track the state of the job with ID "
                    f"'{job_id}'. The instance is currently configured to track jobs with IDs: "
                    f"{', '.join(self._jobs.keys())}."
                )
                console.error(message=message, error=ValueError)
                # Fallback to appease mypy, should not be reachable
                raise ValueError(message)  # pragma: no cover

            # Updates the job's status.
            job_info = self._jobs[job_id]
            job_info.status = ProcessingStatus.FAILED

            self._save_state()

    def get_job_status(self, job_id: str) -> ProcessingStatus:
        """Queries the current runtime status of the target job.

        Args:
            job_id: The unique identifier of the job for which to query the runtime status.

        Returns:
            The current runtime status of the job.

        Raises:
            TimeoutError: If the .LOCK file for the tracker .YAML file cannot be acquired within the timeout period.
            ValueError: If the specified job ID is not found in the managed tracker file.
        """
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            self._load_state()

            # Verifies that the tracker is configured to track the specified job
            if job_id not in self._jobs:
                message = (
                    f"The ProcessingTracker instance is not configured to track the state of the job with ID "
                    f"'{job_id}'. The instance is currently configured to track jobs with IDs: "
                    f"{', '.join(self._jobs.keys())}."
                )
                console.error(message=message, error=ValueError)
                # Fallback to appease mypy, should not be reachable
                raise ValueError(message)  # pragma: no cover

            return self._jobs[job_id].status

    def reset(self) -> None:
        """Resets the tracker file to the default state."""
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            # Loads tracker state from the .yaml file.
            self._load_state()

            # Resets the tracker file to the default state.
            self._jobs.clear()
            self._save_state()

    @property
    def complete(self) -> bool:
        """Returns True if the tracked processing pipeline has been completed successfully.

        Notes:
            The pipeline is considered complete if all jobs have been marked as succeeded.
        """
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            self._load_state()
            if not self._jobs:
                return False
            return all(job.status == ProcessingStatus.SUCCEEDED for job in self._jobs.values())

    @property
    def encountered_error(self) -> bool:
        """Returns True if the tracked processing pipeline has been terminated due to a runtime error.

        Note:
            The pipeline is considered to have encountered an error if any job has been marked as failed.
        """
        lock = FileLock(self.lock_path)
        with lock.acquire(timeout=10.0):
            self._load_state()
            return any(job.status == ProcessingStatus.FAILED for job in self._jobs.values())
