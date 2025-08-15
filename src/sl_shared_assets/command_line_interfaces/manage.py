"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from typing import Any
from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from ..tools import (
    ProjectManifest,
    archive_session,
    prepare_session,
    resolve_checksum,
    generate_project_manifest,
    fetch_remote_project_manifest,
    generate_remote_project_manifest,
)
from ..server import (
    Server,
    JupyterJob,
    generate_server_credentials,
)
from ..data_classes import get_working_directory, set_working_directory, get_credentials_file_path


@click.group("manage")
def manage() -> None:
    """This Command-Line Interface exposes subgroups of commands used to manage session and project data acquired in
    the Sun lab."""


# Session data management commands
@manage.group("session")
@click.option(
    "-sp",
    "--session-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the root session directory to process. This directory must contain the 'raw_data' "
    "subdirectory.",
)
@click.option(
    "-pdr",
    "--processed-data-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory that stores the processed data from all Sun lab projects, if it is "
        "different from the root directory included in the 'session-path' argument value."
    ),
)
@click.option(
    "-id",
    "--manager-id",
    type=int,
    required=True,
    default=0,
    show_default=True,
    help="The unique identifier of the process that manages this runtime.",
)
@click.option(
    "-r",
    "--reset-tracker",
    is_flag=True,
    required=False,
    help=(
        "Determines whether to forcibly reset the tracker file for the target processing pipeline before "
        "executing the processing. This flag should only be used in exceptional cases to recover from tracking file "
        "deadlocks due to improper runtime terminations."
    ),
)
@click.pass_context
def manage_session(
    ctx: Any, session_path: Path, processed_data_root: Path | None, manager_id: int, reset_tracker: bool
) -> None:
    """Exposes commands to manage Sun lab session data.

    Commands from this CLI are intended to run on the remote compute server to support data processing, dataset
    integration, and 'cold' storage of the session's data. Lab members typically do not need to use this command block
    directly and should instead use the bindings offered by the sl-forgery and sl-experiment libraries."""
    ctx.ensure_object(dict)
    ctx.obj["session_path"] = session_path
    ctx.obj["processed_data_root"] = processed_data_root
    ctx.obj["manager_id"] = manager_id
    ctx.obj["reset_tracker"] = reset_tracker


# noinspection PyUnresolvedReferences
@manage_session.command("checksum")
@click.option(
    "-rc",
    "--recalculate-checksum",
    is_flag=True,
    help=(
        "Determines whether to recalculate and overwrite the cached checksum value for the processed session. When "
        "the command is called with this flag, it effectively re-checksums the data instead of verifying its integrity."
    ),
)
@click.pass_context
def resolve_session_checksum(ctx: Any, recalculate_checksum: bool) -> None:
    """Resolves the integrity checksum for the 'raw_data' directory.

    This command can be used to either verify an existing 'raw_data' directory checksum or generate a new checksum.
    It only works with the 'raw_data' session directory, ignoring all other directories.
    """

    # Extracts shared parameters from context
    session_path = ctx.obj["session_path"]
    processed_data_root = ctx.obj["processed_data_root"]
    manager_id = ctx.obj["manager_id"]
    reset_tracker = ctx.obj["reset_tracker"]

    resolve_checksum(
        session_path=session_path,
        manager_id=manager_id,
        processed_data_root=processed_data_root,
        regenerate_checksum=recalculate_checksum,
        reset_tracker=reset_tracker,
    )


# noinspection PyUnresolvedReferences
@manage_session.command("prepare")
@click.pass_context
def prepare_session_for_processing(
    ctx: Any,
) -> None:
    """Prepares the target session data for processing.

    To do so, ensures that both raw and processed data is stored on the working (NVME) volume of the filesystem. This
    command is primarily intended to run on remote compute servers that use slow HDD volumes to maximize data
    integrity and fast NVME volumes to maximize data processing speed. For such systems, moving the data to the fast
    volume before processing results in a measurable processing speed increase.
    """
    # Extracts shared parameters from context
    session_path = ctx.obj["session_path"]
    processed_data_root = ctx.obj["processed_data_root"]
    manager_id = ctx.obj["manager_id"]
    reset_tracker = ctx.obj["reset_tracker"]

    prepare_session(
        session_path=session_path,
        manager_id=manager_id,
        processed_data_root=processed_data_root,
        reset_tracker=reset_tracker,
    )


# noinspection PyUnresolvedReferences
@manage_session.command("archive")
@click.pass_context
def archive_session_for_storage(
    ctx: Any,
) -> None:
    """Prepares the target session data for long-term storage.

    To do so, ensures that all session data (raw and processed) is stored only on the storage (HDD) volume. This command
    is primarily intended to run on remote compute servers that use slow HDD volumes to maximize data integrity and fast
    NVME volumes to maximize data processing speed. For such systems, all sessions that are no longer actively
    processed or analyzed should be moved to the slow drive volume for long-term storage.
    """
    # Extracts shared parameters from context
    session_path = ctx.obj["session_path"]
    processed_data_root = ctx.obj["processed_data_root"]
    manager_id = ctx.obj["manager_id"]
    reset_tracker = ctx.obj["reset_tracker"]

    archive_session(
        session_path=session_path,
        manager_id=manager_id,
        processed_data_root=processed_data_root,
        reset_tracker=reset_tracker,
    )


@click.command()
@click.option(
    "-pp",
    "--project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the project-specific directory where raw session data is stored.",
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all Sun lab projects is stored on the machine "
        "that runs this command, if different the root directory used to store raw project data."
    ),
)
def generate_project_manifest_file(project_path: Path, processed_data_root: Path | None) -> None:
    """Generates the manifest .feather file that communicates the current state of the target project's data.

    The manifest file is typically used when batch-processing session data on the remote compute server. It contains the
    comprehensive snapshot of the available project's data in a table-compatible format that can also be transferred
    between machines as a .feather file.
    """
    generate_project_manifest(
        raw_project_directory=Path(project_path),
        processed_data_root=processed_data_root,
        manager_id=1,
        reset_tracker=False,
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
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory to use for working with Sun lab data.",
)
def designate_working_directory(directory: Path) -> None:
    """Sets the input directory as the Sun lab working directory, creating any missing directory path components.

    After the directory is configured, all calls to this library use this directory to store the intermediate data
    required to perform the requested task. This system allows the library to behave consistently across different
    user machines and runtime contexts.
    """
    # Creates the directory if it does not exist
    ensure_directory_exists(directory)

    # Sets the directory as the local working directory
    set_working_directory(path=directory)

    console.echo(message=f"Sun lab working directory set to: {directory}.", level=LogLevel.SUCCESS)


@click.command()
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project for which to print the manifest data.",
)
@click.option(
    "-a",
    "--animal",
    type=str,
    required=False,
    help=(
        "The name of the animal for which to print the manifest data. If not provided, this CLI prints the data for "
        "all animals that participate in the specified project."
    ),
)
@click.option(
    "-n",
    "--notes",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether to print the experimenter note view of the available manifest data. This data view is "
        "optimized for checking the outcome of each session conducted as part of the target project and, optionally, "
        "by the specified animal."
    ),
)
@click.option(
    "-s",
    "--summary",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether to print the data processing view of the available manifest data. This view is optimized "
        "for tracking the data processing state of each session conducted as part of the project."
    ),
)
@click.option(
    "-u",
    "--update_manifest",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether to fetch the most recent project manifest version stored on the remote server before "
        "displaying the data. Since the manifest file is cached locally, this option is only required if the project "
        "data stored on the server has updated since the last call to this CLI."
    ),
)
@click.option(
    "-r",
    "--regenerate_manifest",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether to regenerate the manifest file on the remote server before fetching it it to the local "
        "working directory. This flag requires service access privileges and is not recommend for most use cases, as "
        "all lab pipelines automatically update the manifest file as part of their runtime."
    ),
)
def print_project_manifest_data(
    project: str,
    animal: str | None,
    notes: bool,
    summary: bool,
    update_manifest: bool,
    regenerate_manifest: bool,
) -> None:
    if not summary and not notes:
        message = (
            f"No data display options were selected when calling the command. Pass either the 'notes' (-n), "
            f"'summary' (-s), or both flags when calling the command to display the data using the target format."
        )
        console.error(message=message, error=ValueError)

    # Resolves the path to the manifest file
    manifest_path = get_working_directory().joinpath(project, "manifest.feather")

    # If the manifest file does not exist on the local machine, ensures it is fetched from the remove server
    if not manifest_path.exists() and not regenerate_manifest and not update_manifest:
        update_manifest = True

    # If requested, fetches the most recent manifest file instance from the remote server to the working directory
    # before printing the project data. Note, the default is expected to be 'update' as it does not requre service
    # account credentials.
    if update_manifest:
        # Establishes SSH connection to the processing server using the user account credentials.
        credentials = get_credentials_file_path(require_service=False)
        server = Server(credentials_path=credentials)
        fetch_remote_project_manifest(project=project, server=server)

    # Manifest regeneration requires service account credentials and re-creates the manifest before fetching it to the
    # local machine.
    elif regenerate_manifest:
        # Establishes SSH connection to the processing server using the service account credentials.
        credentials = get_credentials_file_path(require_service=True)
        server = Server(credentials_path=credentials)
        generate_remote_project_manifest(project=project, server=server)

    # Loads the manifest file data into memory
    manifest = ProjectManifest(manifest_file=manifest_path)

    # Ensures that the specified animal exists in the manifest data. Since the manifest is optimized for the Sun lab
    # data format, it stores animal IDs as integers. To improve the flexibility of this CLI, converts animal IDs to
    # strings before running the check.
    if animal is not None and animal not in [str(animal) for animal in manifest.animals]:
        message = (
            f"Unable to display the data for the target animal ({animal}), as the animal does not belong to the "
            f"target project ({project})."
        )
        console.error(message=message, error=ValueError)

    # If requested, prints the experimenter note view of the manifest data
    if notes:
        manifest.print_notes(animal=animal)

    # If requested, prints the data processing view of the manifest data
    if summary:
        manifest.print_summary(animal=animal)


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
    "-c",
    "--cores",
    type=int,
    required=True,
    show_default=True,
    default=2,
    help="The number of CPU cores to allocate to the Jupyter server.",
)
@click.option(
    "-m",
    "--memory",
    type=int,
    required=True,
    show_default=True,
    default=32,
    help="The memory (RAM), in Gigabytes, to allocate to the Jupyter server.",
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
        "at the end of this time limit, the job will be forcibly terminated by SLURM. To prevent hogging the server, "
        "make sure this parameter is always set to the smallest feasible period of time."
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
        "to 9999. Most runtimes should leave this set to the default value (0), which randomly selects one of the "
        "valid ports. Using random selection minimizes the chances of colliding with other interactive jupyter "
        "sessions."
    ),
)
def start_jupyter_server(environment: str, cores: int, memory: int, time: int, port: int) -> None:
    """Starts an interactive Jupyter session on the remote Sun lab server.

    This command allows running Jupyter lab and notebook sessions on the remote Sun lab server. Since all lab data is
    stored on the server, this allows running interactive analysis sessions on the same node as the data,
    while leveraging considerable compute resources of the server.

    Calling this command initializes a SLURM session that runs the interactive Jupyter server. Since this server
    directly competes for resources with all other headless jobs running on the server, it is imperative that each
    jupyter runtime uses the minimum amount of resources as necessary. Do not use this command to run
    heavy data processing pipelines! Instead, consult the API documentation for this library and use the headless
    Job or Pipeline class.
    """
    # Initializes server connection
    credentials_path = get_credentials_file_path(require_service=False)
    server = Server(credentials_path)

    job: JupyterJob | None = None
    job_name = f"interactive_jupyter_server"
    try:
        # Launches the Jupyter server
        job = server.launch_jupyter_server(
            job_name=job_name,
            conda_environment=environment,
            notebook_directory=server.user_working_root,
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
