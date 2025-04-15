from pathlib import Path
from dataclasses import field, dataclass

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig

def replace_root_path(path: Path) -> None:
    """Replaces the path to the local root directory used to store all Sun lab projects with the provided path.

    When ProjectConfiguration class is instantiated for the first time on a new machine, it asks the user to provide
    the path to the local directory where to save all Sun lab projects. This path is then stored inside the default
    user data directory as a .yaml file to be reused for all future projects. To support replacing this path without
    searching for the user data directory, which is usually hidden, this function finds and updates the contents of the
    file that stores the local root path.

    Args:
        path: The path to the new local root directory.
    """
@dataclass()
class ProjectConfiguration(YamlConfig):
    """Stores the project-specific configuration parameters that do not change between different animals and runtime
    sessions.

    An instance of this class is generated and saved as a .yaml file in the \'configuration\' directory of each project
    when it is created. After that, the stored data is reused for every runtime (training or experiment session) carried
    out for each animal of the project.

    Notes:
        This class allows flexibly configuring sl_experiment and sl_forgery libraries for different projects in the
        Sun lab. This allows hiding most inner workings of all libraries from the end-users, while providing a robust,
        machine-independent way to interface with all data acquisition and processing libraries.

        Most lab projects only need to adjust the "surgery_sheet_id" and "water_log_sheet_id" fields of the class.
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
        """Loads the project configuration parameters from a project_configuration.yaml file and uses the loaded data
        to initialize the ProjectConfiguration instance.

        This method is called for each session runtime to reuse the configuration parameters generated at project
        creation. When it is called for the first time (during new project creation), the method generates the default
        configuration file and prompts the user to update the configuration before proceeding with the runtime.

        Notes:
            As part of its runtime, the method may prompt the user to provide the path to the local root directory.
            This directory stores all project subdirectories and acts as the top level of the local data hierarchy.
            The path to the directory will be saved inside user's default data directory, so that it can be reused for
            all future projects. Use sl-replace_root_path CLI to replace the path that is saved in this way.

            Since this class is used during both data acquisition and processing on different machines, this method
            supports multiple ways of initializing the class. Use the project_name on the VRPC (via the sl_experiment
            library). Use the configuration path on the BioHPC server (via the sl_forgery library).

        Args:
            project_name: The name of the project whose configuration file needs to be discovered and loaded. Note, this
                way of resolving the project is the default way on the VRPC. When processing data on the server, the
                pipeline preferentially uses the configuration_path.
            configuration_path: The path to the project_configuration.yaml file from which to load the data. This is
                an optional way of resolving the configuration data source that always takes precedence over the
                project_name when both are provided.

        Returns:
            An initialized ProjectConfiguration instance.
        """
    def _to_path(self, path: Path) -> None:
        """Saves the instance data to disk as a project_configuration.yaml file.

        This method is automatically called when the project is created. All future runtimes should use the load()
        method to load and reuse the configuration data saved to the .yaml file.

        Notes:
            This method also generates and dumps multiple other 'precursor' configuration files into the folder. This
            includes the example 'default' experiment configuration and the DeepLabCut and Suite2P configuration files
            used during data processing.

        Args:
            path: The path to the .yaml file to save the data to.
        """
    def _verify_data(self) -> None:
        """Verifies the data loaded from the project_configuration.yaml file to ensure its validity.

        Since this class is explicitly designed to be modified by the user, this verification step is carried out to
        ensure that the loaded data matches expectations. This reduces the potential for user errors to impact the
        runtime behavior of the library. This internal method is automatically called by the load() method.

        Notes:
            The method does not verify all fields loaded from the configuration file and instead focuses on fields that
            do not have valid default values. Since these fields are expected to be frequently modified by users, they
            are the ones that require additional validation.

        Raises:
            ValueError: If the loaded data does not match expected formats or values.
        """

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
    camera_data_path: str | Path
    mesoscope_data_path: str | Path
    behavior_data_path: str | Path
    zaber_positions_path: str | Path
    session_descriptor_path: str | Path
    hardware_configuration_path: str | Path
    surgery_metadata_path: str | Path
    project_configuration_path: str | Path
    session_data_path: str | Path
    experiment_configuration_path: str | Path
    mesoscope_positions_path: str | Path
    window_screenshot_path: str | Path
    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """
    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
    def make_dirs(self) -> None:
        """Ensures that all major subdirectories and the root raw_data directory exist.

        This method is used by the VRPC to generate the raw_data directory when it creates a new session.
        """
    def switch_root(self, new_root: Path) -> None:
        """Changes the root of the managed raw_data directory to the provided root path.

        This service method is used by the SessionData class to convert all paths in this class to be relative to the
        new root. This is used to adjust the SessionData instance to work for the VRPC (one root) or the BioHPC server
        (another root). Since this is the only subclass used by both the VRPC and the BioHPC server, this method is
        only implemented for this class.

        Args:
            new_root: The new root directory to use for all paths inside the instance. This has to be the path to the
                root session directory: pc_root/project/animal/session.
        """

@dataclass()
class ProcessedData:
    """Stores the paths to the directories and files that make up the 'processed_data' session directory.

    The processed_data directory stores the processed session data, which is generated by running various processing
    pipelines on the BioHPC server. These pipelines use raw data to generate processed data, and the processed data is
    usually only stored on the BioHPC server. Processed data represents an intermediate step between raw data and the
    dataset used in the data analysis.
    """

    processed_data_path: str | Path
    camera_data_path: str | Path
    mesoscope_data_path: str | Path
    behavior_data_path: str | Path
    deeplabcut_root_path: str | Path
    suite2p_configuration_path: str | Path
    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """
    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
    def make_dirs(self) -> None:
        """Ensures that all major subdirectories of the processed_data directory exist.

        This method is used by the BioHPC server to generate the processed_data directory as part of the sl-forgery
        library runtime.
        """

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
    mesoscope_positions_path: str | Path
    motion_estimator_path: str | Path
    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """
    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
    def make_dirs(self) -> None:
        """Ensures that the VRPC and the ScanImagePC persistent_data directories exist."""

@dataclass()
class MesoscopeData:
    """Stores the paths to the directories used by the ScanImagePC to save mesoscope-generated data during session
    runtime.

    The ScanImagePC is largely isolated from the VRPC during runtime. For the VRPC to pull the data acquired by the
    ScanImagePC, it has to use the predefined directory structure to save the data. This class stores the predefined
    path to various directories where ScanImagePC is expected to save the data and store it after acquisition.sers.
    """

    root_data_path: str | Path
    mesoscope_data_path: str | Path
    session_specific_mesoscope_data_path: str | Path
    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """
    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
    def make_dirs(self) -> None:
        """Ensures that the ScanImagePC data acquisition directories exist."""

@dataclass()
class Destinations:
    """Stores the paths to the VRPC filesystem-mounted Synology NAS and BioHPC server directories.

    These directories are used during data preprocessing to transfer the preprocessed raw_data directory from the
    VRPC to the long-term storage destinations.
    """

    nas_raw_data_path: str | Path
    server_raw_data_path: str | Path
    def __post_init__(self) -> None:
        """This method is automatically called after class instantiation and ensures that all path fields of the class
        are converted to Path objects.
        """
    def make_string(self) -> None:
        """Converts all Path objects stored inside the class to strings.

        This transformation is required to support dumping class data into a .YAML file so that the data can be stored
        on disk.
        """
    def make_dirs(self) -> None:
        """Ensures that all destination directories exist."""

@dataclass
class SessionData(YamlConfig):
    """Provides methods for managing the data of a single experiment or training session across all destinations.

    The primary purpose of this class is to maintain the session data structure across all supported destinations. It
    generates the paths used by all other classes from this library and classes from sl-experiment and sl-forgery
    libraries.

    If necessary, the class can be used to either generate a new session or to load an already existing session's data.
    When the class is used to create a new session, it automatically resolves the new session's name using the current
    UTC timestamp, down to microseconds. This ensures that each session name is unique and preserves the overall
    session order.

    Notes:
        If this class is instantiated on the VRPC, it is expected that the BioHPC server, Synology NAS, and ScanImagePC
        data directories are mounted on the local host-machine via the SMB or equivalent protocol. All manipulations
        with these destinations are carried out with the assumption that the OS has full access to these directories
        and filesystems.

        If this class is instantiated on the BioHPC server, some methods from this class will not work as expected. It
        is essential that this class is not used outside the default sl-experiment and sl-forgery library runtimes to
        ensure it is used safely.

        This class is specifically designed for working with the data from a single session, performed by a single
        animal under the specific experiment. The class is used to manage both raw and processed data. It follows the
        data through acquisition, preprocessing and processing stages of the Sun lab data workflow.
    """

    animal_id: str
    session_type: str
    experiment_name: str | None
    raw_data: RawData | None
    processed_data: ProcessedData | None
    persistent_data: PersistentData | None
    mesoscope_data: MesoscopeData | None
    destinations: Destinations | None
    @classmethod
    def create_session(
        cls,
        animal_id: str,
        session_type: str,
        project_configuration: ProjectConfiguration,
        experiment_name: str | None = None,
    ) -> SessionData:
        """Creates a new SessionData object and uses it to generate the session's data structure.

        This method is used to initialize new session runtimes. It always assumes it is called on the VRPC and, as part
        of its runtime, resolves and generates the necessary local and ScanImagePC directories to support acquiring and
        preprocessing session's data.

        Notes:
            To load an already existing session data structure, use the load_session() method instead.

            This method automatically dumps the data of the created SessionData instance into the session_data.yaml file
            inside the root raw_data directory of the created hierarchy. It also finds and dumps other configuration
            files, such as project_configuration.yaml, suite2p_configuration.yaml, and experiment_configuration.yaml.
            This way, if the session's runtime is interrupted unexpectedly, it can still be processed.

        Args:
            animal_id: The ID code of the animal for which the data is acquired.
            session_type: The type of the session. Primarily, this determines how to read the session_descriptor.yaml
                file. Valid options are 'Lick training', 'Run training', or 'Experiment'.
            experiment_name: The name of the experiment to be executed as part of this session. This option is only used
                for 'Experiment' session types. It is used to find the target experiment configuration .YAML file and
                copy it into the session's raw_data directory.
            project_configuration: The initialized ProjectConfiguration instance that stores the data for the session's
                project. This is used to determine the root directory paths for all PCs used in the data workflow.

        Returns:
            An initialized SessionData instance for the newly created session.
        """
    @classmethod
    def load_session(cls, session_path: Path, on_server: bool) -> SessionData:
        """Loads the SessionData instance from the session_data.yaml file of the target session.

        This method is used to load the data for an already existing session. This is used to call preprocessing
        or processing runtime(s) for the target session. Depending on the call location, the method automatically
        resolves all necessary paths and creates the necessary directories.

        Notes:
            To create a new session, use the create_session() method instead.

        Args:
            session_path: The path to the root directory of an existing session, e.g.: vrpc_root/project/animal/session.
            on_server: Determines whether the method is used to initialize an existing session on the VRPC or the
                BioHPC server.

        Returns:
            An initialized SessionData instance for the session whose data is stored at the provided path.

        Raises:
            FileNotFoundError: If the 'session_data.yaml' file is not found after resolving the provided path.
        """
    def _to_path(self) -> None:
        """Saves the instance data to the 'raw_data' directory of the managed session as a 'session_data.yaml' file.

        This is used to save the data stored in the instance to disk, so that it can be reused during preprocessing or
        data processing. The method is intended to only be used by the SessionData instance itself during its
        create_session() method runtime.
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
