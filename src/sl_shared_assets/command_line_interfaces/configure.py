"""This module provides the Command-Line Interface (CLI) for configuring major components of the Sun lab data
workflow."""

from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from ..server import generate_server_credentials
from ..data_classes import (
    AcquisitionSystems,
    get_working_directory,
    set_working_directory,
    create_system_configuration_file,
)

# Ensures that displayed CLICK help messages are formatted according to the lab standard.
CONTEXT_SETTINGS = dict(max_content_width=120)  # or any width you want


@click.group("manage", context_settings=CONTEXT_SETTINGS)
def configure() -> None:
    """This Command-Line Interface (CLI) allows configuring major components of the Sun lab data acquisition,
    processing, and analysis workflow, such as acquisition systems and compute server(s)."""


@configure.command("directory")
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to cache Sun lab configuration and local runtime data.",
)
def configure_directory(directory: Path) -> None:
    """Sets the input directory as the Sun lab working directory, creating any missing path components.

    This command as the initial entry-point for setting up any machine (PC) to work with Sun lab libraries and data.
    After the working directory is configured, all calls to this and all other Sun lab libraries automatically use this
    directory to store the configuration and runtime data required to perform any requested task. This allows all Sun
    lab libraries to behave consistently across different user machines and runtime contexts.
    """
    # Creates the directory if it does not exist
    ensure_directory_exists(directory)

    # Sets the directory as the local working directory
    set_working_directory(path=directory)

    console.echo(message=f"Sun lab working directory set to: {directory}.", level=LogLevel.SUCCESS)


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
        "Determines whether the credentials' file is created for a service account. This determines the name of the "
        "generated file. Do not provide this flag unless creating a service credentials file."
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
    help=(
        "The absolute path to to the root storage server directory. Typically, this is the path to the "
        "top-level (root) directory of the HDD RAID volume."
    ),
)
@click.option(
    "-wr",
    "--working-root",
    type=str,
    required=True,
    show_default=True,
    default="/local/workdir",
    help=(
        "The absolute path to the root working server directory. Typically, this is the path to the top-level "
        "(root) directory of the NVME RAID volume. If the server uses the same volume for both storing and working "
        "with data, set this to the same path as the 'storage-root' argument."
    ),
)
@click.option(
    "-sd",
    "--shared-directory",
    type=str,
    required=True,
    show_default=True,
    default="sun_data",
    help="The name of the shared directory used to store all Sun lab project data on all server volumes.",
)
def generate_server_credentials_file(
    username: str,
    password: str,
    service: bool,
    host: str,
    storage_root: str,
    working_root: str,
    shared_directory: str,
) -> None:
    """Generates a service or user server access credentials' file.

    This command is used to set up access to the lab's remote compute server(s). The Server class uses the data stored
    inside the generated credentials .yaml file to connect to and execute remote jobs on the target compute server(s).
    Depending on the configuration, this command generates either the 'user_credentials.yaml' or
    'service_credentials.yaml' file.
    """

    # Resolves the path to the local Sun lab working directory.
    output_directory = get_working_directory()

    # Generates the requested credentials' file.
    generate_server_credentials(
        output_directory=output_directory,
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
    help="The type (name) of the data acquisition system for which to generate the configuration file.",
)
def generate_system_configuration_file(system: AcquisitionSystems) -> None:
    """Generates the configuration file for the specified data acquisition system.

    This command is typically used when setting up new data acquisition systems in the lab. The sl-experiment library
    uses the created file to load the acquisition system configuration data during data acquisition runtimes. The
    system configuration only needs to be created on the machine (PC) that runs the sl-experiment library and manages
    the acquisition runtime if the system uses multiple machines (PCs). Once the system configuration .yaml file is
    created via this command, edit the file to modify the acquisition system configuration at any time.
    """

    create_system_configuration_file(system=system)
