"""This module provides classes used to store various data used by other Sun lab data acquisition and processing
libraries.This includes classes used to store the data generated during acquisition and preprocessing and classes used
to manage the runtime of other libraries (configuration data classes). Most classes from these modules are used by the
major libraries 'sl-experiment' and 'sl-forgery'."""

import re
import copy
import shutil as sh
from pathlib import Path
import warnings
from dataclasses import field, dataclass

import appdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig
from ataraxis_time.time_helpers import get_timestamp

# Ensures console is enabled when this file is imported
if not console.enabled:
    console.enable()


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
    """The absolute path to the directory where all projects are stored on the BioHPC server. This directory should be 
    locally accessible (mounted) using a network sharing protocol, such as SMB."""
    local_nas_directory: str | Path = Path("/home/cybermouse/nas/rawdata")
    """The absolute path to the directory where all projects are stored on the Synology NAS. This directory should be 
    locally accessible (mounted) using a network sharing protocol, such as SMB."""
    local_mesoscope_directory: str | Path = Path("/home/cybermouse/scanimage/mesodata")
    """The absolute path to the root mesoscope (ScanImagePC) directory where all mesoscope-acquired data is aggregated 
    during acquisition runtime. This directory should be locally accessible (mounted) using a network sharing 
    protocol, such as SMB."""
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
    """Stores the paths to the directories and files that make up the 'raw_data' session directory.

    The raw_data directory stores the data acquired during the session runtime before and after preprocessing. Since
    preprocessing does not alter the data, any data in that folder is considered 'raw'. The raw_data folder is initially
    created on the VRPC and, after preprocessing, is copied to the BioHPC server and the Synology NAS for long-term
    storage and further processing.

    Notes:
        The overall structure of the raw_data directory remains fixed for the entire lifetime of the data. It is reused
        across all destinations.
    """

    raw_data_path: str | Path
    """Stores the path to the root raw_data directory of the session. This directory stores all raw data during 
    acquisition and preprocessing. Note, preprocessing does not alter raw data, so at any point in time all data inside
    the folder is considered 'raw'."""
    camera_data_path: str | Path
    """Stores the path to the directory that contains all camera data acquired during the session. Primarily, this 
    includes .mp4 video files from each recorded camera."""
    mesoscope_data_path: str | Path
    """Stores the path to the directory that contains all Mesoscope data acquired during the session. Primarily, this 
    includes the mesoscope-acquired .tiff files (brain activity data) and the motion estimation data."""
    behavior_data_path: str | Path
    """Stores the path to the directory that contains all behavior data acquired during the session. Primarily, this 
    includes the .npz log files used by data-acquisition libraries to store all acquired data. The data stored in this 
    way includes the camera and mesoscope frame timestamps and the states of Mesoscope-VR components, such as lick 
    sensors, rotary encoders, and other modules."""
    zaber_positions_path: str | Path
    """Stores the path to the zaber_positions.yaml file. This file contains the snapshot of all Zaber motor positions 
    at the end of the session. Zaber motors are used to position the LickPort and the HeadBar manipulators, which is 
    essential for supporting proper brain imaging and animal's running behavior during the session."""
    session_descriptor_path: str | Path
    """Stores the path to the session_descriptor.yaml file. This file is partially filled by the system during runtime 
    and partially by the experimenter after the runtime. It contains session-specific information, such as the specific
    training parameters, the positions of the Mesoscope objective and the notes made by the experimenter during 
    runtime."""
    hardware_configuration_path: str | Path
    """Stores the path to the hardware_configuration.yaml file. This file contains the partial snapshot of the 
    calibration parameters used by the Mesoscope-VR system components during runtime. Primarily, this is used during 
    data processing to read the .npz data log files generated during runtime."""
    surgery_metadata_path: str | Path
    """Stores the path to the surgery_metadata.yaml file. This file contains the most actual information about the 
    surgical intervention(s) performed on the animal prior to the session."""
    project_configuration_path: str | Path
    """Stores the path to the project_configuration.yaml file. This file contains the snapshot of the configuration 
    parameters for the session's project."""
    session_data_path: str | Path
    """Stores the path to the session_data.yaml file. This path is used b y the SessionData instance to save itself to 
    disk as a .yaml file. The file contains all paths used during data acquisition and processing on both the VRPC and 
    the BioHPC server."""
    experiment_configuration_path: str | Path
    """Stores the path to the experiment_configuration.yaml file. This file contains the snapshot of the 
    experiment runtime configuration used by the session. This file is only created for experiment session. It does not
    exist for behavior training sessions."""
    mesoscope_positions_path: str | Path
    """Stores the path to the mesoscope_positions.yaml file. This file contains the snapshot of the positions used
    by the Mesoscope at the end of the session. This includes both the physical position of the mesoscope objective and
    the 'virtual' tip, tilt, and fastZ positions set via ScanImage software. This file is only created for experiment 
    sessions that use the mesoscope, it is omitted for behavior training sessions."""
    window_screenshot_path: str | Path
    """Stores the path to the .png screenshot of the ScanImagePC screen. The screenshot should contain the image of the 
    cranial window and the red-dot alignment windows. This is used to generate a visual snapshot of the cranial window
    alignment and appearance for each experiment session. This file is only created for experiment sessions that use 
    the mesoscope, it is omitted for behavior training sessions."""

    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """

        self.raw_data_path = Path(self.raw_data_path)
        self.camera_data_path = Path(self.camera_data_path)
        self.mesoscope_data_path = Path(self.mesoscope_data_path)
        self.behavior_data_path = Path(self.behavior_data_path)
        self.zaber_positions_path = Path(self.zaber_positions_path)
        self.session_descriptor_path = Path(self.session_descriptor_path)
        self.hardware_configuration_path = Path(self.hardware_configuration_path)
        self.surgery_metadata_path = Path(self.surgery_metadata_path)
        self.project_configuration_path = Path(self.project_configuration_path)
        self.session_data_path = Path(self.session_data_path)
        self.experiment_configuration_path = Path(self.experiment_configuration_path)
        self.mesoscope_positions_path = Path(self.mesoscope_positions_path)
        self.window_screenshot_path = Path(self.window_screenshot_path)

    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
        self.raw_data_path = str(self.raw_data_path)
        self.camera_data_path = str(self.camera_data_path)
        self.mesoscope_data_path = str(self.mesoscope_data_path)
        self.behavior_data_path = str(self.behavior_data_path)
        self.zaber_positions_path = str(self.zaber_positions_path)
        self.session_descriptor_path = str(self.session_descriptor_path)
        self.hardware_configuration_path = str(self.hardware_configuration_path)
        self.surgery_metadata_path = str(self.surgery_metadata_path)
        self.project_configuration_path = str(self.project_configuration_path)
        self.session_data_path = str(self.session_data_path)
        self.experiment_configuration_path = str(self.experiment_configuration_path)
        self.mesoscope_positions_path = str(self.mesoscope_positions_path)
        self.window_screenshot_path = str(self.window_screenshot_path)

    def make_dirs(self) -> None:
        """Ensures that all major subdirectories and the root raw_data directory exist.

        This method is used by the VRPC to generate the raw_data directory when it creates a new session.
        """
        ensure_directory_exists(Path(self.raw_data_path))
        ensure_directory_exists(Path(self.camera_data_path))
        ensure_directory_exists(Path(self.mesoscope_data_path))
        ensure_directory_exists(Path(self.behavior_data_path))

    def switch_root(self, new_root: Path) -> None:
        """Changes the root of the managed raw_data directory to the provided root path.

        This service method is used by the SessionData class to convert all paths in this class to be relative to the
        new root. This is used to adjust the SessionData instance to work for the VRPC (one root) or the BioHPC server
        (another root). This method is only implemented for subclasses intended to be used both locally and on the
        BioHPC server.

        Args:
            new_root: The new root directory to use for all paths inside the instance. This has to be the path to the
                directory that stores all Sun lab projects on the target machine.
        """
        # Gets current root from the raw_data_path.
        old_root = Path(self.raw_data_path).parents[3]

        # Updates all paths by replacing old_root with new_root
        self.raw_data_path = new_root.joinpath(Path(self.raw_data_path).relative_to(old_root))
        self.camera_data_path = new_root.joinpath(Path(self.camera_data_path).relative_to(old_root))
        self.mesoscope_data_path = new_root.joinpath(Path(self.mesoscope_data_path).relative_to(old_root))
        self.behavior_data_path = new_root.joinpath(Path(self.behavior_data_path).relative_to(old_root))
        self.zaber_positions_path = new_root.joinpath(Path(self.zaber_positions_path).relative_to(old_root))
        self.session_descriptor_path = new_root.joinpath(Path(self.session_descriptor_path).relative_to(old_root))
        self.hardware_configuration_path = new_root.joinpath(
            Path(self.hardware_configuration_path).relative_to(old_root)
        )
        self.surgery_metadata_path = new_root.joinpath(Path(self.surgery_metadata_path).relative_to(old_root))
        self.project_configuration_path = new_root.joinpath(Path(self.project_configuration_path).relative_to(old_root))
        self.session_data_path = new_root.joinpath(Path(self.session_data_path).relative_to(old_root))
        self.experiment_configuration_path = new_root.joinpath(
            Path(self.experiment_configuration_path).relative_to(old_root)
        )
        self.mesoscope_positions_path = new_root.joinpath(Path(self.mesoscope_positions_path).relative_to(old_root))
        self.window_screenshot_path = new_root.joinpath(Path(self.window_screenshot_path).relative_to(old_root))


@dataclass()
class ProcessedData:
    """Stores the paths to the directories and files that make up the 'processed_data' session directory.

    The processed_data directory stores the data generated by various processing pipelines from the raw data. Processed
    data represents an intermediate step between raw data and the dataset used in the data analysis, but is not itself
    designed to be analyzed.

    Notes:
        The paths from this section are typically used only on the BioHPC server. This is because most data processing
        in the lab is performed using the processing server's resources. On the server, processed data is stored on
        the fast volume, in contrast to raw data, which is stored on the slow volume. However, to support local testing,
        the class resolves the paths in this section both locally and globally (on the server).

    """

    processed_data_path: str | Path
    """Stores the path to the root processed_data directory of the session. This directory stores the processed data 
    as it is generated by various data processing pipelines."""
    camera_data_path: str | Path
    """Stores the output of the DeepLabCut pose estimation pipeline."""
    mesoscope_data_path: str | Path
    """Stores the output of the suite2p cell registration pipeline."""
    behavior_data_path: str | Path
    """Stores the output of the Sun lab behavior data extraction pipeline."""
    deeplabcut_root_path: str | Path
    """Stores the path to the root DeepLabCut project directory. Since DeepLabCut adopts a project-based directory 
    management hierarchy, it is easier to have a single DLC folder shared by all animals and sessions of a given 
    project. This root folder is typically stored under the main project directory on the fast BioHPC server volume."""
    suite2p_configuration_path: str | Path
    """Stores the path to the suite2p_configuration.yaml file stored inside the project's 'configuration' directory on
    the fast BioHPC server volume. Since all sessions share the same suite2p configuration file, it is stored in a 
    general configuration directory, similar to how project configuration is stored on the VRPC."""

    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """

        self.processed_data_path = Path(self.processed_data_path)
        self.camera_data_path = Path(self.camera_data_path)
        self.mesoscope_data_path = Path(self.mesoscope_data_path)
        self.behavior_data_path = Path(self.behavior_data_path)
        self.deeplabcut_root_path = Path(self.deeplabcut_root_path)
        self.suite2p_configuration_path = Path(self.suite2p_configuration_path)

    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
        self.processed_data_path = str(self.processed_data_path)
        self.camera_data_path = str(self.camera_data_path)
        self.mesoscope_data_path = str(self.mesoscope_data_path)
        self.behavior_data_path = str(self.behavior_data_path)
        self.deeplabcut_root_path = str(self.deeplabcut_root_path)
        self.suite2p_configuration_path = str(self.suite2p_configuration_path)

    def make_dirs(self) -> None:
        """Ensures that all major subdirectories of the processed_data directory exist.

        This method is used by the BioHPC server to generate the processed_data directory as part of the sl-forgery
        library runtime.
        """
        ensure_directory_exists(Path(self.processed_data_path))
        ensure_directory_exists(Path(self.camera_data_path))
        ensure_directory_exists(Path(self.mesoscope_data_path))
        ensure_directory_exists(Path(self.behavior_data_path))
        ensure_directory_exists(Path(self.deeplabcut_root_path))
        ensure_directory_exists(Path(self.suite2p_configuration_path))

    def switch_root(self, new_root: Path) -> None:
        """Changes the root of the managed processed_data directory to the provided root path.

        This service method is used by the SessionData class to convert all paths in this class to be relative to the
        new root. This is used to adjust the SessionData instance to work for the VRPC (one root) or the BioHPC server
        (another root). This method is only implemented for subclasses intended to be used both locally and on the
        BioHPC server.

        Args:
            new_root: The new root directory to use for all paths inside the instance. This has to be the path to the
                directory that stores all Sun lab projects on the target machine.
        """
        # Gets current root from the processed_data_path.
        old_root = Path(self.processed_data_path).parents[3]

        # Updates all paths by replacing old_root with new_root
        self.processed_data_path = new_root.joinpath(Path(self.processed_data_path).relative_to(old_root))
        self.camera_data_path = new_root.joinpath(Path(self.camera_data_path).relative_to(old_root))
        self.mesoscope_data_path = new_root.joinpath(Path(self.mesoscope_data_path).relative_to(old_root))
        self.behavior_data_path = new_root.joinpath(Path(self.behavior_data_path).relative_to(old_root))
        self.deeplabcut_root_path = new_root.joinpath(Path(self.deeplabcut_root_path).relative_to(old_root))
        self.suite2p_configuration_path = new_root.joinpath(Path(self.suite2p_configuration_path).relative_to(old_root))


@dataclass()
class PersistentData:
    """Stores the paths to the directories and files that make up the 'persistent_data' directories of the VRPC and
    the ScanImagePC.

    Persistent data directories are used to keep certain files on the VRPC and the ScanImagePC. Typically, this data
    is reused during the following sessions. For example, a copy of Zaber motor positions is persisted on the VRPC for
    each animal after every session to support automatically restoring Zaber motors to the positions used during the
    previous session.

    Notes:
        Persistent data includes the project and experiment configuration data. Some persistent data is overwritten
        after each session, other data is generated once and kept through the animal's lifetime. Primarily, this data is
        only used internally by the sl-experiment or sl-forgery libraries and is not intended for end-users.
    """

    zaber_positions_path: str | Path
    """Stores the path to the Zaber motor positions snapshot generated at the end of the previous session runtime. This 
    is used to automatically restore all Zaber motors to the same position across all sessions."""
    mesoscope_positions_path: str | Path
    """Stores the path to the Mesoscope positions snapshot generated at the end of the previous session runtime. This 
    is used to help the user to (manually) restore the Mesoscope to the same position across all sessions."""
    motion_estimator_path: str | Path
    """Stores the 'reference' motion estimator file generated during the first experiment session of each animal. This 
    file is kept on the ScanImagePC to image the same population of cells across all experiment sessions."""

    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """

        self.zaber_positions_path = Path(self.zaber_positions_path)
        self.mesoscope_positions_path = Path(self.mesoscope_positions_path)
        self.motion_estimator_path = Path(self.motion_estimator_path)

    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
        self.zaber_positions_path = str(self.zaber_positions_path)
        self.mesoscope_positions_path = str(self.mesoscope_positions_path)
        self.motion_estimator_path = str(self.motion_estimator_path)

    def make_dirs(self) -> None:
        """Ensures that the VRPC and the ScanImagePC persistent_data directories exist."""

        # We need to call ensure_directory_exists one for each unique directory tree
        ensure_directory_exists(Path(self.zaber_positions_path))  # vrpc_root/project/animal/persistent_data
        ensure_directory_exists(Path(self.motion_estimator_path))  # scanimagepc_root/project/animal/persistent_data


@dataclass()
class MesoscopeData:
    """Stores the paths to the directories used by the ScanImagePC to save mesoscope-generated data during session
    runtime.

    The ScanImagePC is largely isolated from the VRPC during runtime. For the VRPC to pull the data acquired by the
    ScanImagePC, it has to use the predefined directory structure to save the data. This class stores the predefined
    path to various directories where ScanImagePC is expected to save the data and store it after acquisition.sers.
    """

    root_data_path: str | Path
    """Stores the path to the root ScanImagePC data directory, mounted to the VRPC filesystem via the SMB or equivalent 
    protocol. This path is used during experiment session runtimes to discover the cranial window screenshots 
    taken by the user before starting the experiment."""
    mesoscope_data_path: str | Path
    """Stores the path to the 'general' mesoscope_data directory. All experiment sessions (across all animals and 
    projects) use the same mesoscope_data directory to save the data generated by the mesoscope via ScanImage 
    software. This simplifies ScanImagePC configuration process during runtime. The data is moved into a 
    session-specific directory during preprocessing."""
    session_specific_mesoscope_data_path: str | Path
    """Stores the path to the session-specific mesoscope_data directory. This directory is generated at the end of 
    each experiment runtime to prepare mesoscope data for further processing and to reset the 'shared' folder for the 
    next session's runtime."""

    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """
        self.root_data_path = Path(self.root_data_path)
        self.mesoscope_data_path = Path(self.mesoscope_data_path)
        self.session_specific_mesoscope_data_path = Path(self.session_specific_mesoscope_data_path)

    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
        self.root_data_path = str(self.root_data_path)
        self.mesoscope_data_path = str(self.mesoscope_data_path)
        self.session_specific_mesoscope_data_path = str(self.session_specific_mesoscope_data_path)

    def make_dirs(self) -> None:
        """Ensures that the ScanImagePC data acquisition directories exist."""

        # Does not create the session-specific directory. This is on purpose, as the session-specific directory
        # is generated during runtime by renaming the 'general' mesoscope_data directory. The 'general' directory is
        # then recreated from scratch. This ensures that the general directory is empty (ready for the next session)
        # with minimal I/O overhead.
        ensure_directory_exists(Path(self.mesoscope_data_path))


@dataclass()
class Destinations:
    """Stores the paths to the VRPC filesystem-mounted Synology NAS and BioHPC server directories.

    These directories are used during data preprocessing to transfer the preprocessed raw_data directory from the
    VRPC to the long-term storage destinations.
    """

    nas_raw_data_path: str | Path
    """Stores the path to the session's raw_data directory on the Synology NAS, which is mounted to the VRPC via the 
    SMB or equivalent protocol."""
    server_raw_data_path: str | Path
    """Stores the path to the session's raw_data directory on the BioHPC server, which is mounted to the VRPC via the 
    SMB or equivalent protocol."""

    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """
        self.nas_raw_data_path = Path(self.nas_raw_data_path)
        self.server_raw_data_path = Path(self.server_raw_data_path)

    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
        self.nas_raw_data_path = str(self.nas_raw_data_path)
        self.server_raw_data_path = str(self.server_raw_data_path)

    def make_dirs(self) -> None:
        """Ensures that all destination directories exist."""
        ensure_directory_exists(Path(self.nas_raw_data_path))
        ensure_directory_exists(Path(self.server_raw_data_path))


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
    raw_data: RawData
    """This section stores the paths to various directories and files that make up the raw_data subfolder. This 
    subfolder stores all data acquired during training or experiment runtimes before and after preprocessing. Note, the 
    preprocessing does not change the raw data in any way other than lossless compression and minor format 
    reorganization. Therefore, the data is considered 'raw' both before and after preprocessing."""
    processed_data: ProcessedData
    """This section stores the paths to various directories used to store processed session data. Processed data is 
    generated from raw data by running various processing pipelines, such as suite2p, DeepLabCut and Sun lab's behavior 
    parsing pipelines. Typically, all data is processed on the BioHPC server and may be stored on a filesystem volume 
    different from the one that stores the raw data."""
    persistent_data: PersistentData
    """This section stores the paths to various files and directories that are held back on the VRPC and ScanImagePC 
    after the session data is transferred to long-term storage destinations as part of preprocessing. Typically, this 
    data is reused during the acquisition of future runtime session data. This section is not used during data 
    processing."""
    mesoscope_data: MesoscopeData
    """This section stores the paths to various directories used by the ScanImagePC when acquiring mesoscope-related 
    data. During runtime, the VRPC (behavior data and experiment control) and the ScanImagePC (brain activity data and 
    Mesoscope control) operate mostly independently of each-other. During preprocessing, the VRPC pulls the data from 
    the ScanImagePC, using the paths in this section to find the data to be transferred. This section is not used 
    during data processing."""
    destinations: Destinations
    """This section stores the paths to the destination directories on the BioHPC server and Synology NAS, to which the 
    data is copied as part of preprocessing for long-term storage and further processing. Both of these directories 
    should be mapped (mounted) to the VRPC's filesystem via the SMB or equivalent protocol. This section is not used 
    during data processing."""

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

        # Extracts the root directory paths stored inside the project configuration file. All roots are expected to be
        # mounted on the local (VRPC) via SMB or equivalent protocol and be relative to the VRPC root.
        vrpc_root = Path(project_configuration.local_root_directory)
        mesoscope_root = Path(project_configuration.local_mesoscope_directory)
        biohpc_root = Path(project_configuration.local_server_directory)
        nas_root = Path(project_configuration.local_nas_directory)

        # Extracts the name of the project stored inside the project configuration file.
        project_name = project_configuration.project_name

        # Constructs the session directory path and generates the directory
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
            warnings.warn(message=message)

        # Generates subclasses stored inside the main class instance based on the data resolved above.
        raw_data = RawData(
            raw_data_path=session_path.joinpath("raw_data"),
            camera_data_path=session_path.joinpath("raw_data", "camera_data"),
            mesoscope_data_path=session_path.joinpath("raw_data", "mesoscope_data"),
            behavior_data_path=session_path.joinpath("raw_data", "behavior_data"),
            zaber_positions_path=session_path.joinpath("raw_data", "zaber_positions.yaml"),
            mesoscope_positions_path=session_path.joinpath("raw_data", "mesoscope_positions.yaml"),
            session_descriptor_path=session_path.joinpath("raw_data", "session_descriptor.yaml"),
            hardware_configuration_path=session_path.joinpath("raw_data", "hardware_configuration.yaml"),
            surgery_metadata_path=session_path.joinpath("raw_data", "surgery_metadata.yaml"),
            project_configuration_path=session_path.joinpath("raw_data", "project_configuration.yaml"),
            session_data_path=session_path.joinpath("raw_data", "session_data.yaml"),
            experiment_configuration_path=session_path.joinpath("raw_data", "experiment_configuration.yaml"),
            window_screenshot_path=session_path.joinpath("raw_data", "window_screenshot.png"),
        )
        raw_data.make_dirs()  # Generates the local directory tree

        processed_data = ProcessedData(
            processed_data_path=session_path.joinpath("processed_data"),
            camera_data_path=session_path.joinpath("processed_data", "camera_data"),
            mesoscope_data_path=session_path.joinpath("processed_data", "mesoscope_data"),
            behavior_data_path=session_path.joinpath("processed_data", "behavior_data"),
            deeplabcut_root_path=vrpc_root.joinpath(project_name, "deeplabcut"),
            suite2p_configuration_path=vrpc_root.joinpath(project_name, "configuration", "suite2p_configuration.yaml"),
        )

        vrpc_persistent_path = vrpc_root.joinpath(project_name, animal_id, "persistent_data")
        scanimagepc_persistent_path = mesoscope_root.joinpath(project_name, animal_id, "persistent_data")
        persistent_data = PersistentData(
            zaber_positions_path=vrpc_persistent_path.joinpath("zaber_positions.yaml"),
            mesoscope_positions_path=vrpc_persistent_path.joinpath("mesoscope_positions.yaml"),
            motion_estimator_path=scanimagepc_persistent_path.joinpath("MotionEstimator.me"),
        )
        persistent_data.make_dirs()  # Generates all persistent directory trees

        mesoscope_data = MesoscopeData(
            root_data_path=mesoscope_root,
            mesoscope_data_path=mesoscope_root.joinpath("mesoscope_data"),
            session_specific_mesoscope_data_path=mesoscope_root.joinpath(f"{session_name}_mesoscope_data"),
        )
        mesoscope_data.make_dirs()  # Generates all Mesoscope directory trees

        destinations = Destinations(
            nas_raw_data_path=nas_root.joinpath(project_name, animal_id, session_name, "raw_data"),
            server_raw_data_path=biohpc_root.joinpath(project_name, animal_id, session_name, "raw_data"),
        )
        destinations.make_dirs()  # Generates all destination directory trees

        # Packages the sections generated above into a SessionData instance
        instance = SessionData(
            project_name=project_configuration.project_name,
            animal_id=animal_id,
            session_name=session_name,
            session_type=session_type,
            raw_data=raw_data,
            processed_data=processed_data,
            persistent_data=persistent_data,
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

        # Resolves the path to the project configuration folder
        vrpc_configuration_path = vrpc_root.joinpath(project_name, "configuration")

        # Discovers and saves the necessary configuration class instances to the raw_data folder of the managed session:
        # Project Configuration
        sh.copy2(
            src=vrpc_configuration_path.joinpath("project_configuration.yaml"),
            dst=instance.raw_data.project_configuration_path,
        )
        # Experiment Configuration, if the session type is Experiment.
        if experiment_name is not None:
            sh.copy2(
                src=vrpc_configuration_path.joinpath(f"{experiment_name}.yaml"),
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

        Args:
            session_path: The path to the root directory of an existing session, e.g.: vrpc_root/project/animal/session.
            on_server: Determines whether the method is used to initialize an existing session on the VRPC or the
                BioHPC server. Note, VRPC runtimes use the same 'root' directory to store raw_data and processed_data
                subfolders. BioHPC server runtimes use different volumes (drives) to store these subfolders.

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

        # Loads class data from .yaml
        instance: SessionData = cls.from_yaml(file_path=session_data_path)  # type: ignore

        # The method assumes that the 'donor' .yaml file is always stored inside the raw_data directory of the session
        # to be processed. Since the directory itself might have moved (between or even within the same PC) relative to
        # where it was when the SessionData snapshot was generated, reconfigures the paths to all raw_data files using
        # the root from above.
        instance.raw_data.switch_root(new_root=session_path.parents[2])

        # Resolves the paths to the processed_data directories. The resolution strategy depends on whether the method is
        # called on the VRPC (locally) or the BioHPC server (remotely).
        if not on_server:
            # Local runtimes use the same root session directory for both raw_data and processed_data. This stems from
            # the assumption that most local machines in the lab only use NVME (fast) volumes and, therefore, do not
            # need to separate 'storage' and 'working' data.
            instance.processed_data.switch_root(new_root=session_path.parents[2])

        else:
            # The BioHPC server stores raw_data on slow volume and processed_data on fast (NVME) volume. Therefore, to
            # configure processed_data paths, the method first needs to load the fast volume root path from the
            # project_configuration.yaml file stored in the raw_data folder.
            project_configuration: ProjectConfiguration = ProjectConfiguration.load(
                project_name=instance.project_name,
                configuration_path=Path(instance.raw_data.project_configuration_path),
            )
            instance.processed_data.switch_root(new_root=Path(project_configuration.remote_working_directory))

        # Generates processed_data directories
        instance.processed_data.make_dirs()

        # Returns the initialized SessionData instance to caller
        return instance

    def _save(self) -> None:
        """Saves the instance data to the 'raw_data' directory of the managed session as a 'session_data.yaml' file.

        This is used to save the data stored in the instance to disk, so that it can be reused during preprocessing or
        data processing. The method is intended to only be used by the SessionData instance itself during its
        create() method runtime.
        """

        # Copies instance data to prevent it from being modified by reference when executing the steps below
        original = copy.deepcopy(self)

        # Extracts the target file path before it is converted to a string.
        file_path: Path = copy.copy(self.raw_data.session_data_path)  # type: ignore

        # Converts all Paths objects to strings before dumping the data to YAML.
        original.raw_data.make_string()
        original.processed_data.make_string()
        original.persistent_data.make_string()
        original.mesoscope_data.make_string()
        original.destinations.make_string()

        # Saves instance data as a .YAML file
        original.to_yaml(file_path=file_path)


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
class HardwareConfiguration(YamlConfig):
    """This class is used to save the runtime hardware configuration parameters as a .yaml file.

    This information is used to read and decode the data saved to the .npz log files during runtime as part of data
    processing.

    Notes:
        All fields in this dataclass initialize to None. During log processing, any log associated with a hardware
        module that provides the data stored in a field will be processed, unless that field is None. Therefore, setting
        any field in this dataclass to None also functions as a flag for whether to parse the log associated with the
        module that provides this field's information.

        This class is automatically configured by MesoscopeExperiment and BehaviorTraining classes from sl-experiment
        library to facilitate log parsing.
    """

    cue_map: dict[int, float] | None = None
    """MesoscopeExperiment instance property. Stores the dictionary that maps the integer id-codes associated with each 
    wall cue in the Virtual Reality task environment with distances in real-world centimeters animals should run on the 
    wheel to fully traverse the cue region on a linearized track."""
    cm_per_pulse: float | None = None
    """EncoderInterface instance property. Stores the conversion factor used to translate encoder pulses into 
    real-world centimeters."""
    maximum_break_strength: float | None = None
    """BreakInterface instance property. Stores the breaking torque, in Newton centimeters, applied by the break to 
    the edge of the running wheel when it is engaged at 100% strength."""
    minimum_break_strength: float | None = None
    """BreakInterface instance property. Stores the breaking torque, in Newton centimeters, applied by the break to 
    the edge of the running wheel when it is engaged at 0% strength (completely disengaged)."""
    lick_threshold: int | None = None
    """LickInterface instance property. Determines the threshold, in 12-bit Analog to Digital Converter (ADC) units, 
    above which an interaction value reported by the lick sensor is considered a lick (compared to noise or non-lick 
    touch)."""
    valve_scale_coefficient: float | None = None
    """ValveInterface instance property. To dispense precise water volumes during runtime, ValveInterface uses power 
    law equation applied to valve calibration data to determine how long to keep the valve open. This stores the 
    scale_coefficient of the power law equation that describes the relationship between valve open time and dispensed 
    water volume, derived from calibration data."""
    valve_nonlinearity_exponent: float | None = None
    """ValveInterface instance property. To dispense precise water volumes during runtime, ValveInterface uses power 
    law equation applied to valve calibration data to determine how long to keep the valve open. This stores the 
    nonlinearity_exponent of the power law equation that describes the relationship between valve open time and 
    dispensed water volume, derived from calibration data."""
    torque_per_adc_unit: float | None = None
    """TorqueInterface instance property. Stores the conversion factor used to translate torque values reported by the 
    sensor as 12-bit Analog to Digital Converter (ADC) units, into real-world Newton centimeters (N·cm) of torque that 
    had to be applied to the edge of the running wheel to produce the observed ADC value."""
    screens_initially_on: bool | None = None
    """ScreenInterface instance property. Stores the initial state of the Virtual Reality screens at the beginning of 
    the session runtime."""
    recorded_mesoscope_ttl: bool | None = None
    """TTLInterface instance property. A boolean flag that determines whether the processed session recorded brain 
    activity data with the mesoscope."""


@dataclass()
class LickTrainingDescriptor(YamlConfig):
    """This class is used to save the description information specific to lick training sessions as a .yaml file.

    The information stored in this class instance is filled in two steps. The main runtime function fills most fields
    of the class, before it is saved as a .yaml file. After runtime, the experimenter manually fills leftover fields,
    such as 'experimenter_notes,' before the class instance is transferred to the long-term storage destination.

    The fully filled instance data is also used during preprocessing to write the water restriction log entry for the
    trained animal.
    """

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    dispensed_water_volume_ml: float
    """Stores the total water volume, in milliliters, dispensed during runtime."""
    minimum_reward_delay: int
    """Stores the minimum delay, in seconds, that can separate the delivery of two consecutive water rewards."""
    maximum_reward_delay_s: int
    """Stores the maximum delay, in seconds, that can separate the delivery of two consecutive water rewards."""
    maximum_water_volume_ml: float
    """Stores the maximum volume of water the system is allowed to dispense during training."""
    maximum_training_time_m: int
    """Stores the maximum time, in minutes, the system is allowed to run the training for."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter replaces this field with their 
    notes made during runtime."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """


@dataclass()
class RunTrainingDescriptor(YamlConfig):
    """This class is used to save the description information specific to run training sessions as a .yaml file.

    The information stored in this class instance is filled in two steps. The main runtime function fills most fields
    of the class, before it is saved as a .yaml file. After runtime, the experimenter manually fills leftover fields,
    such as 'experimenter_notes,' before the class instance is transferred to the long-term storage destination.

    The fully filled instance data is also used during preprocessing to write the water restriction log entry for the
    trained animal.
    """

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    dispensed_water_volume_ml: float
    """Stores the total water volume, in milliliters, dispensed during runtime."""
    final_run_speed_threshold_cm_s: float
    """Stores the final running speed threshold, in centimeters per second, that was active at the end of training."""
    final_run_duration_threshold_s: float
    """Stores the final running duration threshold, in seconds, that was active at the end of training."""
    initial_run_speed_threshold_cm_s: float
    """Stores the initial running speed threshold, in centimeters per second, used during training."""
    initial_run_duration_threshold_s: float
    """Stores the initial running duration threshold, in seconds, used during training."""
    increase_threshold_ml: float
    """Stores the volume of water delivered to the animal, in milliliters, that triggers the increase in the running 
    speed and duration thresholds."""
    run_speed_increase_step_cm_s: float
    """Stores the value, in centimeters per second, used by the system to increment the running speed threshold each 
    time the animal receives 'increase_threshold' volume of water."""
    run_duration_increase_step_s: float
    """Stores the value, in seconds, used by the system to increment the duration threshold each time the animal 
    receives 'increase_threshold' volume of water."""
    maximum_water_volume_ml: float
    """Stores the maximum volume of water the system is allowed to dispense during training."""
    maximum_training_time_m: int
    """Stores the maximum time, in minutes, the system is allowed to run the training for."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter will replace this field with their 
    notes made during runtime."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """


@dataclass()
class MesoscopeExperimentDescriptor(YamlConfig):
    """This class is used to save the description information specific to experiment sessions as a .yaml file.

    The information stored in this class instance is filled in two steps. The main runtime function fills most fields
    of the class, before it is saved as a .yaml file. After runtime, the experimenter manually fills leftover fields,
    such as 'experimenter_notes,' before the class instance is transferred to the long-term storage destination.

    The fully filled instance data is also used during preprocessing to write the water restriction log entry for the
    animal participating in the experiment runtime.
    """

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    dispensed_water_volume_ml: float
    """Stores the total water volume, in milliliters, dispensed during runtime."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter will replace this field with their 
    notes made during runtime."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """


@dataclass()
class ZaberPositions(YamlConfig):
    """This class is used to save Zaber motor positions as a .yaml file to reuse them between sessions.

    The class is specifically designed to store, save, and load the positions of the LickPort and HeadBar motors
    (axes). It is used to both store Zaber motor positions for each session for future analysis and to restore the same
    Zaber motor positions across consecutive runtimes for the same project and animal combination.

    Notes:
        All positions are saved using native motor units. All class fields initialize to default placeholders that are
        likely NOT safe to apply to the VR system. Do not apply the positions loaded from the file unless you are
        certain they are safe to use.

        Exercise caution when working with Zaber motors. The motors are powerful enough to damage the surrounding
        equipment and manipulated objects. Do not modify the data stored inside the .yaml file unless you know what you
        are doing.
    """

    headbar_z: int = 0
    """The absolute position, in native motor units, of the HeadBar z-axis motor."""
    headbar_pitch: int = 0
    """The absolute position, in native motor units, of the HeadBar pitch-axis motor."""
    headbar_roll: int = 0
    """The absolute position, in native motor units, of the HeadBar roll-axis motor."""
    lickport_z: int = 0
    """The absolute position, in native motor units, of the LickPort z-axis motor."""
    lickport_x: int = 0
    """The absolute position, in native motor units, of the LickPort x-axis motor."""
    lickport_y: int = 0
    """The absolute position, in native motor units, of the LickPort y-axis motor."""


@dataclass()
class MesoscopePositions(YamlConfig):
    """This class is used to save the real and virtual Mesoscope objective positions as a .yaml file to reuse it
    between experiment sessions.

    Primarily, the class is used to help the experimenter to position the Mesoscope at the same position across
    multiple imaging sessions. It stores both the physical (real) position of the objective along the motorized
    X, Y, Z, and Roll axes and the virtual (ScanImage software) tip, tilt, and fastZ focus axes.

    Notes:
        Since the API to read and write these positions automatically is currently not available, this class relies on
        the experimenter manually entering all positions and setting the mesoscope to these positions when necessary.
    """

    mesoscope_x_position: float = 0.0
    """The X-axis position, in centimeters, of the Mesoscope objective used during session runtime."""
    mesoscope_y_position: float = 0.0
    """The Y-axis position, in centimeters, of the Mesoscope objective used during session runtime."""
    mesoscope_roll_position: float = 0.0
    """The Roll-axis position, in degrees, of the Mesoscope objective used during session runtime."""
    mesoscope_z_position: float = 0.0
    """The Z-axis position, in centimeters, of the Mesoscope objective used during session runtime."""
    mesoscope_fast_z_position: float = 0.0
    """The Fast-Z-axis position, in micrometers, of the Mesoscope objective used during session runtime."""
    mesoscope_tip_position: float = 0.0
    """The Tilt-axis position, in degrees, of the Mesoscope objective used during session runtime."""
    mesoscope_tilt_position: float = 0.0
    """The Tip-axis position, in degrees, of the Mesoscope objective used during session runtime."""


@dataclass()
class SubjectData:
    """Stores the ID information of the surgical intervention's subject (animal)."""

    id: int
    """Stores the unique ID (name) of the subject. Assumes all animals are given a numeric ID, rather than a string 
    name."""
    ear_punch: str
    """Stores the ear tag location of the subject."""
    sex: str
    """Stores the gender of the subject."""
    genotype: str
    """Stores the genotype of the subject."""
    date_of_birth_us: int
    """Stores the date of birth of the subject as the number of microseconds elapsed since UTC epoch onset."""
    weight_g: float
    """Stores the weight of the subject pre-surgery, in grams."""
    cage: int
    """Stores the number of the cage used to house the subject after surgery."""
    location_housed: str
    """Stores the location used to house the subject after the surgery."""
    status: str
    """Stores the current status of the subject (alive / deceased)."""


@dataclass()
class ProcedureData:
    """Stores the general information about the surgical intervention."""

    surgery_start_us: int
    """Stores the date and time when the surgery has started as microseconds elapsed since UTC epoch onset."""
    surgery_end_us: int
    """Stores the date and time when the surgery has ended as microseconds elapsed since UTC epoch onset."""
    surgeon: str
    """Stores the name or ID of the surgeon. If the intervention was carried out by multiple surgeons, all participating
    surgeon names and IDs are stored as part of the same string."""
    protocol: str
    """Stores the experiment protocol number (ID) used during the surgery."""
    surgery_notes: str
    """Stores surgeon's notes taken during the surgery."""
    post_op_notes: str
    """Stores surgeon's notes taken during the post-surgery recovery period."""
    surgery_quality: int = 0
    """Stores the quality of the surgical intervention as a numeric level. 0 indicates unusable (bad) result, 1 
    indicates usable result that is not good enough to be included in a publication, 2 indicates publication-grade 
    result."""


@dataclass
class ImplantData:
    """Stores the information about a single implantation performed during the surgical intervention.

    Multiple ImplantData instances are used at the same time if the surgery involved multiple implants.
    """

    implant: str
    """The descriptive name of the implant."""
    implant_target: str
    """The name of the brain region or cranium section targeted by the implant."""
    implant_code: int
    """The manufacturer code or internal reference code for the implant. This code is used to identify the implant in 
    additional datasheets and lab ordering documents."""
    implant_ap_coordinate_mm: float
    """Stores implant's antero-posterior stereotactic coordinate, in millimeters, relative to bregma."""
    implant_ml_coordinate_mm: float
    """Stores implant's medial-lateral stereotactic coordinate, in millimeters, relative to bregma."""
    implant_dv_coordinate_mm: float
    """Stores implant's dorsal-ventral stereotactic coordinate, in millimeters, relative to bregma."""


@dataclass
class InjectionData:
    """Stores the information about a single injection performed during surgical intervention.

    Multiple InjectionData instances are used at the same time if the surgery involved multiple injections.
    """

    injection: str
    """The descriptive name of the injection."""
    injection_target: str
    """The name of the brain region targeted by the injection."""
    injection_volume_nl: float
    """The volume of substance, in nanoliters, delivered during the injection."""
    injection_code: int
    """The manufacturer code or internal reference code for the injected substance. This code is used to identify the 
    substance in additional datasheets and lab ordering documents."""
    injection_ap_coordinate_mm: float
    """Stores injection's antero-posterior stereotactic coordinate, in millimeters, relative to bregma."""
    injection_ml_coordinate_mm: float
    """Stores injection's medial-lateral stereotactic coordinate, in millimeters, relative to bregma."""
    injection_dv_coordinate_mm: float
    """Stores injection's dorsal-ventral stereotactic coordinate, in millimeters, relative to bregma."""


@dataclass
class DrugData:
    """Stores the information about all drugs administered to the subject before, during, and immediately after the
    surgical intervention.
    """

    lactated_ringers_solution_volume_ml: float
    """Stores the volume of Lactated Ringer's Solution (LRS) administered during surgery, in ml."""
    lactated_ringers_solution_code: int
    """Stores the manufacturer code or internal reference code for Lactated Ringer's Solution (LRS). This code is used 
    to identify the LRS batch in additional datasheets and lab ordering documents."""
    ketoprofen_volume_ml: float
    """Stores the volume of ketoprofen diluted with saline administered during surgery, in ml."""
    ketoprofen_code: int
    """Stores the manufacturer code or internal reference code for ketoprofen. This code is used to identify the 
    ketoprofen batch in additional datasheets and lab ordering documents."""
    buprenorphine_volume_ml: float
    """Stores the volume of buprenorphine diluted with saline administered during surgery, in ml."""
    buprenorphine_code: int
    """Stores the manufacturer code or internal reference code for buprenorphine. This code is used to identify the 
    buprenorphine batch in additional datasheets and lab ordering documents."""
    dexamethasone_volume_ml: float
    """Stores the volume of dexamethasone diluted with saline administered during surgery, in ml."""
    dexamethasone_code: int
    """Stores the manufacturer code or internal reference code for dexamethasone. This code is used to identify the 
    dexamethasone batch in additional datasheets and lab ordering documents."""


@dataclass
class SurgeryData(YamlConfig):
    """Stores the data about a single mouse surgical intervention.

    This class aggregates other dataclass instances that store specific data about the surgical procedure. Primarily, it
    is used to save the data as a .yaml file to every session's raw_data directory of each animal used in every lab
    project. This way, the surgery data is always stored alongside the behavior and brain activity data collected
    during the session.
    """

    subject: SubjectData
    """Stores the ID information about the subject (mouse)."""
    procedure: ProcedureData
    """Stores general data about the surgical intervention."""
    drugs: DrugData
    """Stores the data about the substances subcutaneously injected into the subject before, during and immediately 
    after the surgical intervention."""
    implants: list[ImplantData]
    """Stores the data for all cranial and transcranial implants introduced to the subject during the surgical 
    intervention."""
    injections: list[InjectionData]
    """Stores the data about all substances infused into the brain of the subject during the surgical intervention."""
