from pathlib import Path

from _typeshed import Incomplete

from ..data_classes import (
    AcquisitionSystems as AcquisitionSystems,
    set_working_directory as set_working_directory,
    set_google_credentials_path as set_google_credentials_path,
    create_server_configuration_file as create_server_configuration_file,
    create_system_configuration_file as create_system_configuration_file,
)

CONTEXT_SETTINGS: Incomplete

def configure() -> None: ...
def configure_directory(directory: Path) -> None: ...
def generate_server_configuration_file(
    username: str,
    password: str,
    host: str,
    storage_root: str,
    working_root: str,
    shared_directory: str,
    *,
    service: bool,
) -> None: ...
def generate_system_configuration_file(system: AcquisitionSystems) -> None: ...
def configure_google_credentials(credentials: Path) -> None: ...
