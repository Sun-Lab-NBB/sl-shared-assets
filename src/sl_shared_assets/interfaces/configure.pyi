from pathlib import Path

from _typeshed import Incomplete

from .mcp_server import run_server as run_server
from ..configuration import (
    GasPuffTrial as GasPuffTrial,
    TaskTemplate as TaskTemplate,
    ExperimentState as ExperimentState,
    WaterRewardTrial as WaterRewardTrial,
    AcquisitionSystems as AcquisitionSystems,
    set_working_directory as set_working_directory,
    set_google_credentials_path as set_google_credentials_path,
    get_task_templates_directory as get_task_templates_directory,
    set_task_templates_directory as set_task_templates_directory,
    get_system_configuration_data as get_system_configuration_data,
    create_experiment_configuration as create_experiment_configuration,
    create_server_configuration_file as create_server_configuration_file,
    create_system_configuration_file as create_system_configuration_file,
)

CONTEXT_SETTINGS: Incomplete

def configure() -> None: ...
def configure_directory(directory: Path) -> None: ...
def generate_server_configuration_file(
    username: str, password: str, host: str, storage_root: str, working_root: str, shared_directory: str
) -> None: ...
def generate_system_configuration_file(system: AcquisitionSystems) -> None: ...
def configure_google_credentials(credentials: Path) -> None: ...
def configure_task_templates_directory(directory: Path) -> None: ...
def configure_project(project: str) -> None: ...
def generate_experiment_configuration_file(
    project: str,
    experiment: str,
    template: str,
    state_count: int,
    reward_size: float,
    reward_tone_duration: int,
    puff_duration: int,
    occupancy_duration: int,
) -> None: ...
def start_mcp_server(transport: str) -> None: ...
