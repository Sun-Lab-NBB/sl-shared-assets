from enum import IntEnum, StrEnum
from pathlib import Path
from dataclasses import field, dataclass

from ataraxis_data_structures import YamlConfig

from .job import Job as Job
from .server import Server as Server

class TrackerFileNames(StrEnum):
    """Stores the names of the processing tacker .yaml files used by the Sun lab data preprocessing, processing, and
    dataset formation pipelines to track the pipeline's progress.

     Notes:
        The elements in this enumeration match the elements in the ProcessingPipelines enumeration, since each valid
        ProcessingPipeline instance has an associated ProcessingTracker file instance.
    """

    MANIFEST = "manifest_generation_tracker.yaml"
    CHECKSUM = "checksum_resolution_tracker.yaml"
    PREPARATION = "processing_preparation_tracker.yaml"
    BEHAVIOR = "behavior_processing_tracker.yaml"
    SUITE2P = "suite2p_processing_tracker.yaml"
    VIDEO = "video_processing_tracker.yaml"
    FORGING = "dataset_forging_tracker.yaml"
    MULTIDAY = "multiday_processing_tracker.yaml"
    ARCHIVING = "data_archiving_tracker.yaml"

class ProcessingPipelines(StrEnum):
    """Stores the names of the data processing pipelines currently used in the lab.

    Notes:
        The elements in this enumeration match the elements in the TrackerFileNames enumeration, since each valid
        ProcessingPipeline instance has an associated ProcessingTracker file instance.

        The order of pipelines in this enumeration loosely follows the sequence in which they are executed during the
        Sun lab data workflow.
    """

    MANIFEST = "manifest generation"
    CHECKSUM = "checksum resolution"
    PREPARATION = "processing preparation"
    BEHAVIOR = "behavior processing"
    SUITE2P = "single-day suite2p processing"
    VIDEO = "video processing"
    MULTIDAY = "multi-day suite2p processing"
    FORGING = "dataset forging"
    ARCHIVING = "data archiving"

class ProcessingStatus(IntEnum):
    """Maps integer-based processing pipeline status (state) codes to human-readable names.

    The codes from this enumeration are used by the ProcessingPipeline class to communicate the status of the managed
    pipelines to manager processes that oversee the execution of each pipeline.

    Notes:
        The status codes from this enumeration track the state of the pipeline as a whole, instead of tracking the
        state of each job that comprises the pipeline.
    """

    RUNNING = 0
    SUCCEEDED = 1
    FAILED = 2
    ABORTED = 3

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
    _complete: bool = ...
    _encountered_error: bool = ...
    _running: bool = ...
    _manager_id: int = ...
    _lock_path: str = field(init=False)
    _job_count: int = ...
    _completed_jobs: int = ...
    def __post_init__(self) -> None: ...
    def _load_state(self) -> None:
        """Reads the current processing state from the wrapped .YAML file."""
    def _save_state(self) -> None:
        """Saves the current processing state stored inside instance attributes to the specified .YAML file."""
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
    def abort(self) -> None:
        """Resets the pipeline tracker file to the default state.

        This method can be used to reset the pipeline tracker file, regardless of the current pipeline state. Unlike
        other instance methods, this method can be called from any manager process, even if the pipeline is already
        locked by another process. This method is only intended to be used in the case of emergency to unlock a
        deadlocked pipeline.
        """
    @property
    def is_complete(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing pipeline has been completed
        successfully and that the pipeline is not currently ongoing."""
    @property
    def encountered_error(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing pipeline has aborted due
        to encountering an error."""
    @property
    def is_running(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing pipeline is currently
        ongoing."""

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
    server: Server
    manager_id: int
    jobs: dict[int, tuple[tuple[Job, Path], ...]]
    remote_tracker_path: Path
    local_tracker_path: Path
    session: str
    animal: str
    project: str
    keep_job_logs: bool = ...
    pipeline_status: ProcessingStatus | int = ...
    _pipeline_stage: int = ...
    def __post_init__(self) -> None:
        """Carries out the necessary filesystem setup tasks to support pipeline execution."""
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
    def _submit_jobs(self) -> None:
        """This worker method submits the processing jobs for the currently active processing stage to the remote
        server.

        It is used internally by the runtime_cycle() method to iteratively execute all stages of the managed processing
        pipeline on the remote server.
        """
    @property
    def is_running(self) -> bool:
        """Returns True if the pipeline is currently running, False otherwise."""
    @property
    def status(self) -> ProcessingStatus:
        """Returns the current status of the pipeline packaged into a ProcessingStatus instance."""

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
