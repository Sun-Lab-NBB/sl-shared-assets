"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console

from .tools import ascend_tyche_data, verify_session_checksum, generate_project_manifest
from .server import generate_server_credentials
from .data_classes import SessionData, ProcessingTracker


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session whose raw data needs to be verified for potential corruption.",
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
def verify_session_integrity(session_path: str, create_processed_directories: bool, processed_data_root: Path) -> None:
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
    project_path: str, output_directory: str, project_processed_path: str | None
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
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
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
    "-rdp",
    "--raw_data_path",
    type=str,
    required=True,
    default="/storage/sun_data",
    help=(
        "The absolute path to the directory used to store raw data from all Sun lab projects, relative to the server "
        "root."
    ),
)
@click.option(
    "-pdp",
    "--processed_data_path",
    type=str,
    required=True,
    default="/workdir/sun_data",
    help=(
        "The absolute path to the directory used to store processed data from all Sun lab projects, relative to the "
        "server root."
    ),
)
def generate_server_credentials_file(
    output_directory: str, host: str, username: str, password: str, raw_data_path: str, processed_data_path: str
) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This command is used to set up access to compute servers and clusters on new machines (PCs). The data stored inside
    the server_credentials.yaml file generated by this command is used by the Server and Job classes used in many Sun
    lab data processing libraries.
    """
    generate_server_credentials(
        output_directory=Path(output_directory),
        username=username,
        password=password,
        host=host,
        raw_data_root=raw_data_path,
        processed_data_root=processed_data_path,
    )
    message = (
        f"Server access credentials file: generated. If necessary, remember to edit the data acquisition system "
        f"configuration file to include the path to the credentials file generated via this CLI."
    )
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
def ascend_tyche_directory(input_directory: str) -> None:
    """Restructures old Tyche project data to use the modern Sun lab data structure and uploads them to the processing
    server.

    This command is used to convert ('ascend') the old Tyche project data to the modern Sun lab structure. After
    ascension, the data can be processed and analyzed using all modern Sun lab (sl-) tools and libraries. Note, this
    process expects the input data to be preprocessed using an old Sun lab mesoscope data preprocessing pipeline. It
    will not work for any other project or data. Also, this command will only work on a machine (PC) that belongs to a
    valid Sun lab data acquisition system, such as VRPC of the Mesoscope-VR system.
    """
    ascend_tyche_data(root_directory=Path(input_directory))
