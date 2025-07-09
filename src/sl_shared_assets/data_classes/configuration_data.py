"""This module provides classes used to configure data acquisition and processing runtimes in the Sun lab. All lab
projects use classes from this module to configure experiment runtimes and determine how to interact with the
particular data acquisition and runtime management system (hardware) they run on."""

import copy
from pathlib import Path
from dataclasses import field, dataclass

import appdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig


@dataclass()
class ExperimentState:
    """Encapsulates the information used to set and maintain the desired experiment and system state.

    Broadly, each experiment runtime can be conceptualized as a two state-system. The first state is that of the
    experimental task, which reflects the behavior goal, the rules for achieving the goal, and the reward for
    achieving the goal. The second state is that of the data acquisition and experiment control system, which is a
    snapshot of all hardware module states that make up the system that acquires the data and controls the task
    environment. Overall, experiment state is about 'what the animal is doing', while the system state is about
    'what the hardware is doing'.

    Note:
        This class is acquisition-system-agnostic. It can be used to define the ExperimentConfiguration class for any
        valid data acquisition system.
    """

    experiment_state_code: int
    """The integer code of the experiment state. Experiment states do not have a predefined meaning, Instead, each 
    project is expected to define and follow its own experiment state code mapping. Typically, the experiment state 
    code is used to denote major experiment stages, such as 'baseline', 'task', 'cooldown', etc. Note, the same 
    experiment state code can be used by multiple sequential ExperimentState instances to change the system states 
    while maintaining the same experiment state."""
    system_state_code: int
    """One of the supported system state-codes. Note, the meaning of each system state code depends on the specific 
    data acquisition and experiment control system used by the project. For example, projects using the 'mesoscope-vr' 
    system currently support two system state codes: REST (1) and RUN (2)."""
    state_duration_s: float
    """The time, in seconds, to maintain the current combination of the experiment and system states."""
    initial_guided_trials: int
    """Specifies the number of trials (laps) at the onset of the experiment state, for which lick guidance will be 
    automatically enabled. Specifically, if the experiment state supports running linearized Virtual Reality track, the 
    system will enable lick guidance for this many trials at the beginning of the experiment state and automatically 
    disable it for the following trials."""
    failed_trial_threshold: int
    """Specifies the number of failed (non-rewarded) non-guided trials (laps), after which the system will re-enable 
    guidance for the 'recovery_guided_trials' number of following trials. For this to take effect, the trials must be 
    failed this many times in a row."""
    recovery_guided_trials: int
    """Specifies the number of trials (laps) for which the system will re-enable lick guidance, when the animal 
    repeatedly fails 'failed_trial_threshold' number of trials. This field works similar to the 'initial_guided_trials' 
    field, but is triggered by repeated performance failures, rather than experiment state onset. After the animal 
    runs this many guided trials, the system will automatically disable guidance for the following trials."""


@dataclass()
class TrialCueSequence:
    """Encapsulates information about the Virtual Reality (VR) wall cue sequence experienced by the animal as part of
    the given trial.

    All Virtual Reality environments can be broadly conceptualized as repeating motifs (sequences) of wall cues. Since
    some experimental tasks can use multiple cue sequences as part of the same experiment session, multiple instances of
    this class can be used to specify supported trial structures. The information stored in this class instance is used
    during behavior data parsing to assign trial information to data collected from various sources.
    """

    cue_sequence: list[int]
    """Specifies the sequence of wall cues experienced by the animal while running this trial."""
    trial_length_unity_unit: float
    """The length of the trial cue sequence, in Unity units."""
    trial_length_cm: float
    """The length of the trial cue sequence in centimeters."""


# noinspection PyArgumentList
@dataclass()
class MesoscopeExperimentConfiguration(YamlConfig):
    """Stores the configuration of a single experiment runtime that uses the Mesoscope_VR data acquisition system.

    Primarily, this includes the sequence of experiment and system states that defines the flow of the experiment
    runtime. During runtime, the main runtime control function traverses the sequence of states stored in this class
    instance start-to-end in the exact order specified by the user. Together with custom Unity projects that define
    the task logic (how the system responds to animal interactions with the VR system) this class allows flexibly
    implementing a wide range of experiments using the Mesoscope-VR system.

    Each project should define one or more experiment configurations and save them as .yaml files inside the project
    'configuration' folder. The name for each configuration file is defined by the user and is used to identify and load
    the experiment configuration when 'sl-experiment' CLI command exposed by the sl-experiment library is executed.

    Notes:
        This class is designed exclusively for the Mesoscope-VR system. Any other system needs to define a separate
        ExperimentConfiguration class to specify its experiment runtimes and additional data.
    """

    cue_map: dict[int, float] = field(default_factory=lambda: {0: 30.0, 1: 30.0, 2: 30.0, 3: 30.0, 4: 30.0})
    """A dictionary that maps each integer-code associated with a wall cue used in the Virtual Reality experiment 
    environment to its length in real-world centimeters. It is used to map each VR cue to the distance the animal needs
    to travel to fully traverse the wall cue region from start to end."""
    experiment_states: dict[str, ExperimentState] = field(
        default_factory=lambda: {
            "baseline": ExperimentState(
                experiment_state_code=1,
                system_state_code=1,
                state_duration_s=30,
                initial_guided_trials=0,
                failed_trial_threshold=0,
                recovery_guided_trials=0,
            ),
            "experiment": ExperimentState(
                experiment_state_code=2,
                system_state_code=2,
                state_duration_s=120,
                initial_guided_trials=3,
                failed_trial_threshold=6,
                recovery_guided_trials=3,
            ),
            "cooldown": ExperimentState(
                experiment_state_code=3,
                system_state_code=1,
                state_duration_s=15,
                initial_guided_trials=1000000,
                failed_trial_threshold=0,
                recovery_guided_trials=0,
            ),
        }
    )
    """A dictionary that uses human-readable state-names as keys and ExperimentState instances as values. Each 
    ExperimentState instance represents a phase of the experiment."""
    trial_structures: dict[str, TrialCueSequence] = field(
        default_factory=lambda: {
            "circular 4 cue": TrialCueSequence(
                cue_sequence=[0, 1, 0, 2, 0, 3, 0, 4], trial_length_unity_unit=24.0, trial_length_cm=240.0
            )
        }
    )
    """A dictionary that maps human-readable trial structure names as keys and TrialCueSequence instances as values. 
    Each TrialCueSequence instance represents a specific VR wall cue sequence used by a given trial structure."""


@dataclass()
class MesoscopePaths:
    """Stores the filesystem configuration parameters for the Mesoscope-VR data acquisition system."""

    server_credentials_path: Path = Path("/media/Data/Experiments/server_credentials.yaml")
    """
    The path to the locally stored .YAML file that contains the credentials for accessing the BioHPC server machine. 
    While the filesystem of the server machine should already be mounted to the local machine via SMB or equivalent 
    protocol, this data is used to establish SSH connection to the server and start newly acquired data processing 
    after it is transferred to the server. This allows data acquisition, preprocessing, and processing to be controlled 
    by the same runtime and prevents unprocessed data from piling up on the server.
    """
    google_credentials_path: Path = Path("/media/Data/Experiments/sl-surgery-log-0f651e492767.json")
    """
    The path to the locally stored .JSON file that contains the service account credentials used to read and write 
    Google Sheet data. This is used to access and work with various Google Sheet files used by Sun lab projects, 
    eliminating the need to manually synchronize the data in various Google sheets and other data files.
    """
    root_directory: Path = Path("/media/Data/Experiments")
    """The absolute path to the directory where all projects are stored on the local host-machine (VRPC)."""
    server_storage_directory: Path = Path("/home/cybermouse/server/storage/sun_data")
    """The absolute path to the directory where the raw data from all projects is stored on the BioHPC server. 
    This directory should be locally accessible (mounted) using a network sharing protocol, such as SMB."""
    server_working_directory: Path = Path("/home/cybermouse/server/workdir/sun_data")
    """The absolute path to the directory where the processed data from all projects is stored on the BioHPC 
    server. This directory should be locally accessible (mounted) using a network sharing protocol, such as SMB."""
    nas_directory: Path = Path("/home/cybermouse/nas/rawdata")
    """The absolute path to the directory where the raw data from all projects is stored on the Synology NAS. 
    This directory should be locally accessible (mounted) using a network sharing protocol, such as SMB."""
    mesoscope_directory: Path = Path("/home/cybermouse/scanimage/mesodata")
    """The absolute path to the root ScanImagePC (mesoscope-connected PC) directory where all mesoscope-acquired data 
    is aggregated during acquisition runtime. This directory should be locally accessible (mounted) using a network 
    sharing protocol, such as SMB."""
    harvesters_cti_path: Path = Path("/opt/mvIMPACT_Acquire/lib/x86_64/mvGenTLProducer.cti")
    """The path to the GeniCam CTI file used to connect to Harvesters-managed cameras."""


@dataclass()
class MesoscopeSheets:
    """Stores the IDs of Google Sheets used by the Mesoscope-VR data acquisition system."""

    surgery_sheet_id: str = ""
    """The ID of the Google Sheet file that stores information about surgical interventions performed on all animals 
    participating in each lab project. This log sheet is used to parse and write the surgical intervention data for 
    each animal into every runtime session raw_data folder, so that the surgery data is always kept together with the 
    rest of the training and experiment data."""
    water_log_sheet_id: str = ""
    """The ID of the Google Sheet file that stores information about water restriction (and behavior tracker) 
    information for all animals participating in the managed project. This is used to synchronize the information 
    inside the water restriction log with the state of the animal at the end of each training or experiment session.
    """


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
    """The quantization parameter used by the face camera to encode acquired frames as video files. This controls how
    much data is discarded when encoding each video frame, directly contributing to the encoding speed, resultant video 
    file size and video quality."""
    body_camera_quantization_parameter: int = 15
    """SThe quantization parameter used by the left and right body cameras to encode acquired frames as video files.
    See 'face_camera_quantization_parameter' field for more information on what this parameter does."""
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
    """Determines whether to run the managed acquisition system in the 'debug mode'. This mode should be disabled 
    during most runtimes. It is used during initial system calibration and testing and prints a lot of generally 
    redundant information into the terminal."""
    mesoscope_ttl_pulse_duration_ms: int = 10
    """The duration of the HIGH phase of all outgoing TTL pulses that target the Mesoscope (enable or disable mesoscope
    frame acquisition), in milliseconds."""
    minimum_break_strength_g_cm: float = 43.2047
    """The minimum torque applied by the running wheel break in gram centimeter. This is the torque the break delivers 
    at minimum voltage (break is disabled)."""
    maximum_break_strength_g_cm: float = 1152.1246
    """The maximum torque applied by the running wheel break in gram centimeter. This is the torque the break delivers 
    at maximum voltage (break is fully engaged)."""
    wheel_diameter_cm: float = 15.0333
    """The diameter of the running wheel connected to the break and torque sensor, in centimeters."""
    lick_threshold_adc: int = 850
    """The threshold voltage, in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC), interpreted 
    as the animal's tongue contacting the sensor. Note, 12-bit ADC only supports values between 0 and 4095, so setting 
    the threshold above 4095 will result in no licks being reported to Unity."""
    lick_signal_threshold_adc: int = 300
    """The minimum voltage, in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC), reported to the
    PC as a non-zero value. Voltages below this level are interpreted as 'no-lick' noise and are always pulled to 0."""
    lick_delta_threshold_adc: int = 300
    """The minimum absolute difference in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC) for 
    the change to be reported to the PC. This is used to prevent reporting repeated non-lick or lick readouts to the 
    PC, conserving communication bandwidth."""
    lick_averaging_pool_size: int = 10
    """The number of lick sensor readouts to average together to produce the final lick sensor readout value."""
    torque_baseline_voltage_adc: int = 2046
    """The voltage level, in raw analog units measured by 3.3v Analog-to-Digital-Converter (ADC) at 12-bit resolution 
    after the AD620 amplifier, that corresponds to no (0) torque readout. Usually, for a 3.3v ADC, this would be 
    around 2046 (the midpoint, ~1.65 V)."""
    torque_maximum_voltage_adc: int = 2750
    """The voltage level, in raw analog units measured by 3.3v Analog-to-Digital-Converter (ADC) at 12-bit resolution 
    after the AD620 amplifier, that corresponds to the absolute maximum torque detectable by the sensor. At most,
    this value can be 4095 (~3.3 V)."""
    torque_sensor_capacity_g_cm: float = 720.0779
    """The maximum torque detectable by the sensor, in grams centimeter (g cm)."""
    torque_report_cw: bool = True
    """Determines whether the sensor should report torque in the Clockwise (CW) direction. This direction corresponds 
    to the animal trying to move the wheel backward."""
    torque_report_ccw: bool = True
    """Determines whether the sensor should report torque in the Counter-Clockwise (CCW) direction. This direction 
    corresponds to the animal trying to move the wheel forward."""
    torque_signal_threshold_adc: int = 100
    """The minimum voltage, in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC), reported to the
    PC as a non-zero value. Voltages below this level are interpreted as noise and are always pulled to 0."""
    torque_delta_threshold_adc: int = 70
    """The minimum absolute difference in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC) for 
    the change to be reported to the PC. This is used to prevent reporting repeated static torque readouts to the 
    PC, conserving communication bandwidth."""
    torque_averaging_pool_size: int = 10
    """The number of torque sensor readouts to average together to produce the final torque sensor readout value."""
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
    the PC. This is used to prevent reporting idle readouts and filter out sub-threshold noise."""
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
    """Stores the hardware and filesystem configuration parameters for the Mesoscope-VR data acquisition system used in
    the Sun lab.

    This class is specifically designed to encapsulate the configuration parameters for the Mesoscope-VR system. It
    expects the system to be configured according to the specifications available from the sl_experiment repository
    (https://github.com/Sun-Lab-NBB/sl-experiment) and should be used exclusively by the VRPC machine
    (main Mesoscope-VR PC).

    Notes:
        Each SystemConfiguration class is uniquely tied to a specific hardware configuration used in the lab. This
        class will only work with the Mesoscope-VR system. Any other data acquisition and runtime management system in
        the lab should define its own SystemConfiguration class to specify its own hardware and filesystem configuration
        parameters.
    """

    name: str = "mesoscope-vr"
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
        self.paths.server_credentials_path = Path(self.paths.server_credentials_path)
        self.paths.google_credentials_path = Path(self.paths.google_credentials_path)
        self.paths.root_directory = Path(self.paths.root_directory)
        self.paths.server_storage_directory = Path(self.paths.server_storage_directory)
        self.paths.server_working_directory = Path(self.paths.server_working_directory)
        self.paths.nas_directory = Path(self.paths.nas_directory)
        self.paths.mesoscope_directory = Path(self.paths.mesoscope_directory)
        self.paths.harvesters_cti_path = Path(self.paths.harvesters_cti_path)

        # Converts valve_calibration data from dictionary to a tuple of tuples format
        if not isinstance(self.microcontrollers.valve_calibration_data, tuple):
            self.microcontrollers.valve_calibration_data = tuple(
                (k, v) for k, v in self.microcontrollers.valve_calibration_data.items()
            )

        # Verifies the contents of the valve calibration data loaded from the config file.
        valve_calibration_data = self.microcontrollers.valve_calibration_data
        if not all(
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], (int, float))
            and isinstance(item[1], (int, float))
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
        """Saves class instance data to disk as a 'mesoscope_system_configuration.yaml' file.

        This method converts certain class variables to yaml-safe types (for example, Path objects -> strings) and
        saves class data to disk as a .yaml file. The method is intended to be used solely by the
        set_system_configuration_file() function and should not be called from any other context.

        Args:
            path: The path to the .yaml file to save the data to.
        """

        # Copies instance data to prevent it from being modified by reference when executing the steps below
        original = copy.deepcopy(self)

        # Converts all Path objects to strings before dumping the data, as .yaml encoder does not properly recognize
        # Path objects
        original.paths.server_credentials_path = str(original.paths.server_credentials_path)  # type: ignore
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


# A dictionary that maps the file names for supported data acquisition systems to their configuration classes. This
# dictionary always contains all data acquisition systems used in the lab.
_supported_configuration_files = {"mesoscope_system_configuration.yaml": MesoscopeSystemConfiguration}


def set_system_configuration_file(path: Path) -> None:
    """Sets the system configuration .yaml file specified by the input path as the default system configuration file for
    the managed machine (PC).

    This function is used to initially configure or override the existing configuration of any data acquisition system
    used in the lab. The path to the configuration file is stored inside the user's data directory, so that all
    Sun lab libraries can automatically access that information during every runtime. Since the storage directory is
    typically hidden and varies between OSes and machines, this function provides a convenient way for setting that
    path without manually editing the storage cache.

    Notes:
        If the input path does not point to an existing file, but the file name and extension are correct, the function
        will automatically generate a default SystemConfiguration class instance and save it under the specified path.

        A data acquisition system can include multiple machines (PCs). However, the configuration file is typically
        only present on the 'main' machine that manages all runtimes.

    Args:
        path: The path to the new system configuration file to be used by the local data acquisition system (PC).

    Raises:
        ValueError: If the input path is not a valid system configuration file or does not use a supported data
            acquisition system name.
    """

    # Prevents setting the path to an invalid file.
    if path.name not in _supported_configuration_files.keys():
        message = (
            f"Unable to set the input path {path} as the default system configuration file path. The input path has "
            f"to point to a configuration file ending with a '.yaml' extension and using one of the supported system "
            f"names: {', '.join(_supported_configuration_files.keys())}."
        )
        console.error(message=message, error=ValueError)

    # If the configuration file specified by the 'path' does not exist, generates a default SystemConfiguration instance
    # and saves it to the specified path.
    if not path.exists():
        precursor = _supported_configuration_files[path.name]()  # Instantiates default class instance
        precursor.save(path=path)
        message = (
            f"The file specified by the input system configuration path {path} does not exist. Generating and saving "
            f"the default system configuration class instance to the specified path."
        )
        console.echo(message=message, level=LogLevel.WARNING)

    # Resolves the path to the static .txt file used to store the path to the system configuration file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("configuration_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Ensures that the input path's directory exists
    ensure_directory_exists(path)

    # Replaces the contents of the configuration_path.txt file with the provided path
    with open(path_file, "w") as f:
        f.write(str(path))


def get_system_configuration_data() -> MesoscopeSystemConfiguration:
    """Resolves the path to the local system configuration file and loads the system configuration data.

    This service function is used by all Sun lab data acquisition runtimes to load the system configuration data from
    the shared configuration file. It supports resolving and returning the data for all data acquisition systems used
    in the lab.

    Returns:
        The initialized SystemConfiguration class instance for the local acquisition system that stores the loaded
        configuration parameters.

    Raises:
        FileNotFoundError: If the local machine does not have the Sun lab data directory, or the system configuration
            file does not exist.
    """
    # Uses appdirs to locate the user data directory and resolve the path to the configuration file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("configuration_path.txt")

    # If the cache file or the Sun lab data directory do not exist, aborts with an error
    if not path_file.exists():
        message = (
            "Unable to resolve the path to the local system configuration file, as local machine does not have the "
            "Sun lab data directory. Generate the local configuration file and Sun lab data directory by calling the "
            "'sl-create-system-config' CLI command and rerun the command that produced this error."
        )
        console.error(message=message, error=FileNotFoundError)

    # Once the location of the path storage file is resolved, reads the file path from the file
    with open(path_file, "r") as f:
        configuration_file = Path(f.read().strip())

    # If the configuration file does not exist, also aborts with an error
    if not configuration_file.exists():
        message = (
            "Unable to resolve the path to the local system configuration file, as the file pointed by the path stored "
            "in Sun lab data directory does not exist. Generate a new local configuration file by calling the "
            "'sl-create-system-config' CLI command and rerun the command that produced this error."
        )
        console.error(message=message, error=FileNotFoundError)

    # Loads the data stored inside the .yaml file into the class instance that matches the file name and returns the
    # instantiated class to caller
    file_name = configuration_file.name
    return _supported_configuration_files[file_name].from_yaml(file_path=configuration_file)  # type: ignore
