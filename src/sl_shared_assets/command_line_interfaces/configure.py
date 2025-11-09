"""This module provides the Command-Line Interface (CLI) for configuring major components of the Sun lab data
workflow.
"""

from pathlib import Path  # pragma: no cover

import click  # pragma: no cover
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists  # pragma: no cover

from ..data_classes import (
    AcquisitionSystems,
    set_working_directory,
    set_google_credentials_path,
    create_server_configuration_file,
    create_system_configuration_file,
)  # pragma: no cover

# Ensures that displayed CLICK help messages are formatted according to the lab standard.
CONTEXT_SETTINGS = {"max_content_width": 120}  # pragma: no cover


@click.group("configure", context_settings=CONTEXT_SETTINGS)
def configure() -> None:  # pragma: no cover
    """This Command-Line Interface allows configuring major components of the Sun lab data workflow."""


@configure.command("directory")
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to cache Sun lab configuration and local runtime data.",
)
def configure_directory(directory: Path) -> None:  # pragma: no cover
    """Sets the input directory as the local Sun lab's working directory."""
    # Creates the directory if it does not exist
    ensure_directory_exists(directory)

    # Sets the directory as the local working directory
    set_working_directory(path=directory)


@configure.command("server")
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
    "-s",
    "--service",
    is_flag=True,
    default=False,
    help=(
        "Determines whether the server configuration file should use the shared service account for accessing the "
        "server."
    ),
)
@click.option(
    "-h",
    "--host",
    type=str,
    required=True,
    show_default=True,
    default="cbsuwsun.biohpc.cornell.edu",
    help="The host name or IP address of the server.",
)
@click.option(
    "-sr",
    "--storage-root",
    type=str,
    required=True,
    show_default=True,
    default="/local/storage",
    help="The absolute path to to the server's slow HDD RAID volume.",
)
@click.option(
    "-wr",
    "--working-root",
    type=str,
    required=True,
    show_default=True,
    default="/local/workdir",
    help="The absolute path to to the server's fast NVME RAID volume.",
)
@click.option(
    "-sd",
    "--shared-directory",
    type=str,
    required=True,
    show_default=True,
    default="sun_data",
    help="The name of the shared directory used to store all Sun lab's projects on both server's volumes.",
)
def generate_server_configuration_file(
    username: str,
    password: str,
    host: str,
    storage_root: str,
    working_root: str,
    shared_directory: str,
    *,
    service: bool,
) -> None:  # pragma: no cover
    """Creates the requested service or user server configuration file."""
    # Generates the requested credentials' file.
    create_server_configuration_file(
        username=username,
        password=password,
        service=service,
        host=host,
        storage_root=storage_root,
        working_root=working_root,
        shared_directory_name=shared_directory,
    )


@configure.command("system")
@click.option(
    "-s",
    "--system",
    type=click.Choice(AcquisitionSystems, case_sensitive=False),
    show_default=True,
    required=True,
    default=AcquisitionSystems.MESOSCOPE_VR,
    help="The type (name) of the data acquisition system for which to create the configuration file.",
)
def generate_system_configuration_file(system: AcquisitionSystems) -> None:  # pragma: no cover
    """Creates the specified data acquisition system's configuration file."""
    create_system_configuration_file(system=system)


@configure.command("google")
@click.option(
    "-c",
    "--credentials",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="The absolute path to the Google service account credentials .JSON file.",
)
def configure_google_credentials(credentials: Path) -> None:  # pragma: no cover
    """Sets the path to the Google service account credentials file."""
    # Sets the Google Sheets credentials path
    set_google_credentials_path(path=credentials)

    console.echo(
        message=f"Google Sheets credentials path set to: {credentials.resolve()}.",
        level=LogLevel.SUCCESS,
    )
