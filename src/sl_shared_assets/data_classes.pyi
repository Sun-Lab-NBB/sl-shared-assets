from pathlib import Path
from dataclasses import field, dataclass

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig

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
    processing_tracker_path: Path = ...
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
        """Saves the instance data to the 'raw_data' directory of the managed session as a 'session_data.yaml' file.

        This is used to save the data stored in the instance to disk, so that it can be reused during preprocessing or
        data processing. The method is intended to only be used by the SessionData instance itself during its
        create() method runtime.
        """

@dataclass()
class ExperimentState:
    """Encapsulates the information used to set and maintain the desired experiment and Mesoscope-VR system state.

    Primarily, experiment runtime logic (task logic) is resolved by the Unity game engine. However, the Mesoscope-VR
    system configuration may also need to change throughout the experiment to optimize the runtime by disabling or
    reconfiguring specific hardware modules. For example, some experiment stages may require the running wheel to be
    locked to prevent the animal from running, and other may require the VR screens to be turned off.
    """

    experiment_state_code: int
    vr_state_code: int
    state_duration_s: float

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

    cue_map: dict[int, float] = field(default_factory=Incomplete)
    experiment_states: dict[str, ExperimentState] = field(default_factory=Incomplete)

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

    cue_map: dict[int, float] | None = ...
    cm_per_pulse: float | None = ...
    maximum_break_strength: float | None = ...
    minimum_break_strength: float | None = ...
    lick_threshold: int | None = ...
    valve_scale_coefficient: float | None = ...
    valve_nonlinearity_exponent: float | None = ...
    torque_per_adc_unit: float | None = ...
    screens_initially_on: bool | None = ...
    recorded_mesoscope_ttl: bool | None = ...

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
    mouse_weight_g: float
    dispensed_water_volume_ml: float
    minimum_reward_delay: int
    maximum_reward_delay_s: int
    maximum_water_volume_ml: float
    maximum_training_time_m: int
    experimenter_notes: str = ...
    experimenter_given_water_volume_ml: float = ...

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
    mouse_weight_g: float
    dispensed_water_volume_ml: float
    final_run_speed_threshold_cm_s: float
    final_run_duration_threshold_s: float
    initial_run_speed_threshold_cm_s: float
    initial_run_duration_threshold_s: float
    increase_threshold_ml: float
    run_speed_increase_step_cm_s: float
    run_duration_increase_step_s: float
    maximum_water_volume_ml: float
    maximum_training_time_m: int
    experimenter_notes: str = ...
    experimenter_given_water_volume_ml: float = ...

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
    mouse_weight_g: float
    dispensed_water_volume_ml: float
    experimenter_notes: str = ...
    experimenter_given_water_volume_ml: float = ...

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

    headbar_z: int = ...
    headbar_pitch: int = ...
    headbar_roll: int = ...
    lickport_z: int = ...
    lickport_x: int = ...
    lickport_y: int = ...

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

    mesoscope_x_position: float = ...
    mesoscope_y_position: float = ...
    mesoscope_roll_position: float = ...
    mesoscope_z_position: float = ...
    mesoscope_fast_z_position: float = ...
    mesoscope_tip_position: float = ...
    mesoscope_tilt_position: float = ...

@dataclass()
class SubjectData:
    """Stores the ID information of the surgical intervention's subject (animal)."""

    id: int
    ear_punch: str
    sex: str
    genotype: str
    date_of_birth_us: int
    weight_g: float
    cage: int
    location_housed: str
    status: str

@dataclass()
class ProcedureData:
    """Stores the general information about the surgical intervention."""

    surgery_start_us: int
    surgery_end_us: int
    surgeon: str
    protocol: str
    surgery_notes: str
    post_op_notes: str
    surgery_quality: int = ...

@dataclass
class ImplantData:
    """Stores the information about a single implantation performed during the surgical intervention.

    Multiple ImplantData instances are used at the same time if the surgery involved multiple implants.
    """

    implant: str
    implant_target: str
    implant_code: int
    implant_ap_coordinate_mm: float
    implant_ml_coordinate_mm: float
    implant_dv_coordinate_mm: float

@dataclass
class InjectionData:
    """Stores the information about a single injection performed during surgical intervention.

    Multiple InjectionData instances are used at the same time if the surgery involved multiple injections.
    """

    injection: str
    injection_target: str
    injection_volume_nl: float
    injection_code: int
    injection_ap_coordinate_mm: float
    injection_ml_coordinate_mm: float
    injection_dv_coordinate_mm: float

@dataclass
class DrugData:
    """Stores the information about all drugs administered to the subject before, during, and immediately after the
    surgical intervention.
    """

    lactated_ringers_solution_volume_ml: float
    lactated_ringers_solution_code: int
    ketoprofen_volume_ml: float
    ketoprofen_code: int
    buprenorphine_volume_ml: float
    buprenorphine_code: int
    dexamethasone_volume_ml: float
    dexamethasone_code: int

@dataclass
class SurgeryData(YamlConfig):
    """Stores the data about a single mouse surgical intervention.

    This class aggregates other dataclass instances that store specific data about the surgical procedure. Primarily, it
    is used to save the data as a .yaml file to every session's raw_data directory of each animal used in every lab
    project. This way, the surgery data is always stored alongside the behavior and brain activity data collected
    during the session.
    """

    subject: SubjectData
    procedure: ProcedureData
    drugs: DrugData
    implants: list[ImplantData]
    injections: list[InjectionData]

@dataclass()
class ProcessingTracker(YamlConfig):
    """Tracks the data processing status for a single session.

    This class is used during BioHPC-server data processing runtimes to track which processing steps are enabled and
    have been successfully applied to a given session. This is used to optimize data processing and avoid unnecessary
    processing step repetitions where possible.

    Notes:
        This class uses a similar mechanism for determining whether a particular option is enabled as the
        HardwareConfiguration class. Specifically, if any field of the class is set to None (null), the processing
        associated with that field is disabled. Otherwise, if the field is False, that session has not been processed
        and, if True, the session has been processed.
    """

    checksum: bool | None = ...
    log_extractions: bool | None = ...
    suite2p: bool | None = ...
    deeplabcut: bool | None = ...
