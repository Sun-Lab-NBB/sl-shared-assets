"""This module provides classes used to configure data acquisition and processing runtimes in the Sun lab."""

import copy
from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass

import appdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from ..server import ServerCredentials


class AcquisitionSystems(StrEnum):
    """Stores the names for all data acquisition systems currently used in the Sun lab."""

    MESOSCOPE_VR = "mesoscope-vr"
    """The Mesoscope-VR data acquisition system. It is built around 2-Photon Random Access Mesoscope (2P-RAM) and 
    relies on Unity-backed virtual reality task-environments to conduct experiments."""


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
    """The integer code of the experiment state. Note, each experiment is expected to define and follow its own 
    experiment state code mapping. Typically, the experiment state code is used to denote major experiment stages, 
    such as 'baseline', 'task', 'cooldown', etc. The same experiment state code can be used by multiple sequential 
    ExperimentState instances to change the data acquisition system states while maintaining the same experiment
    state."""
    system_state_code: int
    """One of the supported data acquisition system state-codes. Note, the meaning of each system state code depends on 
    the specific data acquisition system used during the experiment."""
    state_duration_s: float
    """The time, in seconds, to maintain the experiment and system state combination specified by this instance during 
    runtime."""
    initial_guided_trials: int
    """The number of trials (laps), counting from the onset of the experiment state, during which the animal should 
    receive water rewards for entering the reward zone. Once the specified number of guided trials passes, the system 
    disables guidance, requiring the animal to lick in the reward zone to get rewards."""
    recovery_failed_trial_threshold: int
    """The number of sequentially failed (non-rewarded) trials (laps), after which the system should 
    re-enable lick guidance for the following 'recovery_guided_trials' number of trials."""
    recovery_guided_trials: int
    """The number of trials (laps) for which the system should re-enable lick guidance, when the animal 
    sequentially fails 'failed_trial_threshold' number of trials. This field works similar to the 
    'initial_guided_trials' field, but is triggered by repeated performance failures, rather than experiment state 
    onset."""


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
    """The sequence of Virtual Reality environment wall cues experienced by the animal while running this 
    trial. Note, the cues must be specified as integer-codes matching the codes used in the 'cue_map' dictionary of the 
    ExperimentConfiguration class for the experiment."""
    trial_length_cm: float
    """The length of the trial cue sequence in centimeters."""
    trial_reward_size_ul: float
    """The volume of water, in microliters, dispensed when the animal successfully completes the trial's task."""
    reward_zone_start_cm: float
    """The starting boundary of the trial reward zone, in centimeters."""
    reward_zone_end_cm: float
    """The ending boundary of the trial reward zone, in centimeters."""
    guidance_trigger_location_cm: float
    """The location of the invisible boundary (wall) with which the animal must collide to trigger water reward 
    delivery during guided trials."""


# noinspection PyArgumentList
@dataclass()
class MesoscopeExperimentConfiguration(YamlConfig):
    """Stores the configuration of an experiment runtime that uses the Mesoscope_VR data acquisition system.

    During runtime, the acquisition system executes the sequence of states stored in this class instance. Together with
    custom Unity projects, which define the task environment and logic, this class allows flexibly implementing a wide
    range of experiments using the Mesoscope-VR system.
    """

    cue_map: dict[int, float] = field(default_factory=lambda: {0: 30.0, 1: 30.0, 2: 30.0, 3: 30.0, 4: 30.0})
    """Maps each integer-code associated with the experiment's Virtual Reality (VR) environment wall 
    cue to its length in real-world centimeters. It is used to map each VR cue to the distance the animal needs
    to travel to fully traverse the wall cue region from start to end."""
    cue_offset_cm: float = 10.0
    """Specifies the offset distance, in centimeters, by which the animal's running track is shifted relative to the 
    Virtual Reality (VR) environment's wall cue sequence. Due to how the VR environment is displayed to the animal, 
    most runtimes need to shift the animal slightly forward relative to the VR cue sequence origin (0), to prevent it 
    from seeing the portion of the environment before the first VR wall cue. This offset statically shifts the entire 
    track (in centimeters) against the set of VR wall cues used during runtime."""
    unity_scene_name: str = "IvanScene"
    """The name of the Virtual Reality task (Unity Scene) used during experiment."""
    experiment_states: dict[str, ExperimentState] = field(
        default_factory=lambda: {
            "baseline": ExperimentState(
                experiment_state_code=1,
                system_state_code=1,
                state_duration_s=30,
                initial_guided_trials=0,
                recovery_failed_trial_threshold=0,
                recovery_guided_trials=0,
            ),
            "experiment": ExperimentState(
                experiment_state_code=2,
                system_state_code=2,
                state_duration_s=120,
                initial_guided_trials=3,
                recovery_failed_trial_threshold=6,
                recovery_guided_trials=3,
            ),
            "cooldown": ExperimentState(
                experiment_state_code=3,
                system_state_code=1,
                state_duration_s=15,
                initial_guided_trials=1000000,
                recovery_failed_trial_threshold=0,
                recovery_guided_trials=0,
            ),
        }
    )
    """Maps human-readable experiment state names to corresponding ExperimentState instances. Each ExperimentState 
    instance represents a phase of the experiment. During runtime, the phases are executed in the same order as 
    specified in this dictionary."""
    trial_structures: dict[str, ExperimentTrial] = field(
        default_factory=lambda: {
            "cyclic_4_cue": ExperimentTrial(
                cue_sequence=[1, 0, 2, 0, 3, 0, 4, 0],
                trial_length_cm=240.0,
                trial_reward_size_ul=5.0,
                reward_zone_start_cm=208.0,
                reward_zone_end_cm=222.0,
                guidance_trigger_location_cm=208.0,
            )
        }
    )
    """Maps human-readable trial structure names to corresponding ExperimentTrial instances. Each ExperimentTrial 
    instance specifies the Virtual Reality (VR) environment layout and task parameters associated with a single 
    type of trials supported by the experiment runtime."""


@dataclass()
class MesoscopePaths:
    """Stores the filesystem configuration parameters for the Mesoscope-VR data acquisition system.

    Notes:
        All directories specified in this instance must be mounted to the local PC's filesystem using an SMB or an
        equivalent protocol.
    """

    google_credentials_path: Path = Path("/media/Data/Experiments/sl-surgery-log-0f651e492767.json")
    """
    The absolute path to the locally stored .JSON file that contains the service account credentials used to read and 
    write Google Sheet data. This is used to access and work with the Google Sheet files used in the Sun lab.
    """
    root_directory: Path = Path("/media/Data/Experiments")
    """The absolute path to the directory where all projects are stored on the main data acquisition system PC."""
    server_storage_directory: Path = Path("/home/cybermouse/server/storage/sun_data")
    """The absolute path to the local-filesystem-mounted directory where the raw data from all projects is stored on 
    the remote compute server."""
    server_working_directory: Path = Path("/home/cybermouse/server/workdir/sun_data")
    """The absolute path to the local-filesystem-mounted directory where the processed data from all projects is 
    stored on the remote compute server."""
    nas_directory: Path = Path("/home/cybermouse/nas/rawdata")
    """The absolute path to the local-filesystem-mounted directory where the raw data from all projects is stored on 
    the NAS (backup long-term storage destination)."""
    mesoscope_directory: Path = Path("/home/cybermouse/scanimage/mesodata")
    """The absolute path to the root ScanImagePC (mesoscope-connected PC) local-filesystem-mounted directory where all 
    mesoscope-acquired data is aggregated during acquisition."""
    harvesters_cti_path: Path = Path("/opt/mvIMPACT_Acquire/lib/x86_64/mvGenTLProducer.cti")
    """The path to the GeniCam CTI file used to connect to Harvesters-managed cameras."""


@dataclass()
class MesoscopeSheets:
    """Stores the identifiers for the Google Sheet files used by the Mesoscope-VR data acquisition system."""

    surgery_sheet_id: str = ""
    """The ID of the Google Sheet file that stores information about surgical interventions performed on the animals 
    that participate in data acquisition sessions."""
    water_log_sheet_id: str = ""
    """The ID of the Google Sheet file that stores information about water restriction and user-interaction for all 
    animals that participate in data acquisition sessions."""


@dataclass()
class MesoscopeCameras:
    """Stores the configuration parameters for the cameras used by the Mesoscope-VR system to record behavior videos."""

    face_camera_index: int = 0
    """The index of the face camera in the list of all available Harvester-managed cameras."""
    left_camera_index: int = 0
    """The index of the left body camera (from animal's perspective) in the list of all available OpenCV-managed 
    cameras."""
    right_camera_index: int = 2
    """The index of the right body camera (from animal's perspective) in the list of all available OpenCV-managed
     cameras."""
    face_camera_quantization_parameter: int = 15
    """The quantization parameter used by the face camera to encode acquired frames as video files."""
    body_camera_quantization_parameter: int = 15
    """The quantization parameter used by the left and right body cameras to encode acquired frames as video files."""
    display_face_camera_frames: bool = True
    """Determines whether to display the frames grabbed from the face camera during runtime."""
    display_body_camera_frames: bool = True
    """Determines whether to display the frames grabbed from the left and right body cameras during runtime."""


@dataclass()
class MesoscopeMicroControllers:
    """Stores the configuration parameters for the microcontrollers used by the Mesoscope-VR system."""

    actor_port: str = "/dev/ttyACM0"
    """The USB port used by the Actor Microcontroller."""
    sensor_port: str = "/dev/ttyACM1"
    """The USB port used by the Sensor Microcontroller."""
    encoder_port: str = "/dev/ttyACM2"
    """The USB port used by the Encoder Microcontroller."""
    debug: bool = False
    """Determines whether the acquisition system is running in the 'debug mode'. This mode is used during the initial 
    system calibration and testing. It should be disabled during all non-testing sessions to maximize system's 
    runtime performance."""
    minimum_break_strength_g_cm: float = 43.2047
    """The minimum torque applied by the running wheel break in gram centimeter. This is the torque the break delivers 
    at minimum operational voltage."""
    maximum_break_strength_g_cm: float = 1152.1246
    """The maximum torque applied by the running wheel break in gram centimeter. This is the torque the break delivers 
    at maximum operational voltage."""
    wheel_diameter_cm: float = 15.0333
    """The diameter of the running wheel, in centimeters."""
    lick_threshold_adc: int = 400
    """The threshold voltage, in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC), interpreted 
    as the animal's tongue contacting the sensor."""
    lick_signal_threshold_adc: int = 300
    """The minimum voltage, in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC), reported to the
    PC as a non-zero value. Voltages below this level are interpreted as 'no-lick' noise and are always pulled to 0."""
    lick_delta_threshold_adc: int = 300
    """The minimum absolute difference in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC) for 
    the change to be reported to the PC."""
    lick_averaging_pool_size: int = 1
    """The number of lick sensor readouts to average together to produce the final lick sensor readout value. Note, 
    when using a Teensy controller, this number is multiplied by the built-in analog readout averaging (default is 4).
    """
    torque_baseline_voltage_adc: int = 2046
    """The voltage level, in raw analog units measured by a 12-bit Analog-to-Digital-Converter (ADC) after the AD620 
    amplifier, that corresponds to no torque (0) readout."""
    torque_maximum_voltage_adc: int = 2750
    """The voltage level, in raw analog units measured by a 12-bit Analog-to-Digital-Converter (ADC) 
    after the AD620 amplifier, that corresponds to the absolute maximum torque detectable by the sensor."""
    torque_sensor_capacity_g_cm: float = 720.0779
    """The maximum torque detectable by the sensor, in grams centimeter (g cm)."""
    torque_report_cw: bool = True
    """Determines whether the sensor should report torque in the Clockwise (CW) direction. This direction corresponds 
    to the animal trying to move forward on the wheel."""
    torque_report_ccw: bool = True
    """Determines whether the sensor should report torque in the Counter-Clockwise (CCW) direction. This direction 
    corresponds to the animal trying to move backward on the wheel."""
    torque_signal_threshold_adc: int = 100
    """The minimum voltage, in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC), reported to the
    PC as a non-zero value. Voltages below this level are interpreted as noise and are always pulled to 0."""
    torque_delta_threshold_adc: int = 70
    """The minimum absolute difference in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC) for 
    the change to be reported to the PC."""
    torque_averaging_pool_size: int = 1
    """The number of torque sensor readouts to average together to produce the final torque sensor readout value. Note, 
    when using a Teensy controller, this number is multiplied by the built-in analog readout averaging (default is 4).
    """
    wheel_encoder_ppr: int = 8192
    """The resolution of the managed quadrature encoder, in Pulses Per Revolution (PPR). This is the number of 
    quadrature pulses the encoder emits per full 360-degree rotation."""
    wheel_encoder_report_cw: bool = False
    """Determines whether to report encoder rotation in the CW (negative) direction. This corresponds to the animal 
    moving backward on the wheel."""
    wheel_encoder_report_ccw: bool = True
    """Determines whether to report encoder rotation in the CCW (positive) direction. This corresponds to the animal 
    moving forward on the wheel."""
    wheel_encoder_delta_threshold_pulse: int = 15
    """The minimum difference, in encoder pulse counts, between two encoder readouts for the change to be reported to 
    the PC."""
    wheel_encoder_polling_delay_us: int = 500
    """The delay, in microseconds, between any two successive encoder state readouts."""
    cm_per_unity_unit: float = 10.0
    """The length of each Unity 'unit' in real-world centimeters recorded by the running wheel encoder."""
    screen_trigger_pulse_duration_ms: int = 500
    """The duration of the HIGH phase of the TTL pulse used to toggle the VR screens between ON and OFF states."""
    auditory_tone_duration_ms: int = 300
    """The time, in milliseconds, to sound the auditory tone when water rewards are delivered to the animal."""
    valve_calibration_pulse_count: int = 200
    """The number of times to cycle opening and closing (pulsing) the valve during each calibration runtime. This 
    determines how many reward deliveries are used at each calibrated time-interval to produce the average dispensed 
    water volume readout used to calibrate the valve."""
    sensor_polling_delay_ms: int = 1
    """The delay, in milliseconds, between any two successive readouts of any sensor other than the encoder. Note, the 
    encoder uses a dedicated parameter, as the encoder needs to be sampled at a higher frequency than all other sensors.
    """
    valve_calibration_data: dict[int | float, int | float] | tuple[tuple[int | float, int | float], ...] = (
        (15000, 1.10),
        (30000, 3.00),
        (45000, 6.25),
        (60000, 10.90),
    )
    """A tuple of tuples that maps water delivery solenoid valve open times, in microseconds, to the dispensed volume 
    of water, in microliters. During training and experiment runtimes, this data is used by the ValveModule to translate
    the requested reward volumes into times the valve needs to be open to deliver the desired volume of water.
    """


@dataclass()
class MesoscopeAdditionalFirmware:
    """Stores the configuration parameters for all firmware and hardware components not assembled in the Sun lab."""

    headbar_port: str = "/dev/ttyUSB0"
    """The USB port used by the HeadBar Zaber motor controllers (devices)."""
    lickport_port: str = "/dev/ttyUSB1"
    """The USB port used by the LickPort Zaber motor controllers (devices)."""
    wheel_port: str = "/dev/ttyUSB2"
    """The USB port used by the (running) Wheel Zaber motor controllers (devices)."""
    unity_ip: str = "127.0.0.1"
    """The IP address of the MQTT broker used to communicate with the Unity game engine."""
    unity_port: int = 1883
    """The port number of the MQTT broker used to communicate with the Unity game engine."""


@dataclass()
class MesoscopeSystemConfiguration(YamlConfig):
    """Stores the hardware and filesystem configuration parameters for the Mesoscope-VR data acquisition system.

    This class is specifically designed to encapsulate the configuration parameters for the Mesoscope-VR system. It
    expects the system to be configured according to the specifications outlined in the sl-experiment repository
    (https://github.com/Sun-Lab-NBB/sl-experiment) and should be used exclusively on the VRPC machine
    (main Mesoscope-VR PC).
    """

    name: str = str(AcquisitionSystems.MESOSCOPE_VR)
    """Stores the descriptive name of the data acquisition system."""
    paths: MesoscopePaths = field(default_factory=MesoscopePaths)
    """Stores the filesystem configuration parameters for the Mesoscope-VR data acquisition system."""
    sheets: MesoscopeSheets = field(default_factory=MesoscopeSheets)
    """Stores the IDs of Google Sheets used by the Mesoscope-VR data acquisition system."""
    cameras: MesoscopeCameras = field(default_factory=MesoscopeCameras)
    """Stores the configuration parameters for the cameras used by the Mesoscope-VR system to record behavior videos."""
    microcontrollers: MesoscopeMicroControllers = field(default_factory=MesoscopeMicroControllers)
    """Stores the configuration parameters for the microcontrollers used by the Mesoscope-VR system."""
    additional_firmware: MesoscopeAdditionalFirmware = field(default_factory=MesoscopeAdditionalFirmware)
    """Stores the configuration parameters for all firmware and hardware components not assembled in the Sun lab."""

    def __post_init__(self) -> None:
        """Ensures that variables converted to different types for storage purposes are always set to expected types
        upon class instantiation."""

        # Converts all paths loaded as strings to Path objects used inside the library
        self.paths.google_credentials_path = Path(self.paths.google_credentials_path)
        self.paths.root_directory = Path(self.paths.root_directory)
        self.paths.server_storage_directory = Path(self.paths.server_storage_directory)
        self.paths.server_working_directory = Path(self.paths.server_working_directory)
        self.paths.nas_directory = Path(self.paths.nas_directory)
        self.paths.mesoscope_directory = Path(self.paths.mesoscope_directory)
        self.paths.harvesters_cti_path = Path(self.paths.harvesters_cti_path)

        # Converts valve_calibration data from a dictionary to a tuple of tuples format
        if not isinstance(self.microcontrollers.valve_calibration_data, tuple):
            self.microcontrollers.valve_calibration_data = tuple(
                (k, v) for k, v in self.microcontrollers.valve_calibration_data.items()
            )

        # Verifies the contents of the valve calibration data loaded from the config file.
        valve_calibration_data = self.microcontrollers.valve_calibration_data
        if not all(
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], (int | float))
            and isinstance(item[1], (int | float))
            for item in valve_calibration_data
        ):
            message = (
                f"Unable to initialize the MesoscopeSystemConfiguration class. Expected each item under the "
                f"'valve_calibration_data' field of the Mesoscope-VR acquisition system configuration .yaml file to be "
                f"a tuple of two integer or float values, but instead encountered {valve_calibration_data} with at "
                f"least one incompatible element."
            )
            console.error(message=message, error=TypeError)

    def save(self, path: Path) -> None:
        """Saves class instance data to disk as a .yaml file.

        This method converts certain class variables to yaml-safe types (for example, Path objects -> strings) and
        saves class data to disk as a .yaml file. The method is intended to be used solely by the
        create_system_configuration_file() function and should not be called from any other context.

        Args:
            path: The path to the .yaml file to save the data to.
        """

        # Copies instance data to prevent it from being modified by reference when executing the steps below
        original = copy.deepcopy(self)

        # Converts all Path objects to strings before dumping the data, as .yaml encoder does not properly recognize
        # Path objects
        original.paths.google_credentials_path = str(original.paths.google_credentials_path)  # type: ignore
        original.paths.root_directory = str(original.paths.root_directory)  # type: ignore
        original.paths.server_storage_directory = str(original.paths.server_storage_directory)  # type: ignore
        original.paths.server_working_directory = str(original.paths.server_working_directory)  # type: ignore
        original.paths.nas_directory = str(original.paths.nas_directory)  # type: ignore
        original.paths.mesoscope_directory = str(original.paths.mesoscope_directory)  # type: ignore
        original.paths.harvesters_cti_path = str(original.paths.harvesters_cti_path)  # type: ignore

        # Converts valve calibration data into dictionary format
        if isinstance(original.microcontrollers.valve_calibration_data, tuple):
            original.microcontrollers.valve_calibration_data = {
                k: v for k, v in original.microcontrollers.valve_calibration_data
            }

        # Saves the data to the YAML file
        original.to_yaml(file_path=path)


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

    # If the directory specified by the 'path' does not exist, generates the specified directory tree. As part of this
    # process, also generate the precursor server_credentials.yaml file to use for accessing the remote server used to
    # store project data.
    if not path.exists():
        message = (
            f"The specified working directory ({path}) does not exist. Generating the directory at the "
            f"specified path..."
        )
        console.echo(message=message, level=LogLevel.INFO)

    # Resolves the path to the static .txt file used to store the path to the system configuration file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("working_directory_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Ensures that the input path's directory exists
    ensure_directory_exists(path)

    # Replaces the contents of the working_directory_path.txt file with the provided path
    with path_file.open("w") as f:
        f.write(str(path))

    if not path.joinpath("user_credentials.yaml").exists():
        message = (
            f"Unable to locate the 'user_credentials.yaml' file in the Sun lab working directory {path}. Call the "
            f"'sl-configure server' CLI command to create the user server access credentials file. Note, all users "
            f"need to have a valid user credentials file to work with the data stored on the remote server."
        )
        console.echo(message=message, level=LogLevel.WARNING)

    if not path.joinpath("service_credentials.yaml").exists():
        message = (
            f"Unable to locate the 'service_credentials.yaml' file in the Sun lab working directory {path}. If you "
            f"intend to work with the remote compute server in the 'service' mode, use the 'sl-configure server -s' "
            f"CLI command to create the service server access credentials file. Note, most lab users should skip this "
            f"step, all intended interactions with teh server can be carried out via the user access mode."
        )
        console.echo(message=message, level=LogLevel.WARNING)


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
    # Uses appdirs to locate the user data directory and resolve the path to the configuration file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("working_directory_path.txt")

    # If the cache file or the Sun lab data directory does not exist, aborts with an error
    if not path_file.exists():
        message = (
            "Unable to resolve the path to the local Sun lab working directory, as local machine does not have a "
            "configured working directory. Configure the local working directory by using the 'sl-configure directory' "
            "CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Once the location of the path storage file is resolved, reads the file path from the file
    with path_file.open() as f:
        working_directory = Path(f.read().strip())

    # If the configuration file does not exist, also aborts with an error
    if not working_directory.exists():
        message = (
            "Unable to resolve the path to the local Sun lab working directory, as the directory pointed by the path "
            "stored in the Sun lab data directory does not exist. Configure a new working directory by using the "
            "'sl-configure directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Returns the path to the working directory
    return working_directory


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

    # Gets the path to the local working directory.
    working_directory = get_working_directory()

    # Resolves the paths to the credential files.
    service_path = working_directory.joinpath("service_credentials.yaml")
    user_path = working_directory.joinpath("user_credentials.yaml")

    # If the caller requires the service account, evaluates the service credentials file.
    if service:
        # Ensures that the credentials' file exists.
        if not service_path.exists():
            message = (
                f"Unable to locate the 'service_credentials.yaml' file in the Sun lab working directory "
                f"{service_path}. If you intend to work with the remote compute server in the 'service' mode, use the "
                f"'sl-configure server -s' CLI command to create the service server access credentials file. Note, "
                f"most lab users should skip this step, all intended interactions with teh server can be carried out "
                f"via the user access mode."
            )
            console.error(message=message, error=FileNotFoundError)
            raise FileNotFoundError(message)  # Fallback to appease mypy, should not be reachable

        credentials: ServerCredentials = ServerCredentials.from_yaml(file_path=service_path)  # type: ignore

        # If the service account is not configured, aborts with an error.
        if credentials.username == "YourNetID" or credentials.password == "YourPassword":
            message = (
                f"The 'service_credentials.yaml' file appears to be unconfigured or contains placeholder credentials. "
                f"Use the 'sl-configure server -s' CLI command to reconfigure the server credentials file."
            )
            console.error(message=message, error=ValueError)
            raise ValueError(message)  # Fallback to appease mypy, should not be reachable

        # If the service account is configured, returns the path to the service credentials file to caller
        else:
            message = f"Server access credentials: Resolved. Using the service {credentials.username} account."
            console.echo(message=message, level=LogLevel.SUCCESS)
            return service_path

    else:
        if not user_path.exists():
            message = (
                f"Unable to locate the 'user_credentials.yaml' file in the Sun lab working directory {user_path}. Call "
                f"the 'sl-configure server' CLI command to create the user server access credentials file. Note, "
                f"all users need to have a valid user credentials file to work with the data stored on the remote "
                f"server."
            )
            console.error(message=message, error=FileNotFoundError)
            raise FileNotFoundError(message)  # Fallback to appease mypy, should not be reachable

        # Otherwise, evaluates the user credentials file.
        credentials: ServerCredentials = ServerCredentials.from_yaml(file_path=user_path)  # type: ignore

        # If the user account is not configured, aborts with an error.
        if credentials.username == "YourNetID" or credentials.password == "YourPassword":
            message = (
                f"The 'user_credentials.yaml' file appears to be unconfigured or contains placeholder credentials. "
                f"Use the 'sl-configure server' CLI command to reconfigure the server credentials file."
            )
            console.error(message=message, error=ValueError)
            raise ValueError(message)  # Fallback to appease mypy, should not be reachable

        # Otherwise, returns the path to the user credentials file to caller
        message = f"Server access credentials: Resolved. Using the {credentials.username} account."
        console.echo(message=message, level=LogLevel.SUCCESS)
        return user_path


# Maps supported file names to configuration classes. This is used when loading the configuration data into memory.
_supported_configuration_files = {
    "mesoscope-vr_configuration.yaml": MesoscopeSystemConfiguration,
}


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

    # Resolves the path to the local Sun lab working directory.
    directory = get_working_directory()

    # Removes any existing configuration files to ensure only one configuration exists on each configured machine
    existing_configs = tuple(directory.glob("*_configuration.yaml"))
    for config_file in existing_configs:
        console.echo(f"Removing existing configuration file: {config_file.name}...")
        config_file.unlink()

    if system == AcquisitionSystems.MESOSCOPE_VR:
        # Creates the precursor configuration file for the mesoscope-vr system
        configuration = MesoscopeSystemConfiguration()
        configuration_path = directory.joinpath(f"{system}_configuration.yaml")
        configuration.save(path=configuration_path)

        # Forces the user to finish configuring the system by editing the parameters inside the configuration file
        message = (
            f"Mesoscope-VR data acquisition system configuration file: Saved to {configuration_path}. Edit the "
            f"default parameters inside the configuration file to finish configuring the system."
        )
        console.echo(message=message, level=LogLevel.SUCCESS)
        input("Enter anything to continue...")

    # If the input acquisition system is not recognized, raises a ValueError
    else:
        systems = tuple(AcquisitionSystems)
        message = (
            f"Unable to generate the system configuration file for the acquisition system '{system}'. The specified "
            f"acquisition system is not supported (not recognized). Currently, only the following acquisition systems "
            f"are supported: {', '.join(systems)}."
        )
        console.error(message=message, error=ValueError)


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

    # Resolves the path to the local Sun lab working directory.
    directory = get_working_directory()

    # Finds all configuration files stored in the local working directory
    config_files = tuple(directory.glob("*_configuration.yaml"))

    # Ensures exactly one configuration file exists in the working directory
    if len(config_files) != 1:
        file_names = [f.name for f in config_files]
        message = (
            f"Expected a single dta acquisition system configuration file to be found inside the local Sun lab working "
            f"directory ({directory}), but found {len(config_files)} files ({', '.join(file_names)}). Use the "
            f"'sl-configure system' CLI command to reconfigure the local machine to only contain a single data "
            f"acquisition system configuration file."
        )
        console.error(message=message, error=FileNotFoundError)
        raise FileNotFoundError(message)  # Fallback to appease mypy, should not be reachable

    # Gets the single configuration file
    configuration_file = config_files[0]
    file_name = configuration_file.name

    # Ensures that the file name is supported
    if file_name not in _supported_configuration_files:
        message = (
            f"The data acquisition system configuration file '{file_name}' stored in teh local Sun lab working "
            f"directory is not recognized. Use one of the supported configuration files: "
            f"{', '.join(_supported_configuration_files.keys())}."
        )
        console.error(message=message, error=ValueError)
        raise ValueError(message)  # Fallback to appease mypy, should not be reachable

    # Loads and return the configuration data
    configuration_class = _supported_configuration_files[file_name]
    return configuration_class.from_yaml(file_path=configuration_file)  # type: ignore
