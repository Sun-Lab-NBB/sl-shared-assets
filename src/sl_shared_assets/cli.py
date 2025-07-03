"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from .tools import ascend_tyche_data, resolve_p53_marker, verify_session_checksum, generate_project_manifest
from .server import Server, JupyterJob, generate_server_credentials
from .data_classes import SessionData, ProcessingTracker


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session directory whose raw data needs to be verified for potential corruption.",
)
@click.option(
    "-c",
    "--create_processed_directories",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether to create the processed data hierarchy. This flag should be disabled for most runtimes. "
        "Primarily, it is used by lab acquisition system code to generate processed data directories on the remote "
        "compute servers as part of the data preprocessing pipeline."
    ),
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
        "automatically modified to include the project name, the animal id, and the session ID. This argument is only "
        "used if 'create_processed_directories' flag is True."
    ),
)
def verify_session_integrity(
    session_path: Path, create_processed_directories: bool, processed_data_root: Path | None
) -> None:
    """Checks the integrity of the target session's raw data (contents of the raw_data directory).

    This command assumes that the data has been checksummed during acquisition and contains an ax_checksum.txt file
    that stores the data checksum generated before transferring the data to long-term storage destination. This function
    always verified the integrity of the 'raw_data' directory. It does not work with 'processed_data' or any other
    directories. If the session data was corrupted, the command removes the 'telomere.bin' file, marking the session as
    'incomplete' and automatically excluding it from all further automated processing runtimes. if the session data
    is intact, generates a 'verified.bin' marker file inside the session's raw_data folder.

    The command is also used by Sun lab data acquisition systems to generate the processed data hierarchy for each
    processed session. This use case is fully automated and should not be triggered manually by the user.
    """
    session = Path(session_path)
    session_data = SessionData.load(session_path=session)

    # Runs the verification process
    verify_session_checksum(
        session, create_processed_data_directory=create_processed_directories, processed_data_root=processed_data_root
    )

    # Checks the outcome of the verification process
    tracker = ProcessingTracker(file_path=session_data.raw_data.integrity_verification_tracker_path)
    if tracker.is_complete:
        # noinspection PyTypeChecker
        console.echo(message=f"Session {session.stem} raw data integrity: Verified.", level=LogLevel.SUCCESS)
    else:
        # noinspection PyTypeChecker
        console.echo(message=f"Session {session.stem} raw data integrity: Compromised!", level=LogLevel.ERROR)


@click.command()
@click.option(
    "-pp",
    "--project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the project directory where raw session data is stored.",
)
@click.option(
    "-od",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated project manifest file.",
)
@click.option(
    "-ppp",
    "--project_processed_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the project directory where processed session data is stored, if different from the "
        "directory used to store raw session data. Typically, this extra argument is only used when processing data "
        "stored on remote compute server(s)."
    ),
)
def generate_project_manifest_file(
    project_path: Path, output_directory: Path, project_processed_path: Path | None
) -> None:
    """Generates the manifest .feather file that provides information about the data-processing state of all available
    project sessions.

    The manifest file is typically used when batch-processing session data on the remote compute server. It contains the
    comprehensive snapshot of the available project's data in a table-compatible format that can also be transferred
    between machines (as it is cached in a file).
    """
    generate_project_manifest(
        raw_project_directory=Path(project_path),
        output_directory=Path(output_directory),
        processed_project_directory=Path(project_processed_path) if project_processed_path else None,
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
    "-id",
    "--input_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory that stores original Tyche animal folders.",
)
def ascend_tyche_directory(input_directory: Path) -> None:
    """Restructures old Tyche project data to use the modern Sun lab data structure and uploads them to the processing
    server.

    This command is used to convert ('ascend') the old Tyche project data to the modern Sun lab structure. After
    ascension, the data can be processed and analyzed using all modern Sun lab (sl-) tools and libraries. Note, this
    process expects the input data to be preprocessed using an old Sun lab mesoscope data preprocessing pipeline. It
    will not work for any other project or data. Also, this command will only work on a machine (PC) that belongs to a
    valid Sun lab data acquisition system, such as VRPC of the Mesoscope-VR system.
    """
    ascend_tyche_data(root_directory=Path(input_directory))


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
        # If the caller did not provide an explicit notebook directory, defaults to user's working directory
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
        if job is not None:
            server.abort_job(job)

        # Closes server connection if it is still open
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
    "-c",
    "--create_processed_directories",
    is_flag=True,
    show_default=True,
    default=False,
    help="Determines whether to create the processed data hierarchy. This flag should be disabled for most runtimes.",
)
@click.option(
    "-ppp",
    "--project_processed_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the project directory where processed session data is stored, if different from the "
        "directory used to store raw session data. Typically, this extra argument is only used when processing data "
        "stored on remote compute server(s)."
    ),
)
@click.option(
    "-r",
    "--remove",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether the command should create or remove the dataset integration marker. Do not enable this "
        "flag unless you know what you are doing. It is only safe to enable this flag if the session is not currently "
        "being integrated into any datasets."
    ),
)
def resolve_dataset_marker(
    session_path: Path, create_processed_directories: bool, project_processed_path: Path | None, remove: bool
) -> None:
    """Depending on configuration, either creates or removes the p53.bin marker from the target session.

    The p53.bin marker determines whether the session is ready for dataset integration. When the marker exists,
    processing pipelines are not allowed to work with the session data, ensuring that all processed data remains
    unchanged. If the marker does not exist, dataset integration pipelines are not allowed to work with the session
    data, enabling processing pipelines to safely modify the data at any time.

    This command is automatically called at the end of each processing runtime to automatically transfer processed
    sessions to the dataset integration step by creating the p53.bin marker. In contrast, removing the marker can only
    be done manually.
    """
    resolve_p53_marker(
        session_path=session_path,
        create_processed_data_directory=create_processed_directories,
        processed_data_root=project_processed_path,
        remove=remove,
    )
