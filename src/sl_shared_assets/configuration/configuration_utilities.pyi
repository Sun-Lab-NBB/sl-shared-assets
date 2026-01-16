from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass
from collections.abc import Callable

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig

from .vr_configuration import (
    TriggerType as TriggerType,
    TaskTemplate as TaskTemplate,
)
from .mesoscope_configuration import (
    MesoscopeSystemConfiguration as MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration as MesoscopeExperimentConfiguration,
)
from .experiment_configuration import (
    GasPuffTrial as GasPuffTrial,
    WaterRewardTrial as WaterRewardTrial,
)

class AcquisitionSystems(StrEnum):
    MESOSCOPE_VR = "mesoscope"

SystemConfiguration = MesoscopeSystemConfiguration
ExperimentConfiguration = MesoscopeExperimentConfiguration
_SYSTEM_CONFIG_CLASSES: dict[str, type[SystemConfiguration]]
_CONFIG_FILE_TO_CLASS: dict[str, type[SystemConfiguration]]
ExperimentConfigFactory = Callable[
    [TaskTemplate, str, dict[str, WaterRewardTrial | GasPuffTrial], float], ExperimentConfiguration
]
_EXPERIMENT_CONFIG_FACTORIES: dict[str, ExperimentConfigFactory]

def _create_mesoscope_experiment_config(
    template: TaskTemplate,
    unity_scene_name: str,
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial],
    cue_offset_cm: float,
) -> MesoscopeExperimentConfiguration: ...
@dataclass
class ServerConfiguration(YamlConfig):
    username: str = ...
    password: str = ...
    host: str = ...
    storage_root: str = ...
    working_root: str = ...
    shared_directory_name: str = ...
    shared_storage_root: str = field(init=False, default_factory=Incomplete)
    shared_working_root: str = field(init=False, default_factory=Incomplete)
    user_data_root: str = field(init=False, default_factory=Incomplete)
    user_working_root: str = field(init=False, default_factory=Incomplete)
    def __post_init__(self) -> None: ...

def set_working_directory(path: Path) -> None: ...
def get_working_directory() -> Path: ...
def set_google_credentials_path(path: Path) -> None: ...
def get_google_credentials_path() -> Path: ...
def set_task_templates_directory(path: Path) -> None: ...
def get_task_templates_directory() -> Path: ...
def create_system_configuration_file(system: AcquisitionSystems | str) -> None: ...
def get_system_configuration_data() -> SystemConfiguration: ...
def create_server_configuration_file(
    username: str,
    password: str,
    host: str = "cbsuwsun.biohpc.cornell.edu",
    storage_root: str = "/local/workdir",
    working_root: str = "/local/storage",
    shared_directory_name: str = "sun_data",
) -> None: ...
def get_server_configuration() -> ServerConfiguration: ...
def create_experiment_configuration(
    template: TaskTemplate,
    system: AcquisitionSystems | str,
    unity_scene_name: str,
    default_reward_size_ul: float = 5.0,
    default_reward_tone_duration_ms: int = 300,
    default_puff_duration_ms: int = 100,
    default_occupancy_duration_ms: int = 1000,
) -> ExperimentConfiguration: ...
