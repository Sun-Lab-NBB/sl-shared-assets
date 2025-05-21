"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click

from .tools import verify_session_checksum, generate_project_manifest
from .server import generate_server_credentials
from .data_classes import set_system_configuration_file, MesoscopeSystemConfiguration
from ataraxis_base_utilities import console, ensure_directory_exists


@click.command()
@click.option(
    "-s",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session whose raw data needs to be verified for potential corruption.",
)
def verify_session_integrity(session_path: str) -> None:
    """Checks the integrity of the target session's raw_data folder contents.

    This command assumes that the data has been checksummed during acquisition and contains an ax_checksum.txt file
    that stores the data checksum generated before transferring the data to long-term storage destination. This function
    always verified the integrity of the 'raw_data' directory. It does not work with 'processed_data' or any other
    directories.
    """
    verify_session_checksum(Path(session_path))


@click.command()
@click.option(
    "-pr",
    "--project_raw_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the project's directory where raw session data is stored.",
)
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated project manifest file.",
)
@click.option(
    "-pp",
    "--project_processed_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the project's directory where processed session data is stored, if different from the "
        "project's raw session data directory."
    ),
)
def generate_project_manifest_file(project_raw_path: str, output_directory: str, project_processed_path: str | None) -> None:
    """ Generates a manifest .feather
    """
    generate_project_manifest(
        raw_project_directory=Path(project_raw_path),
        output_directory=Path(output_directory),
        processed_project_directory=Path(project_processed_path) if project_processed_path else None,
    )


@click.command()
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated system configuration file.",
)
@click.option(
    "-t",
    "--target_system",
    type=str,
    show_default=True,
    required=True,
    default="Mesoscope-VR",
    help=(
        "The type (name) of the data acquisition system for which to generate the configuration file. Note, currently, "
        "only the following types are supported: Mesoscope-VR."
    )
)
def generate_system_configuration_file(path: str, target_system: str) -> None:
    """Generates a precursor system configuration file for the target acquisition system and configures all local
    Sun lab libraries to use that file to load the acquisition system configuration data.

    This command is typically used when setting up a new data acquisition system in the lab. The system configuration
    only needs to be specified on the machine (PC) that runs the sl-experiment library and manages the acquisition
    runtime if the system uses multiple machines (PCs). Once the system configuration .yaml file is created via this
    command, editing the configuration parameters in the file will automatically take effect during all following
    runtimes.
    """

    # Verifies that the input path is a valid directory path and, if necessary, creates the directory specified by the
    # path.
    path = Path(path)
    if not path.is_dir():
        message = (
            f"Unable to generate the system configuration file for the system '{target_system}'. The path to "
            f"the output directory ({path}) is not a valid directory path."
        )
        console.error(message=message, error=ValueError)
    else:
        ensure_directory_exists(path)

    # Mesoscope
    if target_system == "Mesoscope-VR":
        file_path = path.joinpath("mesoscope_system_configuration.yaml")
        system_configuration = MesoscopeSystemConfiguration()
        system_configuration.save(file_path)
        set_system_configuration_file(file_path)

    # For unsupported system types, raises an error message
    else:
        message = (
            f"Unable to generate the system configuration file for the system '{target_system}'. The input "
            f"acquisition system is not supported (not recognized). Currently, only the following acquisition "
            f"systems are supported: Mesoscope-VR."
        )
        console.error(message=message, error=ValueError)


@click.command()
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated server credentials file.",
)
@click.option(
    "-h",
    "--host",
    type=str,
    show_default=True,
    required=True,
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
def generate_server_credentials_file(output_directory: str, host: str, username: str, password: str) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This command is used to set up access to compute servers and clusters on new machines (PCs). The data stored inside
    the server_credentials.yaml file generated by this command is used by the Server and Job classes used in many Sun
    lab data processing libraries.
    """
    generate_server_credentials(
        output_directory=Path(output_directory), username=username, password=password, host=host
    )


def create_new_project() -> None:
    pass
