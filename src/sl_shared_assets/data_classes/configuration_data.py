"""This module provides classes used to configure data acquisition and processing runtimes in the Sun lab.
Classes from this library are saved as .yaml files to be edited by the user when a new project and / or session
is created by the sl-experiment library. The runtime settings are then loaded from user-edited .yaml files by various
lab pipelines."""

import copy
from pathlib import Path
from dataclasses import field, dataclass

from ataraxis_data_structures import YamlConfig


@dataclass()
class ExperimentState:
    """Encapsulates the information used to set and maintain the desired experiment and Mesoscope-VR system state.

    Primarily, experiment runtime logic (task logic) is resolved by the Unity game engine. However, the Mesoscope-VR
    system configuration may also need to change throughout the experiment to optimize the runtime by disabling or
    reconfiguring specific hardware modules. For example, some experiment stages may require the running wheel to be
    locked to prevent the animal from running, and other may require the VR screens to be turned off.
    """

    experiment_state_code: int
    """The integer code of the experiment state. Experiment states do not have a predefined meaning, Instead, each 
    project is expected to define and follow its own experiment state code mapping. Typically, the experiment state 
    code is used to denote major experiment stages, such as 'baseline', 'task', 'cooldown', etc. Note, the same 
    experiment state code can be used by multiple sequential ExperimentState instances to change the VR system states 
    while maintaining the same experiment state."""
    vr_state_code: int
    """One of the supported VR system state-codes. Currently, the Mesoscope-VR system supports two state codes. State 
    code '1' denotes 'REST' state and code '2' denotes 'RUN' state. Note, multiple consecutive ExperimentState 
    instances with different experiment state codes can reuse the same VR state code."""
    state_duration_s: float
    """The time, in seconds, to maintain the current combination of the experiment and VR states."""


@dataclass()
class ExperimentConfiguration(YamlConfig):
    """Stores the configuration of a single experiment runtime.

    Primarily, this includes the sequence of experiment and Virtual Reality (Mesoscope-VR) states that defines the flow
    of the experiment runtime. During runtime, the main runtime control function traverses the sequence of states
    stored in this class instance start-to-end in the exact order specified by the user. Together with custom Unity
    projects that define the task logic (how the system responds to animal interactions with the VR system) this class
    allows flexibly implementing a wide range of experiments.

    Each project should define one or more experiment configurations and save them as .yaml files inside the project
    'configuration' folder. The name for each configuration file is defined by the user and is used to identify and load
    the experiment configuration when 'sl-run-experiment' CLI command exposed by the sl-experiment library is executed.
    """

    cue_map: dict[int, float] = field(default_factory=lambda: {0: 30.0, 1: 30.0, 2: 30.0, 3: 30.0, 4: 30.0})
    """A dictionary that maps each integer-code associated with a wall cue used in the Virtual Reality experiment 
    environment to its length in real-world centimeters. It is used to map each VR cue to the distance the animal needs
    to travel to fully traverse the wall cue region from start to end."""
    experiment_states: dict[str, ExperimentState] = field(
        default_factory=lambda: {
            "baseline": ExperimentState(experiment_state_code=1, vr_state_code=1, state_duration_s=30),
            "experiment": ExperimentState(experiment_state_code=2, vr_state_code=2, state_duration_s=120),
            "cooldown": ExperimentState(experiment_state_code=3, vr_state_code=1, state_duration_s=15),
        }
    )
    """A dictionary that uses human-readable state-names as keys and ExperimentState instances as values. Each 
    ExperimentState instance represents a phase of the experiment."""


@dataclass()
class SystemConfiguration(YamlConfig):
    """This class stores global Mesoscope-VR configuration parameters that expected to change comparatively frequently.

    These parameters are shared by all projects in the lab. Primarily, they determine how the VRPC interacts with
    various components of the Mesoscope-VR system used in the lab. Although most parameters in this class are designed
    to be permanent, it is possible that the VRPC or Mesoscope-VR configuration changes, requiring an update to these
    parameters. In that case, the instance of this class stored as a .yaml file inside the root project directory
    on the VRPC can be modified to update the affected parameters.
    """

    face_camera_index: int = 0
    """The index of the face camera in the list of all available Harvester-managed cameras."""
    left_camera_index: int = 0
    """The index of the left body camera in the list of all available OpenCV-managed cameras."""
    right_camera_index: int = 2
    """The index of the right body camera in the list of all available OpenCV-managed cameras."""
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
    harvesters_cti_path: str | Path = Path("/opt/mvIMPACT_Acquire/lib/x86_64/mvGenTLProducer.cti")
    """The path to the GeniCam CTI file used to connect to Harvesters-managed cameras."""
    google_credentials_path: str | Path = Path("/media/Data/Experiments/sl-surgery-log-0f651e492767.json")
    """
    The path to the locally stored .JSON file that contains the service account credentials used to read and write 
    Google Sheet data. This is used to access and work with the surgery log and the water restriction log files. 
    Usually, the same service account is used across all projects.
    """
    server_credentials_path: str | Path = Path("/media/Data/Experiments/server_credentials.yaml")
    """
    The path to the locally stored .YAML file that contains the credentials for accessing the BioHPC server machine. 
    While the filesystem of the server machine should already be mounted to the local machine via SMB or equivalent 
    protocol, this data is used to establish SSH connection to the server and start newly acquired data processing 
    after it is transferred to the server. This allows data acquisition, preprocessing, and processing to be controlled 
    by the same runtime and prevents unprocessed data from piling up on the server.
    """
    valve_calibration_data: dict[int | float, int | float] | tuple[tuple[int | float, int | float], ...] = (
        (15000, 1.8556),
        (30000, 3.4844),
        (45000, 7.1846),
        (60000, 10.0854),
    )
    """A tuple of tuples that maps water delivery solenoid valve open times, in microseconds, to the dispensed volume 
    of water, in microliters. During training and experiment runtimes, this data is used by the ValveModule to translate
    the requested reward volumes into times the valve needs to be open to deliver the desired volume of water.
    """

    @classmethod
    def load(cls, path: Path) -> "SystemConfiguration":
        """Loads the SystemConfiguration data from the specified .YAML file and returns it as a class instance.

        This is used at the beginning of each sl-experiment runtime to access the actual Mesoscope-VR configuration
        parameters
        """
        instance: SystemConfiguration = cls.from_yaml(path)  # type: ignore

        # Converts all paths loaded as strings to Path objects used inside the library
        instance.google_credentials_path = Path(instance.google_credentials_path)
        instance.server_credentials_path = Path(instance.server_credentials_path)
        instance.harvesters_cti_path = Path(instance.harvesters_cti_path)

        # Converts valve_calibration data from dictionary to a tuple of tuples format
        if not isinstance(instance.valve_calibration_data, tuple):
            instance.valve_calibration_data = tuple((k, v) for k, v in instance.valve_calibration_data.items())

        return instance

    def save(self, path: Path) -> None:
        """Saves the SystemConfiguration data to the specified .YAML file.

        This is typically only used once, the first time the VRPC is configured. After that, all projects reuse the
        existing .yaml file.

        Args:
            path: The path to the system_configuration.yaml file to use for storing the data.
        """
        # Copies instance data to prevent it from being modified by reference when executing the steps below
        original = copy.deepcopy(self)

        # Converts all Path objects to strings before dumping the data, as .yaml encoder does not properly recognize
        # Path objects
        original.google_credentials_path = str(original.google_credentials_path)
        original.server_credentials_path = str(original.server_credentials_path)
        original.harvesters_cti_path = str(original.harvesters_cti_path)
        # Converts valve calibration data into dictionary format
        if isinstance(original.valve_calibration_data, tuple):
            original.valve_calibration_data = {k: v for k, v in original.valve_calibration_data}

        original.to_yaml(file_path=path)
