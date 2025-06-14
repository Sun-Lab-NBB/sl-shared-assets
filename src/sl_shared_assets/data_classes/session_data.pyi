from pathlib import Path
from dataclasses import field, dataclass

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig

from .configuration_data import get_system_configuration_data as get_system_configuration_data

_valid_session_types: Incomplete

@dataclass()
class VersionData(YamlConfig):
    """Stores information about the versions of important Sun lab libraries used to acquire the session's data."""

    python_version: str = ...
    sl_experiment_version: str = ...

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
    """

    project_name: str = ...
    surgery_sheet_id: str = ...
    water_log_sheet_id: str = ...
    @classmethod
    def load(cls, configuration_path: Path) -> ProjectConfiguration:
        """Loads the project configuration parameters from the specified project_configuration.yaml file.

        This method is called during each interaction with any runtime session's data, including the creation of a new
        session.

        Args:
            configuration_path: The path to the project_configuration.yaml file from which to load the data.

        Returns:
            The initialized ProjectConfiguration instance that stores the configuration data for the target project.

        Raise:
            FileNotFoundError: If the specified configuration file does not exist or is not a valid YAML file.
        """
    def save(self, path: Path) -> None:
        """Saves class instance data to disk as a project_configuration.yaml file.

        This method is automatically called from the 'sl_experiment' library when a new project is created. After this
        method's runtime, all future project initialization calls will use the load() method to reuse configuration data
        saved to the .yaml file created by this method.

        Args:
            path: The path to the .yaml file to save the data to.
        """
    def _verify_data(self) -> None:
        """Verifies the user-modified data loaded from the project_configuration.yaml file.

        Since this class is explicitly designed to be modified by the user, this verification step is carried out to
        ensure that the loaded data matches expectations. This reduces the potential for user errors to impact the
        runtime behavior of the libraries using this class. This internal method is automatically called by the load()
        method.

        Raises:
            ValueError: If the loaded data does not match expected formats or values.
        """

@dataclass()
class RawData:
    """Stores the paths to the directories and files that make up the 'raw_data' session-specific directory.

    The raw_data directory stores the data acquired during the session runtime before and after preprocessing. Since
    preprocessing does not alter the data, any data in that folder is considered 'raw'.

    Notes:
        Sun lab data management strategy primarily relies on keeping multiple redundant copies of the raw_data for
        each acquired session. Typically, one copy is stored on the lab's processing server and the other is stored on
        the NAS.
    """

    raw_data_path: Path = ...
    camera_data_path: Path = ...
    mesoscope_data_path: Path = ...
    behavior_data_path: Path = ...
    zaber_positions_path: Path = ...
    session_descriptor_path: Path = ...
    hardware_state_path: Path = ...
    surgery_metadata_path: Path = ...
    project_configuration_path: Path = ...
    session_data_path: Path = ...
    experiment_configuration_path: Path = ...
    mesoscope_positions_path: Path = ...
    window_screenshot_path: Path = ...
    system_configuration_path: Path = ...
    checksum_path: Path = ...
    telomere_path: Path = ...
    ubiquitin_path: Path = ...
    integrity_verification_tracker_path: Path = ...
    version_data_path: Path = ...
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
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories."""

@dataclass()
class ProcessedData:
    """Stores the paths to the directories and files that make up the 'processed_data' session-specific directory.

    The processed_data directory stores the data generated by various processing pipelines from the raw data (contents
    of the raw_data directory). Processed data represents an intermediate step between raw data and the dataset used in
    the data analysis, but is not itself designed to be analyzed.
    """

    processed_data_path: Path = ...
    camera_data_path: Path = ...
    mesoscope_data_path: Path = ...
    behavior_data_path: Path = ...
    job_logs_path: Path = ...
    suite2p_processing_tracker_path: Path = ...
    dataset_formation_tracker_path: Path = ...
    behavior_processing_tracker_path: Path = ...
    video_processing_tracker_path: Path = ...
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
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories."""

@dataclass
class SessionData(YamlConfig):
    """Stores and manages the data layout of a single training or experiment session acquired in the Sun lab.

    The primary purpose of this class is to maintain the session data structure across all supported destinations and
    during all processing stages. It generates the paths used by all other classes from all Sun lab libraries that
    interact with the session's data from the point of its creation and until the data is integrated into an
    analysis dataset.

    When necessary, the class can be used to either generate a new session or load the layout of an already existing
    session. When the class is used to create a new session, it generates the new session's name using the current
    UTC timestamp, accurate to microseconds. This ensures that each session name is unique and preserves the overall
    session order.

    Notes:
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
    acquisition_system: str
    experiment_name: str | None
    raw_data: RawData = field(default_factory=Incomplete)
    processed_data: ProcessedData = field(default_factory=Incomplete)
    def __post_init__(self) -> None:
        """Ensures raw_data and processed_data are always instances of RawData and ProcessedData."""
    @classmethod
    def create(
        cls,
        project_name: str,
        animal_id: str,
        session_type: str,
        experiment_name: str | None = None,
        session_name: str | None = None,
    ) -> SessionData:
        """Creates a new SessionData object and generates the new session's data structure on the local PC.

        This method is intended to be called exclusively by the sl-experiment library to create new training or
        experiment sessions and generate the session data directory tree.

        Notes:
            To load an already existing session data structure, use the load() method instead.

            This method automatically dumps the data of the created SessionData instance into the session_data.yaml file
            inside the root raw_data directory of the created hierarchy. It also finds and dumps other configuration
            files, such as project_configuration.yaml, experiment_configuration.yaml, and system_configuration.yaml into
            the same raw_data directory. This ensures that if the session's runtime is interrupted unexpectedly, the
            acquired data can still be processed.

        Args:
            project_name: The name of the project for which the data is acquired.
            animal_id: The ID code of the animal for which the data is acquired.
            session_type: The type of the session. Primarily, this determines how to read the session_descriptor.yaml
                file. Valid options are 'Lick training', 'Run training', 'Window checking', or 'Experiment'.
            experiment_name: The name of the experiment executed during managed session. This optional argument is only
                used for 'Experiment' session types. It is used to find the experiment configuration .YAML file.
            session_name: An optional session_name override. Generally, this argument should not be provided for most
                sessions. When provided, the method uses this name instead of generating a new timestamp-based name.
                This is only used during the 'ascension' runtime to convert old data structures to the modern
                lab standards.

        Returns:
            An initialized SessionData instance that stores the layout of the newly created session's data.
        """
    @classmethod
    def load(
        cls, session_path: Path, processed_data_root: Path | None = None, make_processed_data_directory: bool = False
    ) -> SessionData:
        """Loads the SessionData instance from the target session's session_data.yaml file.

        This method is used to load the data layout information of an already existing session. Primarily, this is used
        when preprocessing or processing session data. Due to how SessionData is stored and used in the lab, this
        method always loads the data layout from the session_data.yaml file stored inside the raw_data session
        subfolder. Currently, all interactions with Sun lab data require access to the 'raw_data' folder.

        Notes:
            To create a new session, use the create() method instead.

        Args:
            session_path: The path to the root directory of an existing session, e.g.: root/project/animal/session.
            processed_data_root: If processed data is kept on a drive different from the one that stores raw data,
                provide the path to the root project directory (directory that stores all Sun lab projects) on that
                drive. The method will automatically resolve the project/animal/session/processed_data hierarchy using
                this root path. If raw and processed data are kept on the same drive, keep this set to None.
            make_processed_data_directory: Determines whether this method should create processed_data directory if it
                does not exist.

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
class ProcessingTracker(YamlConfig):
    """Wraps the .yaml file that tracks the state of a data processing runtime and provides tools for communicating the
    state between multiple processes in a thread-safe manner.

    Primarily, this tracker class is used by all remote data processing pipelines in the lab to prevent race conditions
    and make it impossible to run multiple processing runtimes at the same time.
    """

    file_path: Path
    _is_complete: bool = ...
    _encountered_error: bool = ...
    _is_running: bool = ...
    _lock_path: str = field(init=False)
    def __post_init__(self) -> None: ...
    def _load_state(self) -> None:
        """Reads the current processing state from the wrapped .YAML file."""
    def _save_state(self) -> None:
        """Saves the current processing state stored inside instance attributes to the specified .YAML file."""
    def start(self) -> None:
        """Configures the tracker file to indicate that the tracked processing runtime is currently running.

        All further attempts to start the same processing runtime for the same session's data will automatically abort
        with an error.

        Raises:
            TimeoutError: If the file lock for the target .YAML file cannot be acquired within the timeout period.
        """
    def error(self) -> None:
        """Configures the tracker file to indicate that the tracked processing runtime encountered an error and failed
        to complete.

        This method will only work for an active runtime. When called for an active runtime, it expects the runtime to
        be aborted with an error after the method returns. It configures the target tracker to allow other processes
        to restart the runtime at any point after this method returns, so it is UNSAFE to do any further processing
        from the process that calls this method.

        Raises:
            TimeoutError: If the file lock for the target .YAML file cannot be acquired within the timeout period.
        """
    def stop(self) -> None:
        """Mark processing as started.

        Raises:
            TimeoutError: If the file lock for the target .YAML file cannot be acquired within the timeout period.
        """
    @property
    def is_complete(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing runtime has been completed
        successfully and False otherwise."""
    @property
    def encountered_error(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing runtime aborted due to
        encountering an error and False otherwise."""
    @property
    def is_running(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing runtime is currently
        running and False otherwise."""
