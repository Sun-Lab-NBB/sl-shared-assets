"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process.
Primarily, these CLIs are used when setting up or reconfiguring the VRPC and other machines in the lab to work with
sl-experiment and sl-forgery libraries."""

from pathlib import Path

import click

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
    project directory when it is used for the first time. All future projects reuse the same 'root' path. Since this
    information is stored in a typically hidden user directory, this CLI can be used to replace the local directory
    path, if necessary.
    """
    replace_root_path(path=Path(path))


@click.command()
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    prompt="Enter the path to the directory where to create the credentials file: ",
    help="The path to the directory where to create the credentials file.",
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

    This CLI is used during the initial PC setup (typically, VRPC) to allow it to access the lab BioHPC server.
    """
    generate_server_credentials(
        output_directory=Path(output_directory), username=username, password=password, host=host
    )
