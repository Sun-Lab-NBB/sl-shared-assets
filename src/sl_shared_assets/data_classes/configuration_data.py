"""This module provides classes used to configure data acquisition and processing runtimes in the Sun lab. All lab
projects use classes from this library to configure experiment runtimes and determine how to interact with the
particular data acquisition and runtime management system used by the project."""

import copy
from pathlib import Path
from dataclasses import field, dataclass

import appdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig


def replace_configuration_path(path: Path) -> None:
    """Replaces the path to the acquisition system configuration file used by all data acquisition pipelines that run on
    the local machine.

    The first time a data acquisition runtime starts on a new machine, it asks the user to provide the path to the
    system configuration parameters stored as a .yaml file. This path is then stored inside the default user data
    directory as .txt file to be reused for all future runtimes. Specifically, all future runtimes check the user data
    directory and, if it contains the path to the system configuration file(s), load the system configuration data from
    that file. To support replacing this path without searching for the user data directory, which is usually hidden,
    this function finds and updates the contents of the .txt file.

    Args:
        path: The path to the new directory where to store the system configuration .yaml file.
    """
    # Resolves the path to the static .txt file used to store the local path to the system configuration files
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("configuration_directory.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Ensures that the input root directory exists
    ensure_directory_exists(path)

    # Replaces the contents of the configuration_directory.txt file with the provided path
    with open(path_file, "w") as f:
        f.write(str(path))


def _get_configuration_path() -> Path:
    """Resolves and returns the path to the local sun lab system configuration directory.

    If the directory does not exist, creates the directory at the path specified by the user.
    """
    # Uses appdirs to locate the user data directory and resolve the path to the configuration directory
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("configuration_directory.txt")

    # If the configuration directory path file does not exist, prompts the user to designate a configuration directory.
    if not path_file.exists():
        # Uses console input prompt to ask the user for the configuration directory path
        message = (
            "Unable to resolve the path to the local system configuration directory. Provide the absolute path to the "
            "directory that stores all Sun lab system configuration files, such as mesoscope_system_configuration.yaml."
        )
        # noinspection PyTypeChecker
        console.echo(message=message, level=LogLevel.WARNING)
        config_path = Path(input("System configuration directory path: "))

        # Generates the 'configuration_directory.txt' file and saves the user-provided path to that file
        replace_configuration_path(path=config_path)

    # Once the location of the path storage file is resolved, reads the root path from the file
    with open(path_file, "r") as f:
        configuration_directory = Path(f.read().strip())
    return configuration_directory


@dataclass()
class ExperimentState:
    """Encapsulates the information used to set and maintain the desired experiment and system state.

    Broadly, each experiment runtime can be conceptualized as two state-systems. The first state is that of the
    experimental task, which reflects the behavior goal, the rules for achieving the goal, and the reward for
    achieving the goal. The second state is that of the data acquisition and experiment control system, which is a
    snapshot of all hardware module states that make up the system that acquires the data and controls the task
    environment. In simpler words, experiment state is about 'what the animal is doing', while the system state is
    about 'what the hardware is doing'.

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
    data acquisition and experiment control system used by the project. For example, projects using the Mesoscope-VR 
    system currently support two system state codes: REST (1) and RUN (2)."""
    state_duration_s: float
    """The time, in seconds, to maintain the current combination of the experiment and system states."""


# noinspection PyArgumentList
@dataclass()
class MesoscopeExperimentConfiguration(YamlConfig):
    """Stores the configuration of a single experiment runtime that uses the Mesoscope_VR system.

    Primarily, this includes the sequence of experiment and system states that defines the flow of the experiment
    runtime. During runtime, the main runtime control function traverses the sequence of states stored in this class
    instance start-to-end in the exact order specified by the user. Together with custom Unity projects that define
    the task logic (how the system responds to animal interactions with the VR system) this class allows flexibly
    implementing a wide range of experiments using the Mesoscope-VR system.

    Each project should define one or more experiment configurations and save them as .yaml files inside the project
    'configuration' folder. The name for each configuration file is defined by the user and is used to identify and load
    the experiment configuration when 'sl-run-experiment' CLI command exposed by the sl-experiment library is executed.

    Notes:
        This class is designed exclusively for the Mesoscope-VR system. Any other system needs to define a separate
        ExperimentConfiguration class to specify its experiment runtimes.
    """

    cue_map: dict[int, float] = field(default_factory=lambda: {0: 30.0, 1: 30.0, 2: 30.0, 3: 30.0, 4: 30.0})
    """A dictionary that maps each integer-code associated with a wall cue used in the Virtual Reality experiment 
    environment to its length in real-world centimeters. It is used to map each VR cue to the distance the animal needs
    to travel to fully traverse the wall cue region from start to end."""
    experiment_states: dict[str, ExperimentState] = field(
        default_factory=lambda: {
            "baseline": ExperimentState(experiment_state_code=1, system_state_code=1, state_duration_s=30),
            "experiment": ExperimentState(experiment_state_code=2, system_state_code=2, state_duration_s=120),
            "cooldown": ExperimentState(experiment_state_code=3, system_state_code=1, state_duration_s=15),
        }
    )
    """A dictionary that uses human-readable state-names as keys and ExperimentState instances as values. Each 
    ExperimentState instance represents a phase of the experiment."""


@dataclass()
class MesoscopeSystemConfiguration(YamlConfig):
    """Stores the hardware and filesystem configuration parameters for the Mesoscope-VR data acquisition system used in
    the Sun lab.

    This class is specifically designed to encapsulate the configuration parameters for the Mesoscope-VR system. It
    expects the system to be configured according to the specifications available from the sl_experiment repository
    (https://github.com/Sun-Lab-NBB/sl-experiment) and should be used exclusively on the VRPC.

    Notes:
        This class stores most, but not all configuration parameters of the Mesoscope-VR system components. Some
        parameters are hardcoded in the sl-experiment library code and should only be changed by experienced users
        who understand the source code of all software and firmware components that make up the Mesoscope-VR system.

        Each SystemConfiguration class is uniquely tied to a specific hardware configuration used in the lab. This
        class will only work with the Mesoscope-VR system. Any other data acquisition and runtime management system in
        the lab should define its own SystemConfiguration class to specify its own hardware and filesystem configuration
        parameters.
    """

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
    face_camera_index: int = 0
    """The index of the face camera in the list of all available Harvester-managed cameras."""
    left_camera_index: int = 0
    """The index of the left body camera (from animal's perspective) in the list of all available OpenCV-managed 
    cameras."""
    right_camera_index: int = 2
    """The index of the right body camera (from animal's perspective) in the list of all available OpenCV-managed
     cameras."""
    actor_port: str = "/dev/ttyACM0"
    """The USB port used by the Actor Microcontroller."""
    sensor_port: str = "/dev/ttyACM1"
    """The USB port used by the Sensor Microcontroller."""
    encoder_port: str = "/dev/ttyACM2"
    """The USB port used by the Encoder Microcontroller."""
    headbar_port: str = "/dev/ttyUSB0"
    """The USB port used by the HeadBar Zaber motor controllers (devices)."""
    lickport_port: str = "/dev/ttyUSB1"
    """The USB port used by the LickPort Zaber motor controllers (devices)."""
    unity_ip: str = "127.0.0.1"
    """The IP address of the MQTT broker used to communicate with the Unity game engine. This is only used during 
    experiment runtimes. Training runtimes ignore this parameter."""
    unity_port: int = 1883
    """The port number of the MQTT broker used to communicate with the Unity game engine. This is only used during
    experiment runtimes. Training runtimes ignore this parameter."""
    mesoscope_start_ttl_module_id: int = 1
    """The unique byte-code ID of the TTL module instance used to send mesoscope frame acquisition start trigger 
    signals to the ScanImagePC."""
    mesoscope_stop_ttl_module_id: int = 2
    """The unique byte-code ID of the TTL module instance used to send mesoscope frame acquisition stop trigger 
    signals to the ScanImagePC."""
    minimum_break_strength_g_cm: float = 43.2047
    """The minimum torque applied by the running wheel break in gram centimeter. This is the torque the break delivers 
    at minimum voltage (break is disabled)."""
    maximum_break_strength_g_cm: float = 1152.1246
    """The maximum torque applied by the running wheel break in gram centimeter. This is the torque the break delivers 
    at maximum voltage (break is fully engaged)."""
    wheel_diameter_cm: float = 15.0333
    """The diameter of the running wheel connected to the break and torque sensor, in centimeters."""
    lick_threshold_adc: int = 500
    """The threshold voltage, in raw analog units recorded by a 12-bit Analog-to-Digital-Converter (ADC), interpreted 
    as the animal's tongue contacting the sensor. Note, 12-bit ADC only supports values between 0 and 4095, so setting 
    the threshold above 4095 will result in no licks being reported to Unity."""
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
    wheel_encoder_ppr = 8192
    """The resolution of the managed quadrature encoder, in Pulses Per Revolution (PPR). This is the number of 
    quadrature pulses the encoder emits per full 360-degree rotation."""
    cm_per_unity_unit = 10.0
    """The length of each Unity 'unit' in real-world centimeters recorded by the running wheel encoder."""
    auditory_tone_duration_ms: int = 300
    """The time, in milliseconds, to sound the auditory tone when water rewards are delivered to the animal."""
    system_revision: str = "1.0.0"
    """Stores the revision version of the Mesoscope-VR system. This value is manually modified by lab engineers to track
    changes to the system's hardware and software components."""
    valve_calibration_data: dict[int | float, int | float] | tuple[tuple[int | float, int | float], ...] = (
        (15000, 1.75),
        (30000, 3.85),
        (45000, 7.95),
        (60000, 12.65),
    )
    """A tuple of tuples that maps water delivery solenoid valve open times, in microseconds, to the dispensed volume 
    of water, in microliters. During training and experiment runtimes, this data is used by the ValveModule to translate
    the requested reward volumes into times the valve needs to be open to deliver the desired volume of water.
    """

    @classmethod
    def load(cls) -> "MesoscopeSystemConfiguration":
        """Loads the Mesoscope-VR system configuration parameters from the 'mesoscope_system_configuration.yaml' file.

        This method is called by all training or experiment session runtimes to configure the Mesoscope-VR system for
        data acquisition. When this method is called for the first time on a new machine, it asks the user to provide
        the path to the default configuration directory, where all system configuration files will be cached in the
        future.

        Notes:
            To replace the default configuration file directory, use the `sl-reconfigure' CLI command.

        Returns:
            The initialized MesoscopeSystemConfiguration instance that stores the loaded Mesoscope-VR system
            configuration data.
        """

        # Resolves the path to the configuration directory
        configuration_directory = _get_configuration_path()

        # Resolves the path to the configuration file
        configuration_path = configuration_directory.joinpath("mesoscope_system_configuration.yaml")

        # If the configuration file does not exist creates the configuration file using default configuration
        # parameters. THis would only be the case the first time any configuration class is loaded on a new machine or
        # after changing the root configuration directory.
        if not configuration_path.exists():
            message = (
                f"Unable to load Mesoscope-VR system configuration data from disk as no "
                f"'mesoscope_system_configuration.yaml' file is found inside the root configuration directory"
                f"({configuration_directory}). Generating a precursor (default) configuration file under the "
                f"configuration directory. Edit the file to adjust the Mesoscope-VR system configuration as necessary "
                f"before proceeding further to avoid runtime errors and unexpected behavior."
            )
            # noinspection PyTypeChecker
            console.echo(message=message, level=LogLevel.WARNING)

            # Generates the default configuration class instance and dumps it as a .yaml file.
            precursor = MesoscopeSystemConfiguration()
            precursor.save(path=configuration_path)

            # Waits for the user to manually configure the newly created file.
            input(f"Enter anything to continue: ")

        # Loads the data from the YAML file and initializes the class instance.
        instance: MesoscopeSystemConfiguration = cls.from_yaml(file_path=configuration_path)  # type: ignore

        # Converts all paths loaded as strings to Path objects used inside the library
        instance.server_credentials_path = Path(instance.server_credentials_path)
        instance.google_credentials_path = Path(instance.google_credentials_path)
        instance.root_directory = Path(instance.root_directory)
        instance.server_storage_directory = Path(instance.server_storage_directory)
        instance.server_working_directory = Path(instance.server_working_directory)
        instance.nas_directory = Path(instance.nas_directory)
        instance.mesoscope_directory = Path(instance.mesoscope_directory)
        instance.harvesters_cti_path = Path(instance.harvesters_cti_path)

        # Converts valve_calibration data from dictionary to a tuple of tuples format
        if not isinstance(instance.valve_calibration_data, tuple):
            instance.valve_calibration_data = tuple((k, v) for k, v in instance.valve_calibration_data.items())

        # Returns the initialized class instance to caller
        return instance

    def save(self, path: Path) -> None:
        """Saves class instance data to disk as a 'mesoscope_system_configuration.yaml' file.

        This method is automatically used by the 'load' class method the first time a MesoscopeSystemConfiguration
        class is instantiated on a new machine. It saves the 'precursor' configuration class instance to the
        Sun lab configuration directory as a .yaml file. This method is also used by the SessionData class to save
        a snapshot of the acquisition system configuration to the 'raw_data' directory of each newly created session.

        Args:
            path: The path to the .yaml file to save the data to.
        """

        # Copies instance data to prevent it from being modified by reference when executing the steps below
        original = copy.deepcopy(self)

        # Converts all Path objects to strings before dumping the data, as .yaml encoder does not properly recognize
        # Path objects
        original.server_credentials_path = str(original.server_credentials_path)  # type: ignore
        original.google_credentials_path = str(original.google_credentials_path)  # type: ignore
        original.root_directory = str(original.root_directory)  # type: ignore
        original.server_storage_directory = str(original.server_storage_directory)  # type: ignore
        original.server_working_directory = str(original.server_working_directory)  # type: ignore
        original.nas_directory = str(original.nas_directory)  # type: ignore
        original.mesoscope_directory = str(original.mesoscope_directory)  # type: ignore
        original.harvesters_cti_path = str(original.harvesters_cti_path)  # type: ignore

        # Converts valve calibration data into dictionary format
        if isinstance(original.valve_calibration_data, tuple):
            original.valve_calibration_data = {k: v for k, v in original.valve_calibration_data}

        # Saves the data to the YAML file
        original.to_yaml(file_path=path)
