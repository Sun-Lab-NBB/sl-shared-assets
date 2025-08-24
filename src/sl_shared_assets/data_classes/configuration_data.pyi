from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig

from ..server import ServerCredentials as ServerCredentials

class AcquisitionSystems(StrEnum):
    """Stores the names for all data acquisition systems currently used in the Sun lab."""

    MESOSCOPE_VR = "mesoscope-vr"

@dataclass()
class ExperimentState:
    """Stores the information used to set and maintain the desired experiment and system state.

    Broadly, each experiment runtime can be conceptualized as a two-state system. The first is the experiment task
    state, which reflects the behavior goal, the rules for achieving the goal, and the reward for achieving the goal.
    The second is the data acquisition system state, which is a snapshot of all hardware module states that make up the
    system that acquires the data and controls the task environment.

    Note:
        This class is acquisition-system-agnostic. All data acquisition systems use this class as part of their specific
        ExperimentConfiguration class instances.
    """

    experiment_state_code: int
    system_state_code: int
    state_duration_s: float
    initial_guided_trials: int
    recovery_failed_trial_threshold: int
    recovery_guided_trials: int

@dataclass()
class ExperimentTrial:
    """Stores the information about a single experiment trial.

    All Virtual Reality (VR) tasks can be broadly conceptualized as repeating motifs (sequences) of VR environment wall
    cues, associated with a specific goal, for which animals receive water rewards. Each complete motif is typically
    interpreted as a single experiment trial.

    Notes:
        Since some experiments use multiple distinct trial types as part of the same experiment session, multiple
        instances of this class can be used by an ExperimentConfiguration class instance to represent multiple used
        trial types.
    """

    cue_sequence: list[int]
    trial_length_cm: float
    trial_reward_size_ul: float
    reward_zone_start_cm: float
    reward_zone_end_cm: float
    guidance_trigger_location_cm: float

@dataclass()
class MesoscopeExperimentConfiguration(YamlConfig):
    """Stores the configuration of an experiment runtime that uses the Mesoscope_VR data acquisition system.

    During runtime, the acquisition system executes the sequence of states stored in this class instance. Together with
    custom Unity projects, which define the task environment and logic, this class allows flexibly implementing a wide
    range of experiments using the Mesoscope-VR system.
    """

    cue_map: dict[int, float] = field(default_factory=Incomplete)
    cue_offset_cm: float = ...
    unity_scene_name: str = ...
    experiment_states: dict[str, ExperimentState] = field(default_factory=Incomplete)
    trial_structures: dict[str, ExperimentTrial] = field(default_factory=Incomplete)

@dataclass()
class MesoscopePaths:
    """Stores the filesystem configuration parameters for the Mesoscope-VR data acquisition system.

    Notes:
        All directories specified in this instance must be mounted to the local PC's filesystem using an SMB or an
        equivalent protocol.
    """

    google_credentials_path: Path = ...
    root_directory: Path = ...
    server_storage_directory: Path = ...
    server_working_directory: Path = ...
    nas_directory: Path = ...
    mesoscope_directory: Path = ...
    harvesters_cti_path: Path = ...

@dataclass()
class MesoscopeSheets:
    """Stores the identifiers for the Google Sheet files used by the Mesoscope-VR data acquisition system."""

    surgery_sheet_id: str = ...
    water_log_sheet_id: str = ...

@dataclass()
class MesoscopeCameras:
    """Stores the configuration parameters for the cameras used by the Mesoscope-VR system to record behavior videos."""

    face_camera_index: int = ...
    left_camera_index: int = ...
    right_camera_index: int = ...
    face_camera_quantization_parameter: int = ...
    body_camera_quantization_parameter: int = ...
    display_face_camera_frames: bool = ...
    display_body_camera_frames: bool = ...

@dataclass()
class MesoscopeMicroControllers:
    """Stores the configuration parameters for the microcontrollers used by the Mesoscope-VR system."""

    actor_port: str = ...
    sensor_port: str = ...
    encoder_port: str = ...
    debug: bool = ...
    minimum_break_strength_g_cm: float = ...
    maximum_break_strength_g_cm: float = ...
    wheel_diameter_cm: float = ...
    lick_threshold_adc: int = ...
    lick_signal_threshold_adc: int = ...
    lick_delta_threshold_adc: int = ...
    lick_averaging_pool_size: int = ...
    torque_baseline_voltage_adc: int = ...
    torque_maximum_voltage_adc: int = ...
    torque_sensor_capacity_g_cm: float = ...
    torque_report_cw: bool = ...
    torque_report_ccw: bool = ...
    torque_signal_threshold_adc: int = ...
    torque_delta_threshold_adc: int = ...
    torque_averaging_pool_size: int = ...
    wheel_encoder_ppr: int = ...
    wheel_encoder_report_cw: bool = ...
    wheel_encoder_report_ccw: bool = ...
    wheel_encoder_delta_threshold_pulse: int = ...
    wheel_encoder_polling_delay_us: int = ...
    cm_per_unity_unit: float = ...
    screen_trigger_pulse_duration_ms: int = ...
    auditory_tone_duration_ms: int = ...
    valve_calibration_pulse_count: int = ...
    sensor_polling_delay_ms: int = ...
    valve_calibration_data: dict[int | float, int | float] | tuple[tuple[int | float, int | float], ...] = ...

@dataclass()
class MesoscopeAdditionalFirmware:
    """Stores the configuration parameters for all firmware and hardware components not assembled in the Sun lab."""

    headbar_port: str = ...
    lickport_port: str = ...
    wheel_port: str = ...
    unity_ip: str = ...
    unity_port: int = ...

@dataclass()
class MesoscopeSystemConfiguration(YamlConfig):
    """Stores the hardware and filesystem configuration parameters for the Mesoscope-VR data acquisition system.

    This class is specifically designed to encapsulate the configuration parameters for the Mesoscope-VR system. It
    expects the system to be configured according to the specifications outlined in the sl-experiment repository
    (https://github.com/Sun-Lab-NBB/sl-experiment) and should be used exclusively on the VRPC machine
    (main Mesoscope-VR PC).
    """

    name: str = ...
    paths: MesoscopePaths = field(default_factory=MesoscopePaths)
    sheets: MesoscopeSheets = field(default_factory=MesoscopeSheets)
    cameras: MesoscopeCameras = field(default_factory=MesoscopeCameras)
    microcontrollers: MesoscopeMicroControllers = field(default_factory=MesoscopeMicroControllers)
    additional_firmware: MesoscopeAdditionalFirmware = field(default_factory=MesoscopeAdditionalFirmware)
    def __post_init__(self) -> None:
        """Ensures that variables converted to different types for storage purposes are always set to expected types
        upon class instantiation."""
    def save(self, path: Path) -> None:
        """Saves class instance data to disk as a .yaml file.

        This method converts certain class variables to yaml-safe types (for example, Path objects -> strings) and
        saves class data to disk as a .yaml file. The method is intended to be used solely by the
        create_system_configuration_file() function and should not be called from any other context.

        Args:
            path: The path to the .yaml file to save the data to.
        """

def set_working_directory(path: Path) -> None:
    """Sets the specified directory as the Sun lab working directory for the local machine (PC).

    This function is used as the first step for configuring any machine to work with the data stored on the remote
    compute server(s). All lab libraries use this directory for caching configuration data and runtime working
    (intermediate) data.

    Notes:
        The path to the working directory is stored inside the user's data directory so that all Sun lab libraries can
        automatically access and use the same working directory.

        If the input path does not point to an existing directory, the function will automatically generate the
        requested directory.

        After setting up the working directory, the user should use other commands from the 'sl-configure' CLI to
        generate the remote compute server access credentials and / or acquisition system configuration files.

    Args:
        path: The path to the directory to set as the local Sun lab working directory.
    """

def get_working_directory() -> Path:
    """Resolves and returns the path to the local Sun lab working directory.

    This service function is primarily used when working with Sun lab data stored on remote compute server(s) to
    establish local working directories for various jobs and pipelines.

    Returns:
        The path to the local working directory.

    Raises:
        FileNotFoundError: If the local machine does not have the Sun lab data directory, or the local working
            directory does not exist (has not been configured).
    """

def get_credentials_file_path(service: bool = False) -> Path:
    """Resolves and returns the path to the requested .yaml file that stores access credentials for the Sun lab
    remote compute server.

    Depending on the configuration, either returns the path to the 'user_credentials.yaml' file (default) or the
    'service_credentials.yaml' file.

    Notes:
        Assumes that the local working directory has been configured before calling this function.

    Args:
        service: Determines whether this function must evaluate and return the path to the
            'service_credentials.yaml' file (if true) or the 'user_credentials.yaml' file (if false).

    Raises:
        FileNotFoundError: If either the 'service_credentials.yaml' or the 'user_credentials.yaml' files do not exist
            in the local Sun lab working directory.
        ValueError: If both credential files exist, but the requested credentials file is not configured.
    """

_supported_configuration_files: Incomplete

def create_system_configuration_file(system: AcquisitionSystems | str) -> None:
    """Creates the .yaml configuration file for the requested Sun lab data acquisition system and configures the local
    machine (PC) to use this file for all future acquisition-system-related calls.

    This function is used to initially configure or override the existing configuration of any data acquisition system
    used in the lab.

    Notes:
        This function creates the configuration file inside the shared Sun lab working directory on the local machine.
        It assumes that the user has configured (created) the directory before calling this function.

        A data acquisition system can consist of multiple machines (PCs). The configuration file is typically only
        present on the 'main' machine that manages all runtimes.

    Args:
        system: The name (type) of the data acquisition system for which to create the configuration file. Must be one
            of the following supported options: mesoscope-vr.

    Raises:
        ValueError: If the input acquisition system name (type) is not recognized.
    """

def get_system_configuration_data() -> MesoscopeSystemConfiguration:
    """Resolves the path to the local data acquisition system configuration file and loads the configuration data as
    a SystemConfiguration instance.

    This service function is used by all Sun lab data acquisition runtimes to load the system configuration data from
    the locally stored configuration file. It supports resolving and returning the data for all data acquisition
    systems currently used in the lab.

    Returns:
        The initialized SystemConfiguration class instance for the local data acquisition system that stores the loaded
        configuration parameters.

    Raises:
        FileNotFoundError: If the local machine does not have a valid data acquisition system configuration file.
    """
