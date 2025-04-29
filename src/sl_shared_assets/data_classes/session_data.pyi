from pathlib import Path
from dataclasses import field, dataclass

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig

from .configuration_data import ExperimentConfiguration as ExperimentConfiguration

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
@dataclass()
class ProjectConfiguration(YamlConfig):
    """Stores the project-specific configuration parameters that do not change between different animals and runtime
    sessions.

    An instance of this class is generated and saved as a .yaml file in the \'configuration\' directory of each project
    when it is created. After that, the stored data is reused for every runtime (training or experiment session) carried
    out for each animal of the project. Additionally, a copy of the most actual configuration file is saved inside each
    runtime session\'s \'raw_data\' folder, providing seamless integration between the managed data and various Sun lab
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

    project_name: str = ...
    surgery_sheet_id: str = ...
    water_log_sheet_id: str = ...
    google_credentials_path: str | Path = ...
    server_credentials_path: str | Path = ...
    local_root_directory: str | Path = ...
    local_server_directory: str | Path = ...
    local_nas_directory: str | Path = ...
    local_mesoscope_directory: str | Path = ...
    local_server_working_directory: str | Path = ...
    remote_storage_directory: str | Path = ...
    remote_working_directory: str | Path = ...
    face_camera_index: int = ...
    left_camera_index: int = ...
    right_camera_index: int = ...
    harvesters_cti_path: str | Path = ...
    actor_port: str = ...
    sensor_port: str = ...
    encoder_port: str = ...
    headbar_port: str = ...
    lickport_port: str = ...
    unity_ip: str = ...
    unity_port: int = ...
    valve_calibration_data: dict[int | float, int | float] | tuple[tuple[int | float, int | float], ...] = ...
    @classmethod
    def load(cls, project_name: str, configuration_path: None | Path = None) -> ProjectConfiguration:
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

@dataclass()
class RawData:
    """Stores the paths to the directories and files that make up the 'raw_data' session-specific directory.

    The raw_data directory stores the data acquired during the session runtime before and after preprocessing. Since
    preprocessing does not alter the data, any data in that folder is considered 'raw'. The raw_data folder is initially
    created on the VRPC and, after preprocessing, is copied to the BioHPC server and the Synology NAS for long-term
    storage and further processing.
    """

    raw_data_path: Path = ...
    camera_data_path: Path = ...
    mesoscope_data_path: Path = ...
    behavior_data_path: Path = ...
    zaber_positions_path: Path = ...
    session_descriptor_path: Path = ...
    hardware_configuration_path: Path = ...
    surgery_metadata_path: Path = ...
    project_configuration_path: Path = ...
    session_data_path: Path = ...
    experiment_configuration_path: Path = ...
    mesoscope_positions_path: Path = ...
    window_screenshot_path: Path = ...
    telomere_path: Path = ...
    checksum_path: Path = ...
    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """
    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

@dataclass()
class DeepLabCutData:
    """Stores the paths to the directories and files that make up the 'deeplabcut' project-specific directory.

    DeepLabCut (DLC) is used to track animal body parts and poses in video data acquired during experiment and training
    sessions. Since DLC is designed to work with projects, rather than single animals or sessions, each Sun lab
    project data hierarchy contains a dedicated 'deeplabcut' directory under the root project directory. The contents of
    that directory are largely managed by the DLC itself. Therefore, each session of a given project refers to and
    uses the same 'deeplabcut' directory.
    """

    deeplabcut_path: Path = ...
    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """
    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

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

    configuration_path: Path = ...
    experiment_configuration_path: Path = ...
    project_configuration_path: Path = ...
    suite2p_configuration_path: Path = ...
    multiday_configuration_path: Path = ...
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
    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

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

    processed_data_path: Path = ...
    camera_data_path: Path = ...
    mesoscope_data_path: Path = ...
    behavior_data_path: Path = ...
    job_logs_path: Path = ...
    project_configuration_path: Path = ...
    session_data_path: Path = ...
    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """
    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

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

    persistent_data_path: Path = ...
    zaber_positions_path: Path = ...
    mesoscope_positions_path: Path = ...
    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """
    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

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

    persistent_data_path: Path = ...
    motion_estimator_path: Path = ...
    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the local hierarchy. Depending on the managed
                hierarchy, this has to point to a directory under the main /session, /animal, or /project directory of
                the managed session.
        """
    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

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

    meso_data_path: Path = ...
    mesoscope_data_path: Path = ...
    session_specific_path: Path = ...
    ubiquitin_path: Path = ...
    def resolve_paths(self, root_mesoscope_path: Path, session_name: str) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the class is instantiated to regenerate the managed path hierarchy on any
        machine that instantiates the class.

        Args:
            root_mesoscope_path: The path to the top-level directory of the ScanImagePC data hierarchy mounted to the
                VRPC via the SMB or equivalent protocol.
            session_name: The name of the session for which this subclass is initialized.
        """
    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

@dataclass()
class VRPCDestinations:
    """Stores the paths to the VRPC filesystem-mounted directories of the Synology NAS and BioHPC server.

    The paths from this section are primarily used to transfer preprocessed data to the long-term storage destinations.
    Additionally, they allow VRPC to interface with the configuration directory of the BioHPC server to start data
    processing jobs and to read the data from the processed_data directory to remove redundant data from the VRPC
    filesystem.

    Overall, this section is intended solely for the VRPC and should not be used on other PCs.
    """

    nas_raw_data_path: Path = ...
    server_raw_data_path: Path = ...
    server_processed_data_path: Path = ...
    server_configuration_path: Path = ...
    telomere_path: Path = ...
    suite2p_configuration_path: Path = ...
    processing_tracker_path: Path = ...
    multiday_configuration_path: Path = ...
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
    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist."""

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
    animal_id: str
    session_name: str
    session_type: str
    experiment_name: str | None
    raw_data: RawData = field(default_factory=Incomplete)
    processed_data: ProcessedData = field(default_factory=Incomplete)
    deeplabcut_data: DeepLabCutData = field(default_factory=Incomplete)
    configuration_data: ConfigurationData = field(default_factory=Incomplete)
    vrpc_persistent_data: VRPCPersistentData = field(default_factory=Incomplete)
    scanimagepc_persistent_data: ScanImagePCPersistentData = field(default_factory=Incomplete)
    mesoscope_data: MesoscopeData = field(default_factory=Incomplete)
    destinations: VRPCDestinations = field(default_factory=Incomplete)
    @classmethod
    def create(
        cls,
        animal_id: str,
        session_type: str,
        project_configuration: ProjectConfiguration,
        experiment_name: str | None = None,
        session_name: str | None = None,
    ) -> SessionData:
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
    @classmethod
    def load(cls, session_path: Path, on_server: bool) -> SessionData:
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
    def _save(self) -> None:
        """Saves the instance data to the 'raw_data' directory and the 'processed_data' directory of the managed session
         as a 'session_data.yaml' file.

        This is used to save the data stored in the instance to disk, so that it can be reused during preprocessing or
        data processing. The method is intended to only be used by the SessionData instance itself during its
        create() method runtime.
        """
