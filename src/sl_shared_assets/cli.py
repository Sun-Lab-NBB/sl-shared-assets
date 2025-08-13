"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from .tools import (
    reset_trackers,
    archive_session,
    prepare_session,
    resolve_checksum,
    resolve_p53_marker,
    generate_project_manifest,
)
from .server import Server, JupyterJob, TrackerFileNames, generate_server_credentials


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session directory for which to verify or create the data checksum.",
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all projects is stored on the machine that runs "
        "this command, if it is different from raw session's data location."
    ),
)
@click.option(
    "-id",
    "--manager_id",
    type=int,
    required=True,
    default=0,
    show_default=True,
    help="The unique identifier for the process that manages this runtime.",
)
@click.option(
    "-r",
    "--recalculate_checksum",
    is_flag=True,
    help=(
        "Determines whether to recalculate and overwrite the checksum stored inside the ax_checksum.txt file of the "
        "processed session. When the command is called with this flag, it effectively re-checksums the data instead of "
        "verifying it."
    ),
)
def resolve_session_checksum(
    session_path: Path,
    manager_id: int,
    processed_data_root: Path | None,
    recalculate_checksum: bool,
) -> None:
    """Checks the integrity of the target session's 'raw_data' directory or (re)generates the directory checksum.

    This command assumes that the data has been checksummed during acquisition and contains an ax_checksum.txt file
    that stores the data checksum. It only works with the 'raw_data' session directory and ignores the 'processed_data'
    and any other directory. If the command is called with the --recalculate_checksum flag, it instead recalculates and
    overwrites the checksum stored in the ax_checksum.txt file.
    """

    resolve_checksum(
        session_path=session_path,
        manager_id=manager_id,
        processed_data_root=processed_data_root,
        regenerate_checksum=recalculate_checksum,
    )


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session directory for which to reset the processing trackers.",
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all projects is stored on the machine that runs "
        "this command, if it is different from raw session's data location."
    ),
)
@click.option(
    "-t",
    "--tracker",
    type=str,
    required=False,
    help=(
        "The name fo the processing tracker file to reset. Note, the input name must match one of the options "
        "available from the TrackerFileNames enumeration. If this argument is not provided, the command resets all "
        "available trackers."
    ),
)
def reset_session_trackers(
    session_path: Path,
    tracker: str | None | tuple[TrackerFileNames, ...],
    processed_data_root: Path | None,
) -> None:
    """Resets the requested processing tracker files for the target session to the initial state.

    This command is primarily intended to be used on remote compute servers to recover unexpectedly aborted pipelines.
    As part of its runtime, it loops over each requested tracker file and uses the ProcessingTracker.abort() method to
    reset the trackers to pre-pipeline-runtime states.
    """

    # Resolves the tracker(s) to target and casts to TrackerFileNames enumeration type.
    if isinstance(tracker, str):
        tracker = (TrackerFileNames(tracker),)

    # Resets the target trackers
    reset_trackers(
        session_path=session_path,
        trackers=tracker,
        processed_data_root=processed_data_root,
    )


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session directory whose raw data needs to be verified for potential corruption.",
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all projects is stored on the machine that runs "
        "this command, if it is different from raw session's data location."
    ),
)
@click.option(
    "-id",
    "--manager_id",
    type=int,
    required=True,
    default=0,
    show_default=True,
    help="The unique identifier for the process that manages this runtime.",
)
def prepare_session_for_processing(
    session_path: Path,
    manager_id: int,
    processed_data_root: Path | None,
) -> None:
    """Prepares the target session data for processing by ensuring that both raw and processed data is stored on the
    processed data volume (fast drive) of the filesystem.

    This command is primarily intended to run on remote compute servers that use slow HDD volumes to maximize data
    integrity and fast NVME volumes to maximize data processing speed. For such systems, moving data to fast volumes
    before processing results in a measurable processing speed increase.
    """
    prepare_session(
        session_path=session_path,
        manager_id=manager_id,
        processed_data_root=processed_data_root,
    )


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session directory whose raw data needs to be verified for potential corruption.",
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all projects is stored on the machine that runs "
        "this command, if it is different from raw session's data location."
    ),
)
@click.option(
    "-id",
    "--manager_id",
    type=int,
    required=True,
    default=0,
    show_default=True,
    help="The unique identifier for the process that manages this runtime.",
)
def archive_session_for_storage(
    session_path: Path,
    manager_id: int,
    processed_data_root: Path | None,
) -> None:
    """Prepares the target session data for long-term storage by ensuring that both raw and processed data is stored
    only on the raw data (slow drive) volume.

    This command is primarily intended to run on remote compute servers that use slow HDD volumes to maximize data
    integrity and fast NVME volumes to maximize data processing speed. For such systems, all sessions that are no longer
    actively processed or analyzed should be moved to the slow drive volume for long-term storage.
    """
    archive_session(
        session_path=session_path,
        manager_id=manager_id,
        processed_data_root=processed_data_root,
    )


@click.command()
@click.option(
    "-pp",
    "--project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the project directory where raw session data is stored.",
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all projects is stored on the machine that runs "
        "this command. This argument is used when calling the CLI on the BioHPC server, which uses different data "
        "volumes for raw and processed data. Note, the input path must point to the root directory, as it will be "
        "automatically modified to include the project name. Note, if the system cannot properly resolve the path to "
        "the processed data, the generated manifest will indicate that no data processing has been performed for the "
        "project."
    ),
)
def generate_project_manifest_file(project_path: Path, processed_data_root: Path | None) -> None:
    """Generates the manifest .feather file that provides information about the data-processing state of all available
    project sessions.

    The manifest file is typically used when batch-processing session data on the remote compute server. It contains the
    comprehensive snapshot of the available project's data in a table-compatible format that can also be transferred
    between machines (as it is cached in a file).
    """
    generate_project_manifest(
        raw_project_directory=Path(project_path),
        processed_data_root=processed_data_root,
    )
    # noinspection PyTypeChecker
    console.echo(message=f"Project {Path(project_path).stem} data manifest file: generated.", level=LogLevel.SUCCESS)


@click.command()
@click.option(
    "-od",
    "--output_directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated server credentials file.",
)
@click.option(
    "-h",
    "--host",
    type=str,
    required=True,
    show_default=True,
    default="cbsuwsun.biohpc.cornell.edu",
    help="The host name or IP address of the server to connect to.",
)
@click.option(
    "-u",
    "--username",
    type=str,
    required=True,
    help="The username to use for server authentication.",
)
@click.option(
    "-p",
    "--password",
    type=str,
    required=True,
    help="The password to use for server authentication.",
)
@click.option(
    "-sr",
    "--storage_root",
    type=str,
    required=True,
    show_default=True,
    default="/local/storage",
    help=(
        "The absolute path to to the root storage (slow) server directory. Typically, this is the path to the "
        "top-level (root) directory of the HDD RAID volume."
    ),
)
@click.option(
    "-wr",
    "--working_root",
    type=str,
    required=True,
    show_default=True,
    default="/local/workdir",
    help=(
        "The absolute path to the root working (fast) server directory. Typically, this is the path to the top-level "
        "(root) directory of the NVME RAID volume. If the server uses the same volume for both storage and working "
        "directories, enter the same path under both 'storage_root' and 'working_root'."
    ),
)
@click.option(
    "-sdn",
    "--shared_directory_name",
    type=str,
    required=True,
    show_default=True,
    default="sun_data",
    help=(
        "The name of the shared directory used to store all Sun lab project data on the storage and working server "
        "volumes."
    ),
)
def generate_server_credentials_file(
    output_directory: Path,
    host: str,
    username: str,
    password: str,
    storage_root: str,
    working_root: str,
    shared_directory_name: str,
) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This command is used to set up access to compute servers and clusters on new machines (PCs). The data stored inside
    the server_credentials.yaml file generated by this command is used by the Server and Job classes used in many Sun
    lab data processing libraries.
    """

    # If necessary, generates the output directory hierarchy before creating the credentials' file.
    ensure_directory_exists(output_directory)

    # Generates the credentials' file
    generate_server_credentials(
        output_directory=Path(output_directory),
        username=username,
        password=password,
        host=host,
        storage_root=storage_root,
        working_root=working_root,
        shared_directory_name=shared_directory_name,
    )
    message = (
        f"Server access credentials file: generated. If necessary, remember to edit the data acquisition system "
        f"configuration file to include the path to the credentials file generated via this CLI."
    )
    # noinspection PyTypeChecker
    console.echo(message=message, level=LogLevel.SUCCESS)
    message = f"File location: {output_directory}"
    # noinspection PyTypeChecker
    console.echo(message=message, level=LogLevel.SUCCESS)


@click.command()
@click.option(
    "-cp",
    "--credentials_path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help=(
        "The absolute path to the server_credentials.yaml file that stores access credentials for the target Sun lab "
        "server. If necessary, use the 'sl-create-server-credentials' command to generate the file."
    ),
)
@click.option(
    "-n",
    "--name",
    type=str,
    required=True,
    show_default=True,
    default="jupyter_server",
    help=(
        "The descriptive name to be given to the remote Jupyter server job. Primarily, this is used to identify the "
        "job inside the log files."
    ),
)
@click.option(
    "-e",
    "--environment",
    type=str,
    required=True,
    help=(
        "The name of the conda environment to use for running the Jupyter server. At a minimum, the target environment "
        "must contain the 'jupyterlab' and the 'notebook' Python packages. Note, the user whose credentials are used "
        "to connect to the server must have a configured conda / mamba shell that exposes the target environment for "
        "the job to run as expected."
    ),
)
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=True, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the server directory to use as the root directory for the jupyter session. If not "
        "provided, this is automatically resolved to user's working directory. Note, during runtime, Jupyter will only "
        "have access to files stored in or under that root directory."
    ),
)
@click.option(
    "-c",
    "--cores",
    type=int,
    required=True,
    show_default=True,
    default=2,
    help=(
        "The number of CPU cores to allocate to the Jupyter server. Note, during the interactive Jupyter runtime, it "
        "is be impossible to use more than this number of CPU cores."
    ),
)
@click.option(
    "-m",
    "--memory",
    type=int,
    required=True,
    show_default=True,
    default=32,
    help=(
        "The RAM, in Gigabytes, to allocate to the Jupyter server. Note, during the interactive Jupyter runtime, it "
        "is be impossible to use more than this amount of RAM."
    ),
)
@click.option(
    "-t",
    "--time",
    type=int,
    required=True,
    show_default=True,
    default=240,
    help=(
        "The maximum runtime duration for this Jupyter server instance, in minutes. If the server job is still running "
        "at the end of this time limit, the job will be forcibly terminated by SLURM. Note, to prevent hogging the "
        "server, make sure this parameter is always set to the smallest feasible period of time you intend to interact "
        "with the server."
    ),
)
@click.option(
    "-p",
    "--port",
    type=int,
    required=True,
    show_default=True,
    default=0,
    help=(
        "The port to use for the Jupyter server communication on the remote server. Valid port values are from 8888 "
        "to 9999. Most runtimes should leave this set to the default value (0), which will randomly select one of the "
        "valid ports. Using random selection minimizes the chances of colliding with other interactive jupyter "
        "sessions."
    ),
)
def start_jupyter_server(
    credentials_path: Path, name: str, environment: str, directory: Path, cores: int, memory: int, time: int, port: int
) -> None:
    """Starts an interactive Jupyter session on the remote Sun lab server.

    This command should be used to run Jupyter lab and notebooks sessions on the remote Sun lab server. Since all lab
    data is stored on the server, this allows running light interactive analysis sessions on the same node as the data,
    while leveraging considerable compute resources of the server.

    Calling this command initializes a SLURM session that runs the interactive Jupyter server. Since this server
    directly competes for resources with all other headless jobs running on the server, it is imperative that each
    jupyter runtime uses only the minimum amount of resources and run-time as necessary. Do not use this command to run
    heavy data processing pipelines! Instead, consult with library documentation and use the headless Job class.
    """
    # Initializes server connection
    server = Server(credentials_path)
    job: JupyterJob | None = None
    try:
        # If the caller did not provide an explicit notebook directory, defaults to the user's working directory
        if directory is None:
            directory = (server.user_working_root,)

        # Launches the specified Jupyter server
        job = server.launch_jupyter_server(
            job_name=name,
            conda_environment=environment,
            notebook_directory=directory,
            cpus_to_use=cores,
            ram_gb=memory,
            port=port,
            time_limit=time,
        )

        # Displays the server connection details to the user via terminal
        job.print_connection_info()

        # Blocks in-place until the user shuts down the server. This allows terminating the jupyter job early if the
        # user is done working with the server
        input("Enter anything to shut down the server: ")

    # Ensures that the server created as part of this CLI is always terminated when the CLI terminates
    finally:
        # Terminates the server job
        if isinstance(job, JupyterJob) and not server.job_complete(job):
            server.abort_job(job)

        # Closes the server connection if it is still open
        server.close()


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session directory for which to resolve the dataset integration readiness marker.",
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all projects is stored on the machine that runs "
        "this command. This argument is used when calling the CLI on the BioHPC server, which uses different data "
        "volumes for raw and processed data. Note, the input path must point to the root directory, as it will be "
        "automatically modified to include the project name."
    ),
)
@click.option(
    "-r",
    "--remove",
    is_flag=True,
    show_default=True,
    default=False,
    help="Determines whether the command should create or remove the dataset integration marker.",
)
def resolve_dataset_marker(
    session_path: Path,
    processed_data_root: Path | None,
    remove: bool,
) -> None:
    """Depending on configuration, either creates or removes the p53.bin marker from the target session.

    The p53.bin marker determines whether the session is ready for dataset integration. When the marker exists,
    processing pipelines are not allowed to work with the session data, ensuring that all processed data remains
    unchanged. If the marker does not exist, dataset integration pipelines are not allowed to work with the session
    data, enabling processing pipelines to safely modify the data at any time.
    """
    resolve_p53_marker(
        session_path=session_path,
        processed_data_root=processed_data_root,
        remove=remove,
    )
