from pathlib import Path

from _typeshed import Incomplete

from ..data_classes import (
    GasPuffTrial as GasPuffTrial,
    WaterRewardTrial as WaterRewardTrial,
    AcquisitionSystems as AcquisitionSystems,
    MesoscopeExperimentState as MesoscopeExperimentState,
    MesoscopeExperimentConfiguration as MesoscopeExperimentConfiguration,
    set_working_directory as set_working_directory,
    set_google_credentials_path as set_google_credentials_path,
    get_system_configuration_data as get_system_configuration_data,
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
def configure_project(project: str) -> None: ...
def generate_experiment_configuration_file(
    project: str, experiment: str, state_count: int, water_reward_count: int, gas_puff_count: int
) -> None: ...
