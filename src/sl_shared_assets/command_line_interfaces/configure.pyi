from pathlib import Path

from _typeshed import Incomplete

from ..server import generate_server_credentials as generate_server_credentials
from ..data_classes import (
    AcquisitionSystems as AcquisitionSystems,
    get_working_directory as get_working_directory,
    set_working_directory as set_working_directory,
    create_system_configuration_file as create_system_configuration_file,
)

CONTEXT_SETTINGS: Incomplete

def configure() -> None:
    """This Command-Line Interface (CLI) allows configuring major components of the Sun lab data acquisition,
    processing, and analysis workflow, such as acquisition systems and compute server(s)."""

def configure_directory(directory: Path) -> None:
    """Sets the input directory as the Sun lab working directory, creating any missing path components.

    This command as the initial entry-point for setting up any machine (PC) to work with Sun lab libraries and data.
    After the working directory is configured, all calls to this and all other Sun lab libraries automatically use this
    directory to store the configuration and runtime data required to perform any requested task. This allows all Sun
    lab libraries to behave consistently across different user machines and runtime contexts.
    """

def generate_server_credentials_file(
    username: str, password: str, service: bool, host: str, storage_root: str, working_root: str, shared_directory: str
) -> None:
    """Generates a service or user server access credentials' file.

    This command is used to set up access to the lab's remote compute server(s). The Server class uses the data stored
    inside the generated credentials .yaml file to connect to and execute remote jobs on the target compute server(s).
    Depending on the configuration, this command generates either the 'user_credentials.yaml' or
    'service_credentials.yaml' file.
    """

def generate_system_configuration_file(system: AcquisitionSystems) -> None:
    """Generates the configuration file for the specified data acquisition system.

    This command is typically used when setting up new data acquisition systems in the lab. The sl-experiment library
    uses the created file to load the acquisition system configuration data during data acquisition runtimes. The
    system configuration only needs to be created on the machine (PC) that runs the sl-experiment library and manages
    the acquisition runtime if the system uses multiple machines (PCs). Once the system configuration .yaml file is
    created via this command, edit the file to modify the acquisition system configuration at any time.
    """
