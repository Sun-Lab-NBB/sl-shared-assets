from pathlib import Path

from ataraxis_base_utilities import console
from ataraxis_time.time_helpers import get_timestamp

from ..server import Job, Server, ProcessingStatus, TrackerFileNames, ProcessingPipeline, ProcessingPipelines


def _get_remote_job_work_directory(server: Server, job_name: str) -> Path:
    """Generates the working directory for the input job intended to be executed on the compute server managed by the
    input Server class.

    This worker function generates the current UTC timestamp, clips it down to minutes, and concatenates it to the
    job_name to construct the working directory name. It then resolves the path to that directory relative to the user
    working root on the remote server, creates the directory on the server, and returns the resolved path.
    """

    # Resolves working directory name using timestamp (accurate to minutes) and the job_name.
    timestamp = "-".join(get_timestamp().split("-")[:5])  # type: ignore
    working_directory = Path(server.user_working_root).joinpath("job_logs", f"{job_name}_{timestamp}")

    # Creates the working directory on the remote server.
    server.create_directory(remote_path=working_directory, parents=True)

    return working_directory


def compose_processing_pipeline(
    pipeline: ProcessingPipelines,
    project: str,
    animal: str,
    session: str,
    server: Server,
    manager_id: int,
    local_working_directory: Path,
    keep_job_logs: bool = False,
    recalculate_checksum: bool = False,
) -> ProcessingPipeline:
    """Generates and returns the ProcessingPipeline instance used to execute the requested pipeline for the target
    session on the specified remote compute server.

    This function composes the processing pipeline execution graph and packages it into the ProcessingPipeline instance.
    As part of this process, it resolves the necessary local and remote filesystem paths and generates the Job
    instances for all jobs making up the pipeline.

    Notes:
        This function does not start executing the pipeline. Instead, the pipeline starts executing the first time
        the manager process calls its runtime_cycle() method.

    Args:
        pipeline: The ProcessingPipelines enumeration value specifying the target pipeline to compose.
        project: The name of the project for which to compose the processing pipeline.
        animal: The ID of the animal for which to compose the processing pipeline.
        session: The ID of the session to process with the processing pipeline.
        server: The Server class instance that manages access to the remote server that executes the pipeline and
            stores the target session data.
        manager_id: The unique identifier of the process that calls this function to compose the pipeline.
        local_working_directory: The path to the directory on the local machine used to store temporary pipeline data.
        keep_job_logs: Determines whether to keep the logs for completed pipeline jobs on the server or (default)
            remove them after runtime. If any job of the pipeline fails, the logs for all jobs are kept regardless of
            this argument.
        recalculate_checksum: Only for integrity verification pipelines. Determines whether to verify the checksum
            integrity (if false) or whether to recalculate and overwrite the checksum stored in the ax_checksum.txt file
            (if true).

    Returns:
        The ProcessingPipeline instance configured to execute and manage the target processing pipeline on the remote
        server.
    """
    # Parses the paths to the shared Sun lab directories used to store raw session data on the remote server.
    remote_session_path = Path(server.processed_data_root).joinpath(project, animal, session)

    # Precreates the dictionary for storing job instances and their working directories
    jobs: dict[int, tuple[tuple[Job, Path], ...]] = {}
    stage = 1  # This is used to iteratively fill processing stage data for multi-stage pipelines.
    # This is used to store the Tracker file name for the constructed pipeline once it is resolved below
    tracker: TrackerFileNames

    # Integrity verification pipeline
    if pipeline == ProcessingPipelines.INTEGRITY:
        job_name = f"{session}_integrity_verification"
        working_directory = _get_remote_job_work_directory(server=server, job_name=job_name)
        job = Job(
            job_name=job_name,
            output_log=working_directory.joinpath(f"output.txt"),
            error_log=working_directory.joinpath(f"errors.txt"),
            working_directory=working_directory,
            conda_environment="manage",
            cpus_to_use=10,
            ram_gb=10,
            time_limit=30,
        )
        if recalculate_checksum:
            job.add_command(
                f"sl-resolve-checksum -sp {remote_session_path} -pdr {server.processed_data_root} -id {manager_id} -r"
            )
        else:
            job.add_command(
                f"sl-resolve-checksum -sp {remote_session_path} -pdr {server.processed_data_root} -id {manager_id}"
            )
        jobs[stage] = ((job, working_directory),)
        tracker = TrackerFileNames.INTEGRITY

    # Processing preparation pipeline
    elif pipeline == ProcessingPipelines.PREPARATION:
        job_name = f"{session}_processing_preparation"
        working_directory = _get_remote_job_work_directory(server=server, job_name=job_name)
        job = Job(
            job_name=job_name,
            output_log=working_directory.joinpath(f"output.txt"),
            error_log=working_directory.joinpath(f"errors.txt"),
            working_directory=working_directory,
            conda_environment="manage",
            cpus_to_use=20,
            ram_gb=10,
            time_limit=30,
        )
        job.add_command(
            f"sl-prepare-session -sp {remote_session_path} -pdr {server.processed_data_root} -id {manager_id}"
        )
        jobs[stage] = ((job, working_directory),)
        tracker = TrackerFileNames.PREPARATION

    # Archiving pipeline
    elif pipeline == ProcessingPipelines.ARCHIVE:
        job_name = f"{session}_archiving"
        working_directory = _get_remote_job_work_directory(server=server, job_name=job_name)
        job = Job(
            job_name=job_name,
            output_log=working_directory.joinpath(f"output.txt"),
            error_log=working_directory.joinpath(f"errors.txt"),
            working_directory=working_directory,
            conda_environment="manage",
            cpus_to_use=20,
            ram_gb=10,
            time_limit=30,
        )
        job.add_command(
            f"sl-archive-session -sp {remote_session_path} -pdr {server.processed_data_root} -id {manager_id}"
        )
        jobs[stage] = ((job, working_directory),)
        tracker = TrackerFileNames.ARCHIVE

    # Behavior processing pipeline
    elif pipeline == ProcessingPipelines.BEHAVIOR:
        job_name = f"{session}_behavior_processing"
        working_directory = _get_remote_job_work_directory(server=server, job_name=job_name)
        job = Job(
            job_name=job_name,
            output_log=working_directory.joinpath(f"output.txt"),
            error_log=working_directory.joinpath(f"errors.txt"),
            working_directory=working_directory,
            conda_environment="behavior",
            cpus_to_use=7,
            ram_gb=5,
            time_limit=180,
        )
        job.add_command(f"sl-process-behavior -sp {remote_session_path!s} -um")
        jobs[stage] = ((job, working_directory),)
        tracker = TrackerFileNames.BEHAVIOR

    else:
        message = (
            f"Unsupported pipeline {pipeline} encountered when attempting to construct a ProcessingPipeline instance. "
            f"Currently, only the following pipelines listed in the ProcessingPipelines enumeration are supported: "
            f"{', '.join(tuple(ProcessingPipelines))}."
        )
        console.error(message=message, error=ValueError)
        raise ValueError(message)  # Fallback to appease mypy, should not be reachable

    # Resolves paths to pipeline tracker files.
    remote_tracker_path = Path(server.raw_data_root).joinpath(project, animal, session, "raw_data", tracker)
    local_tracker_path = local_working_directory.joinpath(tracker)

    # Packages job data into a ProcessingPipeline object and returns it to the caller.
    processing_pipeline = ProcessingPipeline(
        jobs=jobs,
        server=server,
        manager_id=manager_id,
        pipeline_type=pipeline,
        remote_tracker_path=remote_tracker_path,
        local_tracker_path=local_tracker_path,
        session=session,
        animal=animal,
        project=project,
        keep_job_logs=keep_job_logs,
        pipeline_status=ProcessingStatus.RUNNING,
    )
    return processing_pipeline


def compose_suite2p_pipeline(
    project: str,
    animal: str,
    session: str,
    server: Server,
    manager_id: int,
    local_working_directory: Path,
    configuration_file: str = "GCaMP6f_CA1_SD.yaml",
    plane_count: int = 3,
    keep_job_logs: bool = False,
) -> ProcessingPipeline | None:
    """Generates and returns the ProcessingPipeline instance used to execute the single-day suite2p processing pipeline
    for the target session.

    This function composes the processing pipeline and packages it into the ProcessingPipeline. This pipeline extracts
    the brain activity data from the mesoscope-acquired .tiff stacks. The extracted data is stored as a collection of
    NumPy .npy files and is later used during the multi-day suite2p pipeline.

    Notes:
        This function does not start executing the pipeline. Instead, the pipeline starts executing the first time
        the manager process calls its runtime_cycle() method.

        If the function determines that the target session cannot be processed, it instead returns None and notifies
        the user why the session was excluded from processing via the terminal.

    Args:
        project: The name of the project for which to execute the single-day suite2p processing pipeline.
        session: The name of the session to process with the single-day suite2p processing pipeline.
        server: The Server class instance that manages access to the remote server that executes the pipeline and
            stores the target session data.
        manager_id: The unique identifier of the process that calls this function to construct the pipeline.
        configuration_file: The name of the configuration file stored on the remote compute server that contains the
            processing parameters to use for this runtime. The file with this name (and a .yaml) extensions must be
            present in the shared suite2p configuration folder on the remote compute server for the pipeline to be able
            to run the processing.
        plane_count: The number of planes in the input dataset. For mesoscope images, this is the number of ROIs
            (stripes) x the number of z-planes. This determines the number of plane processing jobs to execute during
            runtime.
        reprocess: Determines whether to reprocess sessions that have already been processed.
        keep_job_logs: Determines whether to keep completed job logs on the server or (default) remove them after
            runtime. If any job of the pipeline fails, the logs for all jobs are kept regardless of this argument's
            value.

    Returns:
        The ProcessingPipeline instance configured to execute and manage the single-day suite2p processing pipeline
        on the server if the session can be processed with this pipeline. None, if the session is excluded from
        processing for any reason.
    """

    # Ensures that the target suite2p configuration file exists on the remote server
    configuration_path = server.raw_data_root.joinpath(project, "suite2p_configuration", configuration_file)
    if not server.exists(configuration_path):
        message = (
            f"Unable to process 2-photon brain activity data for session '{session}' performed by animal '{animal}' "
            f"for '{project}' project. The suite2p configuration file '{configuration_file}' does not exist on the "
            f"remote server."
        )
        console.error(message=message, error=ValueError)

    # Otherwise, resolves the single-day suite2p processing graph. Note; the suite2p processing relies on multiple jobs
    # submitted in 3 distinct processing stages. All Job objects are resolved before running the pipeline on the
    # remote server (below), so that the pipeline functions as a monolithic processing graph.

    # Precreates the iterables to store stage jobs
    stage_1 = []
    stage_2 = []
    stage_3 = []

    # Resolves the directory where to store the data for all jobs executed as part of the pipeline and the current
    # timestamp (to use in job working directory names).
    timestamp = get_timestamp()
    working_root = Path(server.user_working_root).joinpath("job_logs")

    # Parses the paths to the shared Sun lab directories used to store raw and processed session data on the remote
    # server.
    remote_session_path = Path(server.raw_data_root).joinpath(project, animal, session)
    processed_data_root = Path(server.processed_data_root)

    # Stage 1: Binarization
    job_name = f"{session}_s2p_sd_binarization"
    working_directory = working_root.joinpath(f"{job_name}_{timestamp}")
    server.create_directory(remote_path=working_directory)
    job = Job(
        job_name=job_name,
        output_log=working_directory.joinpath(f"output.txt"),
        error_log=working_directory.joinpath(f"errors.txt"),
        working_directory=working_directory,
        conda_environment="suite2p",
        cpus_to_use=1,
        ram_gb=5,
        time_limit=240,
    )
    job.add_command(
        f"sl-process-suite2p -i {configuration_path!s} -sp {remote_session_path!s} "
        f"-pdr {processed_data_root!s} -b -w -1 -um"
    )
    stage_1.append((job, working_directory))

    # Stage 2: Plane processing
    for plane in range(plane_count):
        job_name = f"{session}_s2p_sd_plane_{plane}"
        working_directory = working_root.joinpath(f"{job_name}_{timestamp}")
        server.create_directory(remote_path=working_directory)
        job = Job(
            job_name=job_name,
            output_log=working_directory.joinpath(f"output.txt"),
            error_log=working_directory.joinpath(f"errors.txt"),
            working_directory=working_directory,
            conda_environment="suite2p",
            cpus_to_use=42,
            ram_gb=80,
            time_limit=300,
        )
        job.add_command(
            f"sl-process-suite2p -i {configuration_path!s} -sp {remote_session_path!s} "
            f"-pdr {processed_data_root!s} -p -t {plane} -w -1 -um"
        )
        stage_2.append((job, working_directory))

    # Stage 3: Combination
    job_name = f"{session}_s2p_sd_combination"
    working_directory = working_root.joinpath(f"{job_name}_{timestamp}")
    server.create_directory(remote_path=working_directory)
    job = Job(
        job_name=job_name,
        output_log=working_directory.joinpath(f"output.txt"),
        error_log=working_directory.joinpath(f"errors.txt"),
        working_directory=working_directory,
        conda_environment="suite2p",
        cpus_to_use=1,
        ram_gb=4,
        time_limit=90,
    )
    job.add_command(
        f"sl-process-suite2p -i {configuration_path!s} -sp {remote_session_path!s} "
        f"-pdr {processed_data_root!s} -c -w -1 -um"
    )
    stage_3.append((job, working_directory))

    # Resolves the paths to the local and remote job tracker files.
    remote_tracker_path = Path(server.processed_data_root).joinpath(
        project, animal, session, "processed_data", TrackerFileNames.SUITE2P
    )
    local_tracker_path = local_working_directory.joinpath(
        project, f"{session}_suite2p_processing", TrackerFileNames.SUITE2P
    )

    # Packages job data into a ProcessingPipeline object and returns it to the caller. The end-result is a 'one-stage'
    # and 'one-job' pipeline.
    pipeline = ProcessingPipeline(
        jobs={1: tuple(stage_1), 2: tuple(stage_2), 3: tuple(stage_3)},
        server=server,
        manager_id=manager_id,
        pipeline_type=ProcessingPipelines.SUITE2P,
        remote_tracker_path=remote_tracker_path,
        local_tracker_path=local_tracker_path,
        session=session,
        animal=animal,
        project=project,
        keep_job_logs=keep_job_logs,
        pipeline_status=ProcessingStatus.RUNNING,
    )

    return pipeline


def compose_dataset_pipeline(
    project: str,
    animal: str,
    session: str,
    server: Server,
    create: bool = False,
) -> Job | None:
    """Generates and returns the ProcessingPipeline instance used to execute the single-day suite2p processing pipeline
    for the target session.

    This function composes the processing pipeline and packages it into the ProcessingPipeline. This pipeline extracts
    the brain activity data from the mesoscope-acquired .tiff stacks. The extracted data is stored as a collection of
    NumPy .npy files and is later used during the multi-day suite2p pipeline.

    Notes:
        This function does not start executing the pipeline. Instead, the pipeline starts executing the first time
        the manager process calls its runtime_cycle() method.

        If the function determines that the target session cannot be processed, it instead returns None and notifies
        the user why the session was excluded from processing via the terminal.

    Args:
        project: The name of the project for which to execute the single-day suite2p processing pipeline.
        session: The name of the session to process with the single-day suite2p processing pipeline.
        server: The Server class instance that manages access to the remote server that executes the pipeline and
            stores the target session data.
        manager_id: The unique identifier of the process that calls this function to construct the pipeline.
        keep_job_logs: Determines whether to keep completed job logs on the server or (default) remove them after
            runtime. If any job of the pipeline fails, the logs for all jobs are kept regardless of this argument's
            value.

    Returns:
        The ProcessingPipeline instance configured to execute and manage the single-day suite2p processing pipeline
        on the server if the session can be processed with this pipeline. None, if the session is excluded from
        processing for any reason.
    """

    # This section works similar to other pipeline sections in this module. However, instead of constructing a
    # pipeline object, it constructs and submits a processing job to the server. Primarily, this is because the dataset
    # marker pipeline does not rely on processing tracker files like other pipeline

    # Resolves the working directory for the job, using a static job name and the current timestamp in UTC.
    timestamp = get_timestamp()
    job_name = f"{session}_dataset_marker"
    working_directory = Path(server.user_working_root).joinpath("job_logs", f"{job_name}_{timestamp}")

    # Ensures that the working directory exists on the remote server
    server.create_directory(remote_path=working_directory)

    # Parses the paths to the shared Sun lab directories used to store raw and processed session data on the remote
    # server.
    remote_session_path = Path(server.raw_data_root).joinpath(project, animal, session)
    processed_data_root = Path(server.processed_data_root)

    # Generates the remote job header and configures the job to resolve the dataset marker for the target session.
    job = Job(
        job_name=job_name,
        output_log=working_directory.joinpath(f"output.txt"),
        error_log=working_directory.joinpath(f"errors.txt"),
        working_directory=working_directory,
        conda_environment="manage",
        cpus_to_use=4,
        ram_gb=20,
        time_limit=90,
    )
    if create:
        job.add_command(f"sl-dataset-marker -sp {remote_session_path!s} -pdr {processed_data_root!s} -um")
    else:
        job.add_command(f"sl-dataset-marker -sp {remote_session_path!s} -pdr {processed_data_root!s} -um -r")

    return job
