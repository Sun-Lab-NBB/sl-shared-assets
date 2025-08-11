from enum import IntEnum, StrEnum
import shutil as sh
from pathlib import Path
from dataclasses import dataclass

from ataraxis_base_utilities import ensure_directory_exists

from .job import Job
from .server import Server
from ..data_classes.session_data import ProcessingTracker


class ProcessingStatus(IntEnum):
    """Maps integer-based processing pipeline status (state) codes to human-readable names.

    This enumeration is used to track and communicate the progress of Sun lab processing pipelines as they are executed
    by the remote compute server. Specifically, the codes from this enumeration are used by the ProcessingPipeline
    class to communicate the status of the managed pipelines to external processes.

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


class ProcessingPipelines(StrEnum):
    """Defines the set of processing pipelines currently supported in the Sun lab.

    All processing pipelines currently supported by the lab codebase are defined in this enumeration. Primarily,
    the elements from this enumeration are used in terminal messages and logging to identify the pipelines to the user.

    Notes:
        The elements in this enumeration match the elements in the ProcessingTracker enumeration, since each valid
        processing pipeline has an associated ProcessingTracker file.

        The order of pipelines in this enumeration loosely follows the sequence in which they are executed during the
        lifetime of the Sun lab data on the remote compute server.
    """

    INTEGRITY = "integrity verification"
    """Integrity verification pipeline. Primarily, it is used to verify that the raw data has been transferred to the 
    remote storage server from the main acquisition system PC intact."""
    PREPARATION = "processing preparation"
    """Data processing preparation pipeline. Since the compute server uses a two-volume design with a slow (HDD) storage
    volume and a fast (NVME) working volume, to optimize data processing performance, the data needs to be transferred 
    to the working volume before processing. This pipeline copies the raw data for the target session from the storage 
    volume to the working volume."""
    BEHAVIOR = "behavior processing"
    """Behavior processing pipeline. This pipeline is used to process .npz log files to extract animal behavior data 
    acquired during a single session (day). The processed logs also contain the timestamps use to synchronize behavior 
    to video and mesoscope frame data, and experiment configuration and task information."""
    SUITE2P = "single-day suite2p processing"
    """Single-day suite2p pipeline. This pipeline is used to extract the cell activity data from 2-photon imaging data 
    acquired during a single session (day)."""
    VIDEO = "video processing"
    """DeepLabCut (Video) processing pipeline. This pipeline is used to extract animal pose estimation data from the 
    behavior video frames acquired during a single session (day)."""
    DATASET = "dataset marker resolution"
    """Dataset marker resolution pipeline. This pipeline is used to resolve (create or remove) the dataset integration 
    markers for sessions whose data has been processed with all required processing pipelines. The dataset integration 
    marker both indicates whether the session is ready to be integrated into a dataset and ensures that sessions cannot 
    be targeted by data processing and dataset integration pipelines at the same time."""
    MULTIDAY = "multi-day suite2p processing"
    """Multi-day suite2p processing (cell tracking) pipeline. This pipeline is used to track cells processed with the 
    single-day suite2p pipelines across multiple days. It is executed for all sessions marked for integration into the 
    same dataset as the first step of dataset creation."""
    FORGING = "dataset forging"
    """Dataset creation (forging) pipeline. This pipeline typically runs after the multi-day pipeline. It extracts and 
    integrates the processed data from various sources such as brain activity, behavior, videos, etc., into a unified 
    dataset."""
    ARCHIVE = "data archiving"
    """Data archiving pipeline. To conserve the (limited) space on the fast working volume, once the data has been 
    processed and integrated into a stable dataset, the processed data folder is moved to the storage volume. The 
    now-redundant raw data folder stored on the fast working volume is deleted (as the storage volume already contains 
    a copy of raw_data)."""


@dataclass()
class ProcessingPipeline:
    """Encapsulates access to a processing pipeline running on the remote compute server.

    This class functions as an interface for all data processing pipelines running on Sun lab compute servers. It is
    pipeline-type-agnostic and works for all data processing pipelines supported by this library. After instantiation,
    the class automatically handles all interactions with the server necessary to run the remote processing pipeline and
    verify the runtime outcome via the runtime_cycle() method that has to be called cyclically until the pipeline is
    complete.

    Notes:
        Each pipeline may be executed in one or more stages, each stage using one or more parallel jobs. As such, each
        pipeline can be seen as an execution graph that sequentially submits batches of jobs to the remote server. The
        processing graph for each pipeline is fully resolved at the instantiation of this class instance, so each
        instance contains the necessary data to run the entire processing pipeline.

        The minimum self-contained unit of the processing pipeline is a single job. Since jobs can depend on the output
        of other jobs, they are organized into stages based on the dependency graph between jobs. Combined with cluster
        management software, such as SLURM, this class can efficiently execute processing pipelines on scalable compute
        clusters.
    """

    pipeline_type: ProcessingPipelines
    """Stores the name of the processing pipeline managed by this instance. Primarily, this is used to identify the 
    pipeline to the user in terminal messages and logs."""
    server: Server
    """The reference to the Server object that maintains bidirectional communication with the remote server running 
    the pipeline."""
    manager_id: int
    """The unique identifier for the manager process that constructs and manages the runtime of the tracked pipeline. 
    This is used to ensure that only a single pipeline instance can work with each session's data at the same time on 
    the remote server."""
    jobs: dict[int, tuple[tuple[Job, Path], ...]]
    """Stores the dictionary that maps the pipeline processing stage integer-codes to two-element tuples. Each tuple
    stores the Job objects and the paths to their remote working directories to be submitted to the server at each 
    stage."""
    remote_tracker_path: Path
    """The path to the pipeline's processing tracker .yaml file stored on the remote compute server."""
    local_tracker_path: Path
    """The path to the pipeline's processing tracker .yaml file on the local machine. The remote file is pulled to 
    this location when the instance verifies the outcome of each tracked pipeline's processing stage."""
    session: str
    """The ID of the session whose data is being processed by the tracked pipeline."""
    animal: str
    """The ID of the animal whose data is being processed by the tracked pipeline."""
    project: str
    """The name of the project whose data is being processed by the tracked pipeline."""
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
        ensure_directory_exists(self.local_tracker_path)  # Ensures that the local temporary directory exists

    def runtime_cycle(self) -> None:
        """Checks the current status of the tracked pipeline and, if necessary, submits additional batches of jobs to
        the remote server to progress the pipeline.

        This method is the main entry point for all interactions with the processing pipeline managed by this instance.
        It checks the current state of the pipeline, advances the pipeline's processing stage, and submits the necessary
        jobs to the remote server. The process managing the data processing runtime should call this method repeatedly
        (cyclically) to run the pipeline until the 'is_running' property of the instance returns True.

        Notes:
            While the 'is_running' property can be used to determine whether the pipeline is still running, to resolve
            the final status of the pipeline (success or failure), the manager process should access the
            'pipeline_status' instance attribute.
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
        # case, initialized the shutdown sequence:
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
            self.server.submit_job(job=job)

    @property
    def is_running(self) -> bool:
        """Returns True if the pipeline is currently running, False otherwise."""
        if self.pipeline_status == ProcessingStatus.RUNNING:
            return True
        return False

    @property
    def status(self) -> ProcessingStatus:
        return ProcessingStatus(self.pipeline_status)
