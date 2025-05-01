"""This module contains classes jointly responsible for maintaining the Sun lab project data hierarchy across all
machines used to acquire, process, and store the data. Every valid experiment or training session conducted in the
lab generates a specific directory structure. This structure is defined via the ProjectConfiguration and SessionData
classes, which are also stored as .yaml files inside each session's raw_data and processed_data directories. Jointly,
these classes contain all necessary information to restore the data hierarchy on any machine. All other Sun lab
libraries use these classes to work with all lab-generated data."""

import re
import copy
import shutil as sh
from pathlib import Path
from dataclasses import field, dataclass

import appdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig
from ataraxis_time.time_helpers import get_timestamp

from .configuration_data import ExperimentConfiguration


def replace_root_path(path: Path) -> None:
    """Replaces the path to the local root directory used to store all Sun lab projects with the provided path.

    The first time ProjectConfiguration class is instantiated to create a new project on a new machine,
    it asks the user to provide the path to the local directory where to save all Sun lab projects. This path is then
    stored inside the default user data directory as a .yaml file to be reused for all future projects. To support
    replacing this path without searching for the user data directory, which is usually hidden, this function finds and
    updates the contents of the file that stores the local root path.

    Args:
        path: The path to the new local root directory.
    """
    # Resolves the path to the static .txt file used to store the local path to the root directory
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("root_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Ensures that the input root directory exists
    ensure_directory_exists(path)

    # Replaces the contents of the root_path.txt file with the provided path
    with open(path_file, "w") as f:
        f.write(str(path))


@dataclass()
class ProjectConfiguration(YamlConfig):
    """Stores the project-specific configuration parameters that do not change between different animals and runtime
    sessions.

    An instance of this class is generated and saved as a .yaml file in the 'configuration' directory of each project
    when it is created. After that, the stored data is reused for every runtime (training or experiment session) carried
    out for each animal of the project. Additionally, a copy of the most actual configuration file is saved inside each
    runtime session's 'raw_data' folder, providing seamless integration between the managed data and various Sun lab
    (sl-) libraries.

    Notes:
        Together with SessionData, this class forms the entry point for all interactions with the data acquired in the
        Sun lab. The fields of this class are used to flexibly configure the runtime behavior of major data acquisition
        (sl-experiment) and processing (sl-forgery) libraries, adapting them for any project in the lab.

        Most lab projects only need to adjust the "surgery_sheet_id" and "water_log_sheet_id" fields of the class. Most
        fields in this class are used by the sl-experiment library to generate the SessionData class instance for each
        session and during experiment data acquisition and preprocessing. Data processing pipelines use specialized
        configuration files stored in other modules of this library.

        Although all path fields use str | Path datatype, they are always stored as Path objects. These fields are
        converted to strings only when the data is dumped as a .yaml file.
    """

    project_name: str = ""
    """Stores the descriptive name of the project. This name is used to create the root directory for the project and 
    to discover and load project's data during runtime."""
    surgery_sheet_id: str = ""
    """The ID of the Google Sheet file that stores information about surgical interventions performed on all animals 
    participating in the managed project. This log sheet is used to parse and write the surgical intervention data for 
    each animal into every runtime session raw_data folder, so that the surgery data is always kept together with the 
    rest of the training and experiment data."""
    water_log_sheet_id: str = ""
    """The ID of the Google Sheet file that stores information about water restriction (and behavior tracker) 
    information for all animals participating in the managed project. This is used to synchronize the information 
    inside the water restriction log with the state of the animal at the end of each training or experiment session.
    """
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
    local_root_directory: str | Path = Path("/media/Data/Experiments")
    """The absolute path to the directory where all projects are stored on the local host-machine (VRPC). Note, 
    this field is configured automatically each time the class is instantiated through any method, so overwriting it 
    manually will not be respected."""
    local_server_directory: str | Path = Path("/home/cybermouse/server/storage/sun_data")
    """The absolute path to the directory where the raw data portion of all projects is stored on the BioHPC server. 
    This directory should be locally accessible (mounted) using a network sharing protocol, such as SMB."""
    local_nas_directory: str | Path = Path("/home/cybermouse/nas/rawdata")
    """The absolute path to the directory where all projects are stored on the Synology NAS. This directory should be 
    locally accessible (mounted) using a network sharing protocol, such as SMB."""
    local_mesoscope_directory: str | Path = Path("/home/cybermouse/scanimage/mesodata")
    """The absolute path to the root mesoscope (ScanImagePC) directory where all mesoscope-acquired data is aggregated 
    during acquisition runtime. This directory should be locally accessible (mounted) using a network sharing 
    protocol, such as SMB."""
    local_server_working_directory: str | Path = Path("/home/cybermouse/server/workdir/sun_data")
    """The absolute path to the directory where the processed data portion of all projects is stored on the BioHPC 
    server. This directory should be locally accessible (mounted) using a network sharing protocol, such as SMB."""
    remote_storage_directory: str | Path = Path("/storage/sun_data")
    """The absolute path, relative to the BioHPC server root, to the directory where all projects are stored on the 
    slow (SSD) volume of the server. This path is used when running remote (server-side) jobs and, therefore, has to
    be relative to the server root."""
    remote_working_directory: str | Path = Path("/workdir/sun_data")
    """The absolute path, relative to the BioHPC server root, to the directory where all projects are stored on the 
    fast (NVME) volume of the server. This path is used when running remote (server-side) jobs and, therefore, has to
    be relative to the server root."""
    face_camera_index: int = 0
    """The index of the face camera in the list of all available Harvester-managed cameras."""
    left_camera_index: int = 0
    """The index of the left body camera in the list of all available OpenCV-managed cameras."""
    right_camera_index: int = 2
    """The index of the right body camera in the list of all available OpenCV-managed cameras."""
    harvesters_cti_path: str | Path = Path("/opt/mvIMPACT_Acquire/lib/x86_64/mvGenTLProducer.cti")
    """The path to the GeniCam CTI file used to connect to Harvesters-managed cameras."""
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
    def load(cls, project_name: str, configuration_path: None | Path = None) -> "ProjectConfiguration":
        """Loads the project configuration parameters from a project_configuration.yaml file.

        This method is called during each interaction with any runtime session's data, including the creation of a new
        session. When this method is called for a non-existent (new) project name, it generates the default
        configuration file and prompts the user to update the configuration before proceeding with the runtime. All
        future interactions with the sessions from this project reuse the existing configuration file.

        Notes:
            As part of its runtime, the method may prompt the user to provide the path to the local root directory.
            This directory stores all project subdirectories and acts as the top level of the Sun lab data hierarchy.
            The path to the directory is then saved inside user's default data directory, so that it can be reused for
            all future projects. Use sl-replace-root CLI to replace the saved root directory path.

            Since this class is used for all Sun lab data structure interactions, this method supports multiple ways of
            loading class data. If this method is called as part of the sl-experiment new session creation pipeline, use
            'project_name' argument. If this method is called as part of the sl-forgery data processing pipeline(s), use
            'configuration_path' argument.

        Args:
            project_name: The name of the project whose configuration file needs to be discovered and loaded or, if the
                project does not exist, created.
            configuration_path: Optional. The path to the project_configuration.yaml file from which to load the data.
                This way of resolving the configuration data source always takes precedence over the project_name when
                both are provided.

        Returns:
            The initialized ProjectConfiguration instance that stores the configuration data for the target project.
        """

        # If the configuration path is not provided, uses the 'default' resolution strategy that involves reading the
        # user's data directory
        if configuration_path is None:
            # Uses appdirs to locate the user data directory and resolve the path to the storage file
            app_dir = Path(appdirs.user_data_dir(appname="sl_assets", appauthor="sun_lab"))
            path_file = app_dir.joinpath("root_path.txt")

            # If the .txt file that stores the local root path does not exist, prompts the user to provide the path to
            # the local root directory and creates the root_path.txt file
            if not path_file.exists():
                # Gets the path to the local root directory from the user via command line input
                message = (
                    "Unable to resolve the local root directory automatically. Provide the absolute path to the local "
                    "directory that stores all project-specific directories. This is required when resolving project "
                    "configuration based on project's name."
                )
                # noinspection PyTypeChecker
                console.echo(message=message, level=LogLevel.WARNING)
                root_path_str = input("Local root path: ")
                root_path = Path(root_path_str)

                # If necessary, generates the local root directory
                ensure_directory_exists(root_path)

                # Also ensures that the app directory exists, so that the path_file can be created below.
                ensure_directory_exists(path_file)

                # Saves the root path to the file
                with open(path_file, "w") as f:
                    f.write(str(root_path))

            # Once the location of the path storage file is resolved, reads the root path from the file
            with open(path_file, "r") as f:
                root_path = Path(f.read().strip())

            # Uses the root experiment directory path to generate the path to the target project's configuration file.
            configuration_path = root_path.joinpath(project_name, "configuration", "project_configuration.yaml")
            ensure_directory_exists(configuration_path)  # Ensures the directory tree for the config path exists.

        # If the configuration file does not exist (this is the first time this class is initialized for a given
        # project), generates a precursor (default) configuration file and prompts the user to update the configuration.
        if not configuration_path.exists():
            message = (
                f"Unable to load project configuration data from disk as no 'project_configuration.yaml' file "
                f"found at the provided project path. Generating a precursor (default) configuration file under "
                f"{project_name}/configuration directory. Edit the file to specify project configuration before "
                f"proceeding further to avoid runtime errors. Also, edit other configuration precursors saved to the "
                f"same directory to control other aspects of data acquisition and processing."
            )
            # noinspection PyTypeChecker
            console.echo(message=message, level=LogLevel.WARNING)

            # Generates the default project configuration instance and dumps it as a .yaml file. Note, as part of
            # this process, the class generates the correct 'local_root_path' based on the path provided by the
            # user.
            precursor = ProjectConfiguration(local_root_directory=Path(str(configuration_path.parents[2])))
            precursor.project_name = project_name
            precursor.save(path=configuration_path)

            # Waits for the user to manually configure the newly created file.
            input(f"Enter anything to continue: ")

        # Loads the data from the YAML file and initializes the class instance. This now uses either the automatically
        # resolved configuration path or the manually provided path
        instance: ProjectConfiguration = cls.from_yaml(file_path=configuration_path)  # type: ignore

        # Converts all paths loaded as strings to Path objects used inside the library
        instance.local_mesoscope_directory = Path(instance.local_mesoscope_directory)
        instance.local_nas_directory = Path(instance.local_nas_directory)
        instance.local_server_directory = Path(instance.local_server_directory)
        instance.local_server_working_directory = Path(instance.local_server_working_directory)
        instance.remote_storage_directory = Path(instance.remote_storage_directory)
        instance.remote_working_directory = Path(instance.remote_working_directory)
        instance.google_credentials_path = Path(instance.google_credentials_path)
        instance.server_credentials_path = Path(instance.server_credentials_path)
        instance.harvesters_cti_path = Path(instance.harvesters_cti_path)

        # Local root path is always re-computed from the resolved configuration file's location
        instance.local_root_directory = Path(str(configuration_path.parents[2]))

        # Converts valve_calibration data from dictionary to a tuple of tuples format
        if not isinstance(instance.valve_calibration_data, tuple):
            instance.valve_calibration_data = tuple((k, v) for k, v in instance.valve_calibration_data.items())

        # Partially verifies the loaded data. Most importantly, this step does not allow proceeding if the user did not
        # replace the surgery log and water restriction log placeholders with valid ID values.
        instance._verify_data()

        # Returns the initialized class instance to caller
        return instance

    def save(self, path: Path) -> None:
        """Saves class instance data to disk as a project_configuration.yaml file.

        This method is automatically called when a new project is created. After this method's runtime, all future
        calls to the load() method will reuse the configuration data saved to the .yaml file.

        Notes:
            When this method is used to generate the configuration .yaml file for a new project, it also generates the
            example 'default_experiment.yaml'. This file is designed to showcase how to write ExperimentConfiguration
            data files that are used to control Mesoscope-VR system states during experiment session runtimes.

        Args:
            path: The path to the .yaml file to save the data to.
        """

        # Copies instance data to prevent it from being modified by reference when executing the steps below
        original = copy.deepcopy(self)

        # Converts all Path objects to strings before dumping the data, as .yaml encoder does not properly recognize
        # Path objects
        original.local_root_directory = str(original.local_root_directory)
        original.local_mesoscope_directory = str(original.local_mesoscope_directory)
        original.local_nas_directory = str(original.local_nas_directory)
        original.local_server_directory = str(original.local_server_directory)
        original.local_server_working_directory = str(original.local_server_working_directory)
        original.remote_storage_directory = str(original.remote_storage_directory)
        original.remote_working_directory = str(original.remote_working_directory)
        original.google_credentials_path = str(original.google_credentials_path)
        original.server_credentials_path = str(original.server_credentials_path)
        original.harvesters_cti_path = str(original.harvesters_cti_path)

        # Converts valve calibration data into dictionary format
        if isinstance(original.valve_calibration_data, tuple):
            original.valve_calibration_data = {k: v for k, v in original.valve_calibration_data}

        # Saves the data to the YAML file
        original.to_yaml(file_path=path)

        # As part of this runtime, also generates and dumps the 'precursor' experiment configuration file.
        experiment_configuration_path = path.parent.joinpath("default_experiment.yaml")
        if not experiment_configuration_path.exists():
            example_experiment = ExperimentConfiguration()
            example_experiment.to_yaml(experiment_configuration_path)

    def _verify_data(self) -> None:
        """Verifies the user-modified data loaded from the project_configuration.yaml file.

        Since this class is explicitly designed to be modified by the user, this verification step is carried out to
        ensure that the loaded data matches expectations. This reduces the potential for user errors to impact the
        runtime behavior of the libraries using this class. This internal method is automatically called by the load()
        method.

        Notes:
            The method does not verify all fields loaded from the configuration file and instead focuses on fields that
            do not have valid default values. Since these fields are expected to be frequently modified by users, they
            are the ones that require additional validation.

        Raises:
            ValueError: If the loaded data does not match expected formats or values.
        """

        # Verifies Google Sheet ID formatting. Google Sheet IDs are usually 44 characters long, containing letters,
        # numbers, hyphens, and underscores
        pattern = r"^[a-zA-Z0-9_-]{44}$"
        if not re.match(pattern, self.surgery_sheet_id):
            message = (
                f"Unable to verify the surgery_sheet_id field loaded from the 'project_configuration.yaml' file. "
                f"Expected a string with 44 characters, using letters, numbers, hyphens, and underscores, but found: "
                f"{self.surgery_sheet_id}."
            )
            console.error(message=message, error=ValueError)
        if not re.match(pattern, self.water_log_sheet_id):
            message = (
                f"Unable to verify the surgery_sheet_id field loaded from the 'project_configuration.yaml' file. "
                f"Expected a string with 44 characters, using letters, numbers, hyphens, and underscores, but found: "
                f"{self.water_log_sheet_id}."
            )
            console.error(message=message, error=ValueError)


@dataclass()
class RawData:
    """Stores the paths to the directories and files that make up the 'raw_data' session-specific directory.

    The raw_data directory stores the data acquired during the session runtime before and after preprocessing. Since
    preprocessing does not alter the data, any data in that folder is considered 'raw'. The raw_data folder is initially
    created on the VRPC and, after preprocessing, is copied to the BioHPC server and the Synology NAS for long-term
    storage and further processing.
    """

    raw_data_path: Path = Path()
    """Stores the path to the root raw_data directory of the session. This directory stores all raw data during 
    acquisition and preprocessing. Note, preprocessing does not alter raw data, so at any point in time all data inside
    the folder is considered 'raw'."""
    camera_data_path: Path = Path()
    """Stores the path to the directory that contains all camera data acquired during the session. Primarily, this 
    includes .mp4 video files from each recorded camera."""
    mesoscope_data_path: Path = Path()
    """Stores the path to the directory that contains all Mesoscope data acquired during the session. Primarily, this 
    includes the mesoscope-acquired .tiff files (brain activity data) and the motion estimation data."""
    behavior_data_path: Path = Path()
    """Stores the path to the directory that contains all behavior data acquired during the session. Primarily, this 
    includes the .npz log files used by data-acquisition libraries to store all acquired data. The data stored in this 
    way includes the camera and mesoscope frame timestamps and the states of Mesoscope-VR components, such as lick 
    sensors, rotary encoders, and other modules."""
    zaber_positions_path: Path = Path()
    """Stores the path to the zaber_positions.yaml file. This file contains the snapshot of all Zaber motor positions 
    at the end of the session. Zaber motors are used to position the LickPort and the HeadBar manipulators, which is 
    essential for supporting proper brain imaging and animal's running behavior during the session."""
    session_descriptor_path: Path = Path()
    """Stores the path to the session_descriptor.yaml file. This file is partially filled by the system during runtime 
    and partially by the experimenter after the runtime. It contains session-specific information, such as the specific
    training parameters, the positions of the Mesoscope objective and the notes made by the experimenter during 
    runtime."""
    hardware_configuration_path: Path = Path()
    """Stores the path to the hardware_configuration.yaml file. This file contains the partial snapshot of the 
    calibration parameters used by the Mesoscope-VR system components during runtime. Primarily, this is used during 
    data processing to read the .npz data log files generated during runtime."""
    surgery_metadata_path: Path = Path()
    """Stores the path to the surgery_metadata.yaml file. This file contains the most actual information about the 
    surgical intervention(s) performed on the animal prior to the session."""
    project_configuration_path: Path = Path()
    """Stores the path to the project_configuration.yaml file. This file contains the snapshot of the configuration 
    parameters for the session's project."""
    session_data_path: Path = Path()
    """Stores the path to the session_data.yaml file. This path is used by the SessionData instance to save itself to 
    disk as a .yaml file. The file contains all paths used during data acquisition and processing on both the VRPC and 
    the BioHPC server."""
    experiment_configuration_path: Path = Path()
    """Stores the path to the experiment_configuration.yaml file. This file contains the snapshot of the 
    experiment runtime configuration used by the session. This file is only created for experiment session. It does not
    exist for behavior training sessions."""
    mesoscope_positions_path: Path = Path()
    """Stores the path to the mesoscope_positions.yaml file. This file contains the snapshot of the positions used
    by the Mesoscope at the end of the session. This includes both the physical position of the mesoscope objective and
    the 'virtual' tip, tilt, and fastZ positions set via ScanImage software. This file is only created for experiment 
    sessions that use the mesoscope, it is omitted for behavior training sessions."""
    window_screenshot_path: Path = Path()
    """Stores the path to the .png screenshot of the ScanImagePC screen. The screenshot should contain the image of the 
    cranial window and the red-dot alignment windows. This is used to generate a visual snapshot of the cranial window
    alignment and appearance for each experiment session. This file is only created for experiment sessions that use 
    the mesoscope, it is omitted for behavior training sessions."""
    telomere_path: Path = Path()
    """Stores the path to the telomere.bin file. This file is created by the data processing pipelines running on the 
    BioHPC server to confirm that the raw_data transferred to the server was not altered or damage in transmission."""
    checksum_path: Path = Path()
    """Stores the path to the ax_checksum.txt file. This file is generated as part of packaging the data for 
    transmission and stores the xxHash-128 checksum of the data. It is used to verify that the transmission did not 
    damage or otherwise alter the data."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """

        # Generates the managed paths
        self.raw_data_path = root_directory_path
        self.camera_data_path = self.raw_data_path.joinpath("camera_data")
        self.mesoscope_data_path = self.raw_data_path.joinpath("mesoscope_data")
        self.behavior_data_path = self.raw_data_path.joinpath("behavior_data")
        self.zaber_positions_path = self.raw_data_path.joinpath("zaber_positions.yaml")
        self.session_descriptor_path = self.raw_data_path.joinpath("session_descriptor.yaml")
        self.hardware_configuration_path = self.raw_data_path.joinpath("hardware_configuration.yaml")
        self.surgery_metadata_path = self.raw_data_path.joinpath("surgery_metadata.yaml")
        self.project_configuration_path = self.raw_data_path.joinpath("project_configuration.yaml")
        self.session_data_path = self.raw_data_path.joinpath("session_data.yaml")
        self.experiment_configuration_path = self.raw_data_path.joinpath("experiment_configuration.yaml")
        self.mesoscope_positions_path = self.raw_data_path.joinpath("mesoscope_positions.yaml")
        self.window_screenshot_path = self.raw_data_path.joinpath("window_screenshot.png")
        self.telomere_path = self.raw_data_path.joinpath("telomere.bin")
        self.checksum_path = self.raw_data_path.joinpath("ax_checksum.txt")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""
        ensure_directory_exists(self.raw_data_path)
        ensure_directory_exists(self.camera_data_path)
        ensure_directory_exists(self.mesoscope_data_path)
        ensure_directory_exists(self.behavior_data_path)


@dataclass()
class DeepLabCutData:
    """Stores the paths to the directories and files that make up the 'deeplabcut' project-specific directory.

    DeepLabCut (DLC) is used to track animal body parts and poses in video data acquired during experiment and training
    sessions. Since DLC is designed to work with projects, rather than single animals or sessions, each Sun lab
    project data hierarchy contains a dedicated 'deeplabcut' directory under the root project directory. The contents of
    that directory are largely managed by the DLC itself. Therefore, each session of a given project refers to and
    uses the same 'deeplabcut' directory.
    """

    deeplabcut_path: Path = Path()
    """Stores the path to the project-specific DeepLabCut directory. This folder stores all DeepLabCut data specific to
    a single project, which is reused during the processing of all sessions of the project."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """

        # Generates the managed paths
        self.deeplabcut_path = root_directory_path

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""
        ensure_directory_exists(self.deeplabcut_path)


@dataclass()
class ConfigurationData:
    """Stores the paths to the directories and files that make up the 'configuration' project-specific directory.

    The configuration directory contains various configuration files and settings used by data acquisition,
    preprocessing, and processing pipelines in the lab. Generally, all configuration settings are defined once for each
    project and are reused for every session within the project. Therefore, this directory is created under each main
    project directory.

    Notes:
        Some attribute names inside this section match the names in the RawData section. This is intentional, as some
        configuration files are copied into the raw_data session directories to allow reinstating the session data
        hierarchy across machines.
    """

    configuration_path: Path = Path()
    """Stores the path to the project-specific configuration directory. This directory is used by all animals 
    and sessions of the project to store all pan-project configuration files. The configuration data is reused by all
    sessions in the project."""
    experiment_configuration_path: Path = Path()
    """Stores the path to the experiment_configuration.yaml file. This file contains the snapshot of the 
    experiment runtime configuration used by the session. This file is only created for experiment session. It does not
    exist for behavior training sessions."""
    project_configuration_path: Path = Path()
    """Stores the path to the project_configuration.yaml file. This file contains the snapshot of the configuration 
    parameters for the session's project."""
    single_day_s2p_configuration_path: Path = Path()
    """Stores the path to the single_day_s2p_configuration.yaml file stored inside the project's 'configuration' 
    directory on the fast BioHPC server volume. This configuration file specifies the parameters for the 'single day' 
    suite2p registration pipeline, which is applied to each session that generates brain activity data."""
    multi_day_s2p_configuration_path: Path = Path()
    """Stores the path to the multi_day_s2p_configuration.yaml file stored inside the project's 'configuration' 
    directory on the fast BioHPC server volume. This configuration file specifies the parameters for the 'multiday' 
    sl-suite2p-based registration pipelines used tot rack brain cells across multiple sessions."""

    def resolve_paths(self, root_directory_path: Path, experiment_name: str | None = None) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
            experiment_name: Optionally specifies the name of the experiment executed as part of the managed session's
                runtime. This is used to correctly configure the path to the specific ExperimentConfiguration data file.
                If the managed session is not an Experiment session, this parameter should be set to None.
        """

        # Generates the managed paths
        self.configuration_path = root_directory_path
        if experiment_name is None:
            self.experiment_configuration_path = self.configuration_path.joinpath("null")
        else:
            self.experiment_configuration_path = self.configuration_path.joinpath(f"{experiment_name}.yaml")
        self.project_configuration_path = self.configuration_path.joinpath("project_configuration.yaml")
        self.single_day_s2p_configuration_path = self.configuration_path.joinpath("single_day_s2p_configuration.yaml")
        self.multi_day_s2p_configuration_path = self.configuration_path.joinpath("multi_day_s2p_configuration.yaml")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""
        ensure_directory_exists(self.configuration_path)


@dataclass()
class ProcessedData:
    """Stores the paths to the directories and files that make up the 'processed_data' session-specific directory.

    The processed_data directory stores the data generated by various processing pipelines from the raw data (contents
    of the raw_data directory). Processed data represents an intermediate step between raw data and the dataset used in
    the data analysis, but is not itself designed to be analyzed.

    Notes:
        The paths from this section are typically used only on the BioHPC server. This is because most data processing
        in the lab is performed using the processing server's resources. On the server, processed data is stored on
        the fast (NVME) drive volume, in contrast to raw data, which is stored on the slow (SSD) drive volume.

        When this class is instantiated on a machine other than BioHPC server, for example, to test processing
        pipelines, it uses the same drive as the raw_data folder to create the processed_data folder. This relies on the
        assumption that non-server machines in the lab only use fast NVME drives, so there is no need to separate
        storage and processing volumes.
    """

    processed_data_path: Path = Path()
    """Stores the path to the root processed_data directory of the session. This directory stores the processed data 
    as it is generated by various data processing pipelines."""
    camera_data_path: Path = Path()
    """Stores the path to the directory that contains video tracking data generated by our DeepLabCut-based video 
    processing pipelines."""
    mesoscope_data_path: Path = Path()
    """Stores path to the directory that contains processed brain activity (cell) data generated by our suite2p-based 
    photometry processing pipelines (single day and multi day)."""
    behavior_data_path: Path = Path()
    """Stores the path to the directory that contains the non-video behavior and system runtime data extracted from 
    .npz log files by our in-house log parsing pipeline."""
    job_logs_path: Path = Path()
    """Stores the path to the directory that stores the standard output and standard error data collected during 
    server-side data processing pipeline runtimes. Since we use SLURM job manager to execute multiple compute jobs on 
    the BioHPC server, all information sent to the terminal during runtime is redirected to text files stored in this
    directory."""
    project_configuration_path: Path = Path()
    """Stores the path to the project_configuration.yaml file. This file contains the snapshot of the configuration 
    parameters for the session's project."""
    session_data_path: Path = Path()
    """Stores the path to the session_data.yaml file. This path is used by the SessionData instance to save itself to 
    disk as a .yaml file. The file contains all paths used during data acquisition and processing on both the VRPC and 
    the BioHPC server."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """
        # Generates the managed paths
        self.processed_data_path = root_directory_path
        self.camera_data_path = self.processed_data_path.joinpath("camera_data")
        self.mesoscope_data_path = self.processed_data_path.joinpath("mesoscope_data")
        self.behavior_data_path = self.processed_data_path.joinpath("behavior_data")
        self.job_logs_path = self.processed_data_path.joinpath("job_logs")
        self.project_configuration_path = self.processed_data_path.joinpath("project_configuration.yaml")
        self.session_data_path = self.processed_data_path.joinpath("session_data.yaml")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

        ensure_directory_exists(self.processed_data_path)
        ensure_directory_exists(self.camera_data_path)
        ensure_directory_exists(self.behavior_data_path)
        ensure_directory_exists(self.job_logs_path)


@dataclass()
class VRPCPersistentData:
    """Stores the paths to the directories and files that make up the 'persistent_data' directory on the VRPC.

    Persistent data directories are only used during data acquisition. Therefore, unlike most other directories, they
    are purposefully designed for specific PCs that participate in data acquisition. This section manages the
    animal-specific persistent_data directory stored on the VRPC.

    VRPC persistent data directory is used to preserve configuration data, such as the positions of Zaber motors and
    Meososcope objective, so that they can be reused across sessions of the same animals. The data in this directory
    is read at the beginning of each session and replaced at the end of each session.
    """

    persistent_data_path: Path = Path()
    """Stores the path to the project and animal specific 'persistent_data' directory to which the managed session 
    belongs, relative to the VRPC root. This directory is exclusively used on the VRPC."""
    zaber_positions_path: Path = Path()
    """Stores the path to the Zaber motor positions snapshot generated at the end of the previous session runtime. This 
    is used to automatically restore all Zaber motors to the same position across all sessions."""
    mesoscope_positions_path: Path = Path()
    """Stores the path to the Mesoscope positions snapshot generated at the end of the previous session runtime. This 
    is used to help the user to (manually) restore the Mesoscope to the same position across all sessions."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """

        # Generates the managed paths
        self.persistent_data_path = root_directory_path
        self.zaber_positions_path = self.persistent_data_path.joinpath("zaber_positions.yaml")
        self.mesoscope_positions_path = self.persistent_data_path.joinpath("mesoscope_positions.yaml")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

        ensure_directory_exists(self.persistent_data_path)


@dataclass()
class ScanImagePCPersistentData:
    """Stores the paths to the directories and files that make up the 'persistent_data' directory on the ScanImagePC.

    Persistent data directories are only used during data acquisition. Therefore, unlike most other directories, they
    are purposefully designed for specific PCs that participate in data acquisition. This section manages the
    animal-specific persistent_data directory stored on the ScanImagePC (Mesoscope PC).

    ScanImagePC persistent data directory is used to preserve the motion estimation snapshot, generated during the first
    experiment session. This is necessary to align the brain recording field of view across sessions. In turn, this
    is used to carry out 'online' motion and z-drift correction, improving the accuracy of across-day (multi-day)
    cell tracking.
    """

    persistent_data_path: Path = Path()
    """Stores the path to the project and animal specific 'persistent_data' directory to which the managed session 
    belongs, relative to the ScanImagePC root. This directory is exclusively used on the ScanImagePC (Mesoscope PC)."""
    motion_estimator_path: Path = Path()
    """Stores the 'reference' motion estimator file generated during the first experiment session of each animal. This 
    file is kept on the ScanImagePC to image the same population of cells across all experiment sessions."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """

        # Generates the managed paths
        self.persistent_data_path = root_directory_path
        self.motion_estimator_path = self.persistent_data_path.joinpath("MotionEstimator.me")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

        ensure_directory_exists(self.persistent_data_path)


@dataclass()
class MesoscopeData:
    """Stores the paths to the directories and files that make up the 'meso_data' directory on the ScanImagePC.

    The meso_data directory is the root directory where all mesoscope-generated data is stored on the ScanImagePC. The
    path to this directory should be given relative to the VRPC root and be mounted to the VRPC filesystem via the
    SMB or equivalent protocol.

    During runtime, the ScanImagePC should organize all collected data under this root directory. During preprocessing,
    the VRPC uses SMB to access the data in this directory and merge it into the 'raw_data' session directory. The paths
    in this section, therefore, are specific to the VRPC and are not used on other PCs.
    """

    meso_data_path: Path = Path()
    """Stores the path to the root ScanImagePC data directory, mounted to the VRPC filesystem via the SMB or equivalent 
    protocol. All mesoscope-generated data is stored under this root directory before it is merged into the VRPC-managed
    raw_data directory of each session."""
    mesoscope_data_path: Path = Path()
    """Stores the path to the 'default' mesoscope_data directory. All experiment sessions across all animals and 
    projects use the same mesoscope_data directory to save the data generated by the mesoscope via ScanImage 
    software. This simplifies ScanImagePC configuration process during runtime, as all data is always saved in the same
    directory. During preprocessing, the data is moved from the default directory first into a session-specific 
    ScanImagePC directory and then into the VRPC raw_data session directory."""
    session_specific_path: Path = Path()
    """Stores the path to the session-specific data directory. This directory is generated at the end of each experiment
    runtime to prepare mesoscope data for being moved to the VRPC-managed raw_data directory and to reset the 'default' 
    mesoscope_data directory for the next session's runtime."""
    ubiquitin_path: Path = Path()
    """Stores the path to the 'ubiquitin.bin' file. This file is automatically generated inside the session-specific 
    data directory after its contents are safely transferred to the VRPC as part of preprocessing. During redundant data
    removal step of preprocessing, the VRPC searches for directories marked with ubiquitin.bin and deletes them from the
    ScanImagePC filesystem."""

    def resolve_paths(self, root_mesoscope_path: Path, session_name: str) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_mesoscope_path: The path to the top-level directory of the ScanImagePC data hierarchy mounted to the
                VRPC via the SMB or equivalent protocol.
            session_name: The name of the session for which this subclass is initialized.
        """

        # Generates the managed paths
        self.meso_data_path = root_mesoscope_path
        self.session_specific_path = self.meso_data_path.joinpath(session_name)
        self.ubiquitin_path = self.session_specific_path.joinpath("ubiquitin.bin")
        self.mesoscope_data_path = self.meso_data_path.joinpath("mesoscope_data")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

        ensure_directory_exists(self.meso_data_path)


@dataclass()
class VRPCDestinations:
    """Stores the paths to the VRPC filesystem-mounted directories of the Synology NAS and BioHPC server.

    The paths from this section are primarily used to transfer preprocessed data to the long-term storage destinations.
    Additionally, they allow VRPC to interface with the configuration directory of the BioHPC server to start data
    processing jobs and to read the data from the processed_data directory to remove redundant data from the VRPC
    filesystem.

    Overall, this section is intended solely for the VRPC and should not be used on other PCs.
    """

    nas_raw_data_path: Path = Path()
    """Stores the path to the session's raw_data directory on the Synology NAS, which is mounted to the VRPC via the 
    SMB or equivalent protocol."""
    server_raw_data_path: Path = Path()
    """Stores the path to the session's raw_data directory on the BioHPC server, which is mounted to the VRPC via the 
    SMB or equivalent protocol."""
    server_processed_data_path: Path = Path()
    """Stores the path to the session's processed_data directory on the BioHPC server, which is mounted to the VRPC via 
    the SMB or equivalent protocol."""
    server_configuration_path: Path = Path()
    """Stores the path to the project-specific 'configuration' directory on the BioHPC server, which is mounted to the 
    VRPC via the SMB or equivalent protocol."""
    telomere_path: Path = Path()
    """Stores the path to the session's telomere.bin marker. This marker is generated as part of data processing on the 
    BioHPC server to notify the VRPC that the server received preprocessed data intact. The presence of this marker is 
    used by the VRPC to determine which locally stored raw_data is safe to delete from the filesystem."""
    suite2p_configuration_path: Path = Path()
    """Stores the path to the suite2p_configuration.yaml file stored inside the project's 'configuration' directory on
    the BioHPC server. This configuration file specifies the parameters for the 'single day' sl-suite2p registration 
    pipeline, which is applied to each session that generates brain activity data."""
    processing_tracker_path: Path = Path()
    """Stores the path to the processing_tracker.yaml file stored inside the sessions' root processed_data directory on 
    the BioHPC server. This file tracks which processing pipelines need to be applied the target session and the status 
    (success / failure) of each applied pipeline.
    """
    multiday_configuration_path: Path = Path()
    """Stores the path to the multiday_configuration.yaml file stored inside the project's 'configuration' directory 
    on the BioHPC server. This configuration file specifies the parameters for the 'multiday' sl-suite2p registration 
    pipeline used to track brain cells across multiple sessions."""

    def resolve_paths(
        self,
        nas_raw_data_path: Path,
        server_raw_data_path: Path,
        server_processed_data_path: Path,
        server_configuration_path: Path,
    ) -> None:
        """Resolves all paths managed by the class instance based on the input root directory paths.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            nas_raw_data_path: The path to the session's raw_data directory on the Synology NAS, relative to the VRPC
                filesystem root.
            server_raw_data_path: The path to the session's raw_data directory on the BioHPC server, relative to the
                VRPC filesystem root.
            server_processed_data_path: The path to the session's processed_data directory on the BioHPC server,
                relative to the VRPC filesystem root.
            server_configuration_path: The path to the project-specific 'configuration' directory on the BioHPC server,
                relative to the VRPC filesystem root.
        """

        # Generates the managed paths
        self.nas_raw_data_path = nas_raw_data_path
        self.server_raw_data_path = server_raw_data_path
        self.server_processed_data_path = server_processed_data_path
        self.server_configuration_path = server_configuration_path
        self.telomere_path = self.server_raw_data_path.joinpath("telomere.bin")
        self.suite2p_configuration_path = self.server_configuration_path.joinpath("suite2p_configuration.yaml")
        self.processing_tracker_path = self.server_processed_data_path.joinpath("processing_tracker.yaml")
        self.multiday_configuration_path = self.server_configuration_path.joinpath("multiday_configuration.yaml")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""
        ensure_directory_exists(self.nas_raw_data_path)
        ensure_directory_exists(self.server_raw_data_path)
        ensure_directory_exists(self.server_configuration_path)
        ensure_directory_exists(self.server_processed_data_path)


@dataclass
class SessionData(YamlConfig):
    """Stores and manages the data layout of a single training or experiment session acquired using the Sun lab
    Mesoscope-VR system.

    The primary purpose of this class is to maintain the session data structure across all supported destinations and
    during all processing stages. It generates the paths used by all other classes from all Sun lab libraries that
    interact with the session's data from the point of its creation and until the data is integrated into an
    analysis dataset.

    When necessary, the class can be used to either generate a new session or load the layout of an already existing
    session. When the class is used to create a new session, it generates the new session's name using the current
    UTC timestamp, accurate to microseconds. This ensures that each session name is unique and preserves the overall
    session order.

    Notes:
        If this class is instantiated on the VRPC, it is expected that the BioHPC server, Synology NAS, and ScanImagePC
        data directories are mounted on the local filesystem via the SMB or equivalent protocol. All manipulations
        with these destinations are carried out with the assumption that the local OS has full access to these
        directories and filesystems.

        This class is specifically designed for working with the data from a single session, performed by a single
        animal under the specific experiment. The class is used to manage both raw and processed data. It follows the
        data through acquisition, preprocessing and processing stages of the Sun lab data workflow. Together with
        ProjectConfiguration class, this class serves as an entry point for all interactions with the managed session's
        data.
    """

    project_name: str
    """Stores the name of the managed session's project."""
    animal_id: str
    """Stores the unique identifier of the animal that participates in the managed session."""
    session_name: str
    """Stores the name (timestamp-based ID) of the managed session."""
    session_type: str
    """Stores the type of the session. Primarily, this determines how to read the session_descriptor.yaml file. Has 
    to be set to one of the four supported types: 'Lick training', 'Run training', 'Window checking' or 'Experiment'.
    """
    experiment_name: str | None
    """Stores the name of the experiment configuration file. If the session_type field is set to 'Experiment' and this 
    field is not None (null), it communicates the specific experiment configuration used by the session. During runtime,
    the name stored here is used to load the specific experiment configuration data stored in a .yaml file with the 
    same name. If the session is not an experiment session, this field is ignored."""
    raw_data: RawData = field(default_factory=lambda: RawData())
    """Stores the paths to all subfolders and files found under the /project/animal/session/raw_data directory of any 
    PC used to work with Sun lab data."""
    processed_data: ProcessedData = field(default_factory=lambda: ProcessedData())
    """Stores the paths to all subfolders and files found under the /project/animal/session/processed_data directory of 
    any PC used to work with Sun lab data."""
    deeplabcut_data: DeepLabCutData = field(default_factory=lambda: DeepLabCutData())
    """Stores the paths to all subfolders and files found under the /project/deeplabcut directory of any PC used to 
    work with Sun lab data."""
    configuration_data: ConfigurationData = field(default_factory=lambda: ConfigurationData())
    """Stores the paths to all subfolders and files found under the /project/configuration directory of any PC used to 
    work with Sun lab data."""
    vrpc_persistent_data: VRPCPersistentData = field(default_factory=lambda: VRPCPersistentData())
    """Stores the paths to all subfolders and files found under the /project/animal/persistent_data directory of 
    the VRPC used in the Sun lab to acquire behavior data."""
    scanimagepc_persistent_data: ScanImagePCPersistentData = field(default_factory=lambda: ScanImagePCPersistentData())
    """Stores the paths to all subfolders and files found under the /project/animal/persistent_data directory of 
    the ScanImagePC used in the Sun lab to acquire brain activity data."""
    mesoscope_data: MesoscopeData = field(default_factory=lambda: MesoscopeData())
    """Stores the paths to all subfolders and files found under the /meso_data (root mesoscope data) directory of 
    the ScanImagePC used in the Sun lab to acquire brain activity data."""
    destinations: VRPCDestinations = field(default_factory=lambda: VRPCDestinations())
    """Stores the paths to all subfolders and files under various VRPC-filesystem-mounted directories of other machines 
    used in the Sun lab for long-term data storage."""

    @classmethod
    def create(
        cls,
        animal_id: str,
        session_type: str,
        project_configuration: ProjectConfiguration,
        experiment_name: str | None = None,
        session_name: str | None = None,
    ) -> "SessionData":
        """Creates a new SessionData object and generates the new session's data structure.

        This method is called by sl-experiment runtimes that create new training or experiment sessions to generate the
        session data directory tree. It always assumes it is called on the VRPC and, as part of its runtime, resolves
        and generates the necessary local and ScanImagePC directories to support acquiring and preprocessing session's
        data.

        Notes:
            To load an already existing session data structure, use the load() method instead.

            This method automatically dumps the data of the created SessionData instance into the session_data.yaml file
            inside the root raw_data directory of the created hierarchy. It also finds and dumps other configuration
            files, such as project_configuration.yaml and experiment_configuration.yaml, into the same raw_data
            directory. This ensures that if the session's runtime is interrupted unexpectedly, the acquired data can
            still be processed.

        Args:
            animal_id: The ID code of the animal for which the data is acquired.
            session_type: The type of the session. Primarily, this determines how to read the session_descriptor.yaml
                file. Valid options are 'Lick training', 'Run training', 'Window checking', or 'Experiment'.
            experiment_name: The name of the experiment executed during managed session. This optional argument is only
                used for 'Experiment' session types. It is used to find the experiment configuration .YAML file.
            project_configuration: The initialized ProjectConfiguration instance that stores the session's project
                configuration data. This is used to determine the root directory paths for all lab machines used during
                data acquisition and processing.
            session_name: An optional session_name override. Generally, this argument should not be provided for most
                sessions. When provided, the method uses this name instead of generating a new timestamp-based name.
                This is only used during the 'ascension' runtime to convert old data structures to the modern
                lab standards.

        Returns:
            An initialized SessionData instance that stores the layout of the newly created session's data.
        """

        # Acquires the UTC timestamp to use as the session name
        if session_name is None:
            session_name = str(get_timestamp(time_separator="-"))

        # Extracts the root directory paths stored inside the project configuration file. These roots are then used to
        # initialize this class instance.
        vrpc_root = Path(project_configuration.local_root_directory)
        mesoscope_root = Path(project_configuration.local_mesoscope_directory)
        biohpc_root = Path(project_configuration.local_server_directory)
        biohpc_workdir = Path(project_configuration.local_server_working_directory)
        nas_root = Path(project_configuration.local_nas_directory)

        # Extracts the name of the project stored inside the project configuration file.
        project_name = project_configuration.project_name

        # Constructs the session directory path
        session_path = vrpc_root.joinpath(project_name, animal_id, session_name)

        # Handles potential session name conflicts
        counter = 0
        while session_path.exists():
            counter += 1
            new_session_name = f"{session_name}_{counter}"
            session_path = vrpc_root.joinpath(project_name, animal_id, new_session_name)

        # If a conflict is detected and resolved, warns the user about the resolved conflict.
        if counter > 0:
            message = (
                f"Session name conflict occurred for animal '{animal_id}' of project '{project_name}' "
                f"when adding the new session with timestamp {session_name}. The session with identical name "
                f"already exists. The newly created session directory uses a '_{counter}' postfix to distinguish "
                f"itself from the already existing session directory."
            )
            console.echo(message=message, level=LogLevel.ERROR)

        # Generates subclasses stored inside the main class instance based on the data resolved above. Note; most fields
        # of these classes are resolved automatically, based on one or more 'root' paths provided to the 'resolve_paths'
        # method.
        raw_data = RawData()
        raw_data.resolve_paths(root_directory_path=session_path.joinpath("raw_data"))
        raw_data.make_directories()  # Generates the local directory tree

        processed_data = ProcessedData()
        processed_data.resolve_paths(root_directory_path=session_path.joinpath("processed_data"))
        processed_data.make_directories()

        dlc_data = DeepLabCutData()
        dlc_data.resolve_paths(root_directory_path=vrpc_root.joinpath(project_name, "deeplabcut"))
        dlc_data.make_directories()

        configuration_data = ConfigurationData()
        configuration_data.resolve_paths(
            root_directory_path=vrpc_root.joinpath(project_name, "configuration"),
            experiment_name=experiment_name,
        )
        configuration_data.make_directories()

        vrpc_persistent_data = VRPCPersistentData()
        vrpc_persistent_path = vrpc_root.joinpath(project_name, animal_id, "persistent_data")
        vrpc_persistent_data.resolve_paths(root_directory_path=vrpc_persistent_path)
        vrpc_persistent_data.make_directories()

        scanimagepc_persistent_data = ScanImagePCPersistentData()
        scanimagepc_persistent_path = mesoscope_root.joinpath(project_name, animal_id, "persistent_data")
        scanimagepc_persistent_data.resolve_paths(root_directory_path=scanimagepc_persistent_path)
        scanimagepc_persistent_data.make_directories()

        mesoscope_data = MesoscopeData()
        mesoscope_data.resolve_paths(root_mesoscope_path=mesoscope_root, session_name=session_name)
        mesoscope_data.make_directories()

        destinations = VRPCDestinations()
        destinations.resolve_paths(
            nas_raw_data_path=nas_root.joinpath(project_name, animal_id, session_name, "raw_data"),
            server_raw_data_path=biohpc_root.joinpath(project_name, animal_id, session_name, "raw_data"),
            server_configuration_path=biohpc_root.joinpath(project_name, "configuration"),
            server_processed_data_path=biohpc_workdir.joinpath(project_name, "processed_data"),
        )
        destinations.make_directories()

        # Packages the sections generated above into a SessionData instance
        instance = SessionData(
            project_name=project_configuration.project_name,
            animal_id=animal_id,
            session_name=session_name,
            session_type=session_type,
            raw_data=raw_data,
            deeplabcut_data=dlc_data,
            configuration_data=configuration_data,
            processed_data=processed_data,
            vrpc_persistent_data=vrpc_persistent_data,
            scanimagepc_persistent_data=scanimagepc_persistent_data,
            mesoscope_data=mesoscope_data,
            destinations=destinations,
            experiment_name=experiment_name,
        )

        # Saves the configured instance data to the session's folder, so that it can be reused during processing or
        # preprocessing
        instance._save()

        # Extracts and saves the necessary configuration classes to the session raw_data folder. Note, this list of
        # classes is not exhaustive. More classes are saved as part of the session runtime management class start() and
        # __init__() method runtimes:

        # Discovers and saves the necessary configuration class instances to the raw_data and the processed_data folders
        # of the managed session:
        # Project Configuration
        sh.copy2(
            src=instance.configuration_data.project_configuration_path,
            dst=instance.raw_data.project_configuration_path,
        )
        sh.copy2(
            src=instance.configuration_data.project_configuration_path,
            dst=instance.processed_data.project_configuration_path,
        )  # ProjectConfiguration and SessionData are saved to both raw and processed data folders.
        # Experiment Configuration, if the session type is Experiment.
        if experiment_name is not None:
            sh.copy2(
                src=instance.configuration_data.experiment_configuration_path,
                dst=instance.raw_data.experiment_configuration_path,
            )

        # Returns the initialized SessionData instance to caller
        return instance

    @classmethod
    def load(
        cls,
        session_path: Path,
        on_server: bool,
    ) -> "SessionData":
        """Loads the SessionData instance from the target session's session_data.yaml file.

        This method is used to load the data layout information of an already existing session. Primarily, this is used
        when preprocessing or processing session data. Depending on the call location (machine), the method
        automatically resolves all necessary paths and creates the necessary directories.

        Notes:
            To create a new session, use the create() method instead.

            Although session_data.yaml is stored both inside raw_data and processed_data subfolders, this method
            always searches only inside the raw_data folder. Storing session data in both folders is only used to ensure
            human experimenters can always trace all data in the lab back to the proper project, animal, and session.

        Args:
            session_path: The path to the root directory of an existing session, e.g.: vrpc_root/project/animal/session.
            on_server: Determines whether the method is used to initialize an existing session on the BioHPC server or
                a non-server machine. Note, non-server runtimes use the same 'root' directory to store raw_data and
                processed_data subfolders. BioHPC server runtimes use different volumes (drives) to store these
                subfolders.

        Returns:
            An initialized SessionData instance for the session whose data is stored at the provided path.

        Raises:
            FileNotFoundError: If the 'session_data.yaml' file is not found under the session_path/raw_data/ subfolder.
        """
        # To properly initialize the SessionData instance, the provided path should contain the raw_data directory
        # with session_data.yaml file.
        session_data_path = session_path.joinpath("raw_data", "session_data.yaml")
        if not session_data_path.exists():
            message = (
                f"Unable to load the SessionData class for the target session: {session_path.stem}. No "
                f"session_data.yaml file was found inside the raw_data folder of the session. This likely "
                f"indicates that the session runtime was interrupted before recording any data, or that the "
                f"session path does not point to a valid session."
            )
            console.error(message=message, error=FileNotFoundError)

        # Loads class data from .yaml file
        instance: SessionData = cls.from_yaml(file_path=session_data_path)  # type: ignore

        # The method assumes that the 'donor' .yaml file is always stored inside the raw_data directory of the session
        # to be processed. Since the directory itself might have moved (between or even within the same PC) relative to
        # where it was when the SessionData snapshot was generated, reconfigures the paths to all raw_data files using
        # the root from above.
        local_root = session_path.parents[2]

        # RAW DATA
        new_root = local_root.joinpath(instance.project_name, instance.animal_id, instance.session_name, "raw_data")
        instance.raw_data.resolve_paths(root_directory_path=new_root)
        instance.raw_data.make_directories()

        # Uses the adjusted raw_data section to load the ProjectConfiguration instance. This is used below to resolve
        # all other SessionData sections, as it stores various required root directories.
        project_configuration: ProjectConfiguration = ProjectConfiguration.load(
            project_name=instance.project_name,
            configuration_path=Path(instance.raw_data.project_configuration_path),
        )

        # Resolves the new roots for all sections that use the same root as the raw_data directory:

        # CONFIGURATION
        new_root = local_root.joinpath(instance.project_name, "configuration")
        instance.configuration_data.resolve_paths(
            root_directory_path=new_root,
            experiment_name=instance.experiment_name,
        )
        instance.configuration_data.make_directories()

        # DEEPLABCUT
        new_root = local_root.joinpath(instance.project_name, "deeplabcut")
        instance.deeplabcut_data.resolve_paths(root_directory_path=new_root)
        instance.deeplabcut_data.make_directories()

        # Resolves the roots for all VRPC-specific sections that use the data from the ProjectConfiguration instance:

        # VRPC PERSISTENT DATA
        new_root = Path(project_configuration.local_root_directory).joinpath(
            instance.project_name, instance.animal_id, "persistent_data"
        )
        instance.vrpc_persistent_data.resolve_paths(root_directory_path=new_root)

        # SCANIMAGEPC PERSISTENT DATA
        new_root = Path(project_configuration.local_mesoscope_directory).joinpath(
            instance.project_name, instance.animal_id, "persistent_data"
        )
        instance.scanimagepc_persistent_data.resolve_paths(root_directory_path=new_root)

        # MESOSCOPE DATA
        instance.mesoscope_data.resolve_paths(
            root_mesoscope_path=Path(project_configuration.local_mesoscope_directory),
            session_name=instance.session_name,
        )

        # DESTINATIONS
        instance.destinations.resolve_paths(
            nas_raw_data_path=Path(project_configuration.local_nas_directory).joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "raw_data"
            ),
            server_raw_data_path=Path(project_configuration.local_server_directory).joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "raw_data"
            ),
            server_configuration_path=Path(project_configuration.local_server_directory).joinpath(
                instance.project_name, "configuration"
            ),
            server_processed_data_path=Path(project_configuration.local_server_working_directory).joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "processed_data"
            ),
        )

        # Resolves the paths to the processed_data directories. The resolution strategy depends on whether the method is
        # called on the VRPC (locally) or the BioHPC server (remotely).
        if not on_server:
            # Local runtimes use the same root session directory for both raw_data and processed_data. This stems from
            # the assumption that most local machines in the lab only use NVME (fast) volumes and, therefore, do not
            # need to separate 'storage' and 'working' data directories.
            new_root = local_root  # Reuses the local root for non-server runtimes

        else:
            # The BioHPC server stores raw_data on slow volume and processed_data on fast (NVME) volume. Therefore, to
            # configure processed_data paths, the method first needs to load the fast volume root path from the
            # project_configuration.yaml file stored in the raw_data folder.
            new_root = Path(project_configuration.remote_working_directory)

        # Regenerates the processed_data path depending on the root resolution above
        instance.processed_data.resolve_paths(
            root_directory_path=new_root.joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "processed_data"
            )
        )
        instance.processed_data.make_directories()

        # Ensures that project configuration and session data classes are present in both raw_data and processed_data
        # directories. This ensures that all data of the session can always be traced to the parent project, animal,
        # and session.
        sh.copy2(
            src=instance.raw_data.session_data_path,
            dst=instance.processed_data.session_data_path,
        )
        sh.copy2(
            src=instance.raw_data.project_configuration_path,
            dst=instance.processed_data.project_configuration_path,
        )

        # Generates data directory hierarchies that may be missing on the local machine
        instance.raw_data.make_directories()
        instance.configuration_data.make_directories()
        instance.deeplabcut_data.make_directories()
        instance.processed_data.make_directories()

        # Returns the initialized SessionData instance to caller
        return instance

    def _save(self) -> None:
        """Saves the instance data to the 'raw_data' directory and the 'processed_data' directory of the managed session
         as a 'session_data.yaml' file.

        This is used to save the data stored in the instance to disk, so that it can be reused during preprocessing or
        data processing. The method is intended to only be used by the SessionData instance itself during its
        create() method runtime.
        """

        # Saves instance data as a .YAML file
        self.to_yaml(file_path=self.raw_data.session_data_path)
        self.to_yaml(file_path=self.processed_data.session_data_path)
