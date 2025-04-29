"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click

from .tools import ascend_tyche_data
from .server import generate_server_credentials
from .data_classes import replace_root_path


@click.command()
@click.option(
    "-p",
    "--path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    prompt="Enter the path to the new local directory where to store all project subdirectories: ",
    help="The path to the new local directory where to store all project subdirectories.",
)
def replace_local_root_directory(path: str) -> None:
    """Replaces the root directory used to store all lab projects on the local PC with the specified directory.

    To ensure all projects are saved in the same location, this library resolves and saves the absolute path to the
    project directory the first time ProjectConfiguration class instance is created on a new PC. All future projects
    automatically reuse the same 'root' directory path. Since this information is stored in a typically hidden user
    directory, this CLI can be used to replace the local directory path, if necessary.
    """
    replace_root_path(path=Path(path))


@click.command()
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to create the credentials file.",
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

    This CLI is used to set up new PCs to work with the lab BioHPC server. While this is primarily intended for the
    VRPC, any machined that interacts with BioHPC server can use this CLI to build the access credentials file.
    """
    generate_server_credentials(
        output_directory=Path(output_directory), username=username, password=password, host=host
    )


@click.command()
@click.option(
    "-p",
    "--path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory that stores original Tyche animal folders.",
)
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the local directory where to create the ascended Tyche project hierarchy.",
)
@click.option(
    "-s",
    "--server_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help=(
        "The path to the SMB-mounted BioHPC server directory where to transfer the ascended Tyche project "
        "hierarchy after it is created."
    ),
)
def ascend_tyche_directory(path: str, output_directory: str, server_directory: str) -> None:
    """Restructures old Tyche project data to use the modern Sun lab data structure.

    This CLI is used to convert ('ascend') the old Tyche project data to the modern Sun lab structure. After
    ascension, the data can be processed and analyzed using all modern Sun lab (sl-) tools and libraries. Note, this
    process expects the input data to be preprocessed using an old Sun lab mesoscope data preprocessing pipeline. It
    will not work for any other project or data.
    """
    ascend_tyche_data(
        root_directory=Path(path),
        output_root_directory=Path(output_directory),
        server_root_directory=Path(server_directory),
    )
