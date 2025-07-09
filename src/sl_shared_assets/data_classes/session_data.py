"""This module contains classes jointly responsible for maintaining the Sun lab project data hierarchy across all
machines used to acquire, process, and store the data. Every valid experiment or training session conducted in the
lab generates a specific directory structure. This structure is defined via the ProjectConfiguration and SessionData
classes, which are also stored as .yaml files inside each session's raw_data and processed_data directories. Jointly,
these classes contain all necessary information to restore the data hierarchy on any machine. All other Sun lab
libraries use these classes to work with all lab-generated data."""

import copy
import shutil as sh
from pathlib import Path
from dataclasses import field, dataclass

from filelock import Timeout, FileLock
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig
from ataraxis_time.time_helpers import get_timestamp

from .configuration_data import get_system_configuration_data

# Stores all supported input for SessionData class 'session_type' fields.
_valid_session_types = {"lick training", "run training", "mesoscope experiment", "window checking"}


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

    raw_data_path: Path = Path()
    """Stores the path to the root raw_data directory of the session. This directory stores all raw data during 
    acquisition and preprocessing. Note, preprocessing does not alter raw data, so at any point in time all data inside
    the folder is considered 'raw'."""
    camera_data_path: Path = Path()
    """Stores the path to the directory that contains all camera data acquired during the session. Primarily, this 
    includes .mp4 video files from each recorded camera."""
    mesoscope_data_path: Path = Path()
    """Stores the path to the directory that contains all Mesoscope data acquired during the session. Primarily, this 
    includes the mesoscope-acquired .tiff files (brain activity data) and the motion estimation data. This directory is
    created for all sessions, but is only used (filled) by the sessions that use the Mesoscope-VR system to acquire 
    brain activity data."""
    behavior_data_path: Path = Path()
    """Stores the path to the directory that contains all non-video behavior data acquired during the session. 
    Primarily, this includes the .npz log files that store serialized data acquired by all hardware components of the 
    data acquisition system other than cameras and brain activity data acquisition devices (such as the Mesoscope).
    The reason why the directory is called 'behavior' is primarily because all .npz files are parsed to infer the 
    behavior of the animal, in contrast to brain (cell) activity data."""
    zaber_positions_path: Path = Path()
    """Stores the path to the zaber_positions.yaml file. This file contains the snapshot of all Zaber motor positions 
    at the end of the session. Zaber motors are used to position the LickPort and the HeadBar manipulators, which is 
    essential for supporting proper brain imaging and animal's running behavior during the session. This file is only 
    created for sessions that use the Mesoscope-VR system."""
    session_descriptor_path: Path = Path()
    """Stores the path to the session_descriptor.yaml file. This file is partially filled by the system during runtime 
    and partially by the experimenter after the runtime. It contains session-specific information, such as the specific
    task parameters and the notes made by the experimenter during runtime."""
    hardware_state_path: Path = Path()
    """Stores the path to the hardware_state.yaml file. This file contains the partial snapshot of the calibration 
    parameters used by the data acquisition and runtime management system modules during the session. Primarily, 
    this is used during data processing to read the .npz data log files generated during runtime."""
    surgery_metadata_path: Path = Path()
    """Stores the path to the surgery_metadata.yaml file. This file contains the most actual information about the 
    surgical intervention(s) performed on the animal prior to the session."""
    project_configuration_path: Path = Path()
    """Stores the path to the project_configuration.yaml file. This file contains the snapshot of the configuration 
    parameters for the session's project."""
    session_data_path: Path = Path()
    """Stores the path to the session_data.yaml file. This path is used by the SessionData instance to save itself to 
    disk as a .yaml file. The file contains the paths to all raw and processed data directories used during data 
    acquisition or processing runtime."""
    experiment_configuration_path: Path = Path()
    """Stores the path to the experiment_configuration.yaml file. This file contains the snapshot of the 
    experiment runtime configuration used by the session. This file is only created for experiment sessions."""
    mesoscope_positions_path: Path = Path()
    """Stores the path to the mesoscope_positions.yaml file. This file contains the snapshot of the positions used
    by the Mesoscope at the end of the session. This includes both the physical position of the mesoscope objective and
    the 'virtual' tip, tilt, and fastZ positions set via ScanImage software. This file is only created for sessions that
    use the Mesoscope-VR system to acquire brain activity data."""
    window_screenshot_path: Path = Path()
    """Stores the path to the .png screenshot of the ScanImagePC screen. The screenshot should contain the image of the 
    cranial window and the red-dot alignment windows. This is used to generate a visual snapshot of the cranial window
    alignment and appearance for each experiment session. This file is only created for sessions that use the 
    Mesoscope-VR system to acquire brain activity data."""
    system_configuration_path: Path = Path()
    """Stores the path to the system_configuration.yaml file. This file contains the exact snapshot of the data 
    acquisition and runtime management system configuration parameters used to acquire session data."""
    checksum_path: Path = Path()
    """Stores the path to the ax_checksum.txt file. This file is generated as part of packaging the data for 
    transmission and stores the xxHash-128 checksum of the data. It is used to verify that the transmission did not 
    damage or otherwise alter the data."""
    telomere_path: Path = Path()
    """Stores the path to the telomere.bin file. This file is statically generated at the end of the session's data 
    acquisition based on experimenter feedback to mark sessions that ran in-full with no issues. Sessions without a 
    telomere.bin file are considered 'incomplete' and are excluded from all automated processing, as they may contain 
    corrupted, incomplete, or otherwise unusable data."""
    ubiquitin_path: Path = Path()
    """Stores the path to the ubiquitin.bin file. This file is primarily used by the sl-experiment libraries to mark 
    local session data directories for deletion (purging). Typically, it is created once the data is safely moved to 
    the long-term storage destinations (NAS and Server) and the integrity of the moved data is verified on at least one 
    destination. During 'purge' sl-experiment runtimes, the library discovers and removes all session data marked with 
    'ubiquitin.bin' files from the machine that runs the code."""
    integrity_verification_tracker_path: Path = Path()
    """Stores the path to the integrity_verification.yaml tracker file. This file stores the current state of the data 
    integrity verification pipeline. It prevents more than one instance of the pipeline from working with the data 
    at a given time and communicates the outcome (success or failure) of the most recent pipeline runtime."""
    version_data_path: Path = Path()
    """Stores the path to the version_data.yaml file. This file contains the snapshot of Python and sl-experiment 
    library versions that were used when the data was acquired."""

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
        self.hardware_state_path = self.raw_data_path.joinpath("hardware_state.yaml")
        self.surgery_metadata_path = self.raw_data_path.joinpath("surgery_metadata.yaml")
        self.project_configuration_path = self.raw_data_path.joinpath("project_configuration.yaml")
        self.session_data_path = self.raw_data_path.joinpath("session_data.yaml")
        self.experiment_configuration_path = self.raw_data_path.joinpath("experiment_configuration.yaml")
        self.mesoscope_positions_path = self.raw_data_path.joinpath("mesoscope_positions.yaml")
        self.window_screenshot_path = self.raw_data_path.joinpath("window_screenshot.png")
        self.checksum_path = self.raw_data_path.joinpath("ax_checksum.txt")
        self.system_configuration_path = self.raw_data_path.joinpath("system_configuration.yaml")
        self.telomere_path = self.raw_data_path.joinpath("telomere.bin")
        self.ubiquitin_path = self.raw_data_path.joinpath("ubiquitin.bin")
        self.integrity_verification_tracker_path = self.raw_data_path.joinpath("integrity_verification_tracker.yaml")
        self.version_data_path = self.raw_data_path.joinpath("version_data.yaml")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories."""
        ensure_directory_exists(self.raw_data_path)
        ensure_directory_exists(self.camera_data_path)
        ensure_directory_exists(self.mesoscope_data_path)
        ensure_directory_exists(self.behavior_data_path)


@dataclass()
class ProcessedData:
    """Stores the paths to the directories and files that make up the 'processed_data' session-specific directory.

    The processed_data directory stores the data generated by various processing pipelines from the raw data (contents
    of the raw_data directory). Processed data represents an intermediate step between raw data and the dataset used in
    the data analysis, but is not itself designed to be analyzed.
    """

    processed_data_path: Path = Path()
    """Stores the path to the root processed_data directory of the session. This directory stores the processed data 
    as it is generated by various data processing pipelines."""
    camera_data_path: Path = Path()
    """Stores the path to the directory that contains video tracking data generated by our DeepLabCut-based video 
    processing pipelines."""
    mesoscope_data_path: Path = Path()
    """Stores path to the directory that contains processed brain activity (cell) data generated by our suite2p-based 
    photometry processing pipelines (single-day and multi-day). This directory is only used by sessions acquired with 
    the Mesoscope-VR system. For all other sessions, it will be created, but kept empty."""
    behavior_data_path: Path = Path()
    """Stores the path to the directory that contains the non-video and non-brain-activity data extracted from 
    .npz log files by our in-house log parsing pipeline."""
    suite2p_processing_tracker_path: Path = Path()
    """Stores the path to the suite2p_processing_tracker.yaml tracker file. This file stores the current state of the 
    sl-suite2p single-day data processing pipeline."""
    behavior_processing_tracker_path: Path = Path()
    """Stores the path to the behavior_processing_tracker.yaml file. This file stores the current state of the 
    behavior (log) data processing pipeline."""
    video_processing_tracker_path: Path = Path()
    """Stores the path to the video_processing_tracker.yaml file. This file stores the current state of the video 
    tracking (DeepLabCut) processing pipeline."""
    p53_path: Path = Path()
    """Stores the path to the p53.bin file. This file serves as a lock-in marker that determines whether the session is 
    in the processing or dataset mode. Specifically, if the file does not exist, the session data cannot be integrated 
    into any dataset, as it may be actively worked on by processing pipelines. Conversely, if the marker exists, 
    processing pipelines are not allowed to work with the session, as it may be actively integrated into one or more 
    datasets."""

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
        self.suite2p_processing_tracker_path = self.processed_data_path.joinpath("suite2p_processing_tracker.yaml")
        self.behavior_processing_tracker_path = self.processed_data_path.joinpath("behavior_processing_tracker.yaml")
        self.video_processing_tracker_path = self.processed_data_path.joinpath("video_processing_tracker.yaml")
        self.p53_path = self.processed_data_path.joinpath("p53.bin")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories."""

        ensure_directory_exists(self.processed_data_path)
        ensure_directory_exists(self.camera_data_path)
        ensure_directory_exists(self.behavior_data_path)


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
    """Stores the name of the managed session's project."""
    animal_id: str
    """Stores the unique identifier of the animal that participates in the managed session."""
    session_name: str
    """Stores the name (timestamp-based ID) of the managed session."""
    session_type: str
    """Stores the type of the session. Primarily, this determines how to read the session_descriptor.yaml file. Has 
    to be set to one of the supported types: 'lick training', 'run training', 'window checking' or 
    'mesoscope experiment'.
    """
    acquisition_system: str
    """Stores the name of the data acquisition and runtime management system that acquired the data."""
    experiment_name: str | None
    """Stores the name of the experiment configuration file. If the session_type field is set to 'Experiment' and this 
    field is not None (null), it communicates the specific experiment configuration used by the session. During runtime,
    the name stored here is used to load the specific experiment configuration data stored in a .yaml file with the 
    same name. If the session is not an experiment session, this field is ignored."""
    python_version: str = "3.11.13"
    """Stores the Python version used to acquire raw session data."""
    sl_experiment_version: str = "2.0.0"
    """Stores the version of the sl-experiment library that was used to acquire the raw session data."""
    raw_data: RawData = field(default_factory=lambda: RawData())
    """Stores the paths to all subfolders and files found under the /project/animal/session/raw_data directory of any 
    PC used to work with Sun lab data."""
    processed_data: ProcessedData = field(default_factory=lambda: ProcessedData())
    """Stores the paths to all subfolders and files found under the /project/animal/session/processed_data directory of 
    any PC used to work with Sun lab data."""

    def __post_init__(self) -> None:
        """Ensures raw_data and processed_data are always instances of RawData and ProcessedData."""
        if not isinstance(self.raw_data, RawData):
            self.raw_data = RawData()

        if not isinstance(self.processed_data, ProcessedData):
            self.processed_data = ProcessedData()

    @classmethod
    def create(
        cls,
        project_name: str,
        animal_id: str,
        session_type: str,
        experiment_name: str | None = None,
        session_name: str | None = None,
        python_version: str = "3.11.13",
        sl_experiment_version: str = "2.0.0",
    ) -> "SessionData":
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
            python_version: The string that specifies the Python version used to collect raw session data. Has to be
                specified using the major.minor.patch version format.
            sl_experiment_version: The string that specifies the version of the sl-experiment library used to collect
                raw session data. Has to be specified using the major.minor.patch version format.

        Returns:
            An initialized SessionData instance that stores the layout of the newly created session's data.
        """

        if session_type.lower() not in _valid_session_types:
            message = (
                f"Invalid session type '{session_type.lower()}' encountered when creating a new SessionData instance. "
                f"Use one of the supported session types: {_valid_session_types}"
            )
            console.error(message=message, error=ValueError)

        # Acquires the UTC timestamp to use as the session name, unless a name override is provided
        if session_name is None:
            session_name = str(get_timestamp(time_separator="-"))

        # Resolves the acquisition system configuration. This queries the acquisition system configuration data used
        # by the machine (PC) that calls this method.
        acquisition_system = get_system_configuration_data()

        # Constructs the root session directory path
        session_path = acquisition_system.paths.root_directory.joinpath(project_name, animal_id, session_name)

        # Prevents creating new sessions for non-existent projects.
        if not acquisition_system.paths.root_directory.joinpath(project_name).exists():
            message = (
                f"Unable to create the session directory hierarchy for the session {session_name} of the animal "
                f"'{animal_id}' and project '{project_name}'. The project does not exist on the local machine (PC). "
                f"Use the 'sl-create-project' CLI command to create the project on the local machine before creating "
                f"new sessions."
            )
            console.error(message=message, error=FileNotFoundError)

        # Handles potential session name conflicts
        counter = 0
        while session_path.exists():
            counter += 1
            new_session_name = f"{session_name}_{counter}"
            session_path = acquisition_system.paths.root_directory.joinpath(project_name, animal_id, new_session_name)

        # If a conflict is detected and resolved, warns the user about the resolved conflict.
        if counter > 0:
            message = (
                f"Session name conflict occurred for animal '{animal_id}' of project '{project_name}' "
                f"when adding the new session with timestamp {session_name}. The session with identical name "
                f"already exists. The newly created session directory uses a '_{counter}' postfix to distinguish "
                f"itself from the already existing session directory."
            )
            # noinspection PyTypeChecker
            console.echo(message=message, level=LogLevel.ERROR)

        # Generates subclasses stored inside the main class instance based on the data resolved above.
        raw_data = RawData()
        raw_data.resolve_paths(root_directory_path=session_path.joinpath("raw_data"))
        raw_data.make_directories()  # Generates the local 'raw_data' directory tree

        # Resolves, but does not make processed_data directories. All runtimes that require access to 'processed_data'
        # are configured to generate those directories if necessary, so there is no need to make them here.
        processed_data = ProcessedData()
        processed_data.resolve_paths(root_directory_path=session_path.joinpath("processed_data"))

        # Packages the sections generated above into a SessionData instance
        # noinspection PyArgumentList
        instance = SessionData(
            project_name=project_name,
            animal_id=animal_id,
            session_name=session_name,
            session_type=session_type.lower(),
            acquisition_system=acquisition_system.name,
            raw_data=raw_data,
            processed_data=processed_data,
            experiment_name=experiment_name,
            python_version=python_version,
            sl_experiment_version=sl_experiment_version,
        )

        # Saves the configured instance data to the session's folder, so that it can be reused during processing or
        # preprocessing.
        instance._save()

        # Also saves the ProjectConfiguration, SystemConfiguration, and ExperimentConfiguration instances to the same
        # folder using the paths resolved for the RawData instance above.

        # Copies the project_configuration.yaml file to session's folder
        project_configuration_path = acquisition_system.paths.root_directory.joinpath(
            project_name, "configuration", "project_configuration.yaml"
        )
        sh.copy2(project_configuration_path, instance.raw_data.project_configuration_path)

        # Dumps the acquisition system's configuration data to session's folder
        acquisition_system.save(path=instance.raw_data.system_configuration_path)

        if experiment_name is not None:
            # Copies the experiment_configuration.yaml file to session's folder
            experiment_configuration_path = acquisition_system.paths.root_directory.joinpath(
                project_name, "configuration", f"{experiment_name}.yaml"
            )
            sh.copy2(experiment_configuration_path, instance.raw_data.experiment_configuration_path)

        # Returns the initialized SessionData instance to caller
        return instance

    @classmethod
    def load(
        cls,
        session_path: Path,
        processed_data_root: Path | None = None,
        make_processed_data_directory: bool = False,
    ) -> "SessionData":
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

        # Unless a different root is provided for processed data, it uses the same root as raw_data.
        if processed_data_root is None:
            processed_data_root = local_root

        # Regenerates the processed_data path depending on the root resolution above
        instance.processed_data.resolve_paths(
            root_directory_path=processed_data_root.joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "processed_data"
            )
        )

        # Generates processed data directories if requested and necessary
        if make_processed_data_directory:
            instance.processed_data.make_directories()

        # Returns the initialized SessionData instance to caller
        return instance

    def _save(self) -> None:
        """Saves the instance data to the 'raw_data' directory of the managed session as a 'session_data.yaml' file.

        This is used to save the data stored in the instance to disk, so that it can be reused during preprocessing or
        data processing. The method is intended to only be used by the SessionData instance itself during its
        create() method runtime.
        """

        # Generates a copy of the original class to avoid modifying the instance that will be used for further
        # processing
        origin = copy.deepcopy(self)

        # Resets all path fields to null. These fields are not loaded from disk when the instance is loaded, so setting
        # them to null has no negative consequences. Conversely, keeping these fields with Path objects prevents the
        # SessionData instance from being loaded from disk.
        origin.raw_data = None  # type: ignore
        origin.processed_data = None  # type: ignore

        # Saves instance data as a .YAML file
        origin.to_yaml(file_path=self.raw_data.session_data_path)


@dataclass()
class ProcessingTracker(YamlConfig):
    """Wraps the .yaml file that tracks the state of a data processing runtime and provides tools for communicating the
    state between multiple processes in a thread-safe manner.

    Primarily, this tracker class is used by all remote data processing pipelines in the lab to prevent race conditions
    and make it impossible to run multiple processing runtimes at the same time.
    """

    file_path: Path
    """Stores the path to the .yaml file used to save the tracker data between runtimes. The class instance functions as
    a wrapper around the data stored inside the specified .yaml file."""
    _is_complete: bool = False
    """Tracks whether the processing runtime managed by this tracker has been successfully carried out for the session 
    that calls the tracker."""
    _encountered_error: bool = False
    """Tracks whether the processing runtime managed by this tracker has encountered an error while running for the 
    session that calls the tracker."""
    _is_running: bool = False
    """Tracks whether the processing runtime managed by this tracker is currently running for the session that calls 
    the tracker."""
    _lock_path: str = field(init=False)
    """Stores the path to the .lock file for the target tracker .yaml file. This file is used to ensure that only one 
    process can simultaneously read from or write to the wrapped .yaml file."""

    def __post_init__(self) -> None:
        # Generates the lock file for the target .yaml file path.
        if self.file_path is not None:
            self._lock_path = str(self.file_path.with_suffix(self.file_path.suffix + ".lock"))
        else:
            self._lock_path = ""

    def _load_state(self) -> None:
        """Reads the current processing state from the wrapped .YAML file."""
        if self.file_path.exists():
            # Loads the data for the state values, but does not replace the file path or lock attributes.
            instance: ProcessingTracker = self.from_yaml(self.file_path)  # type: ignore
            self._is_complete = instance._is_complete
            self._encountered_error = instance._encountered_error
            self._is_running = instance._is_running
        else:
            # Otherwise, if the tracker file does not exist, generates a new .yaml file using default instance values.
            self._save_state()

    def _save_state(self) -> None:
        """Saves the current processing state stored inside instance attributes to the specified .YAML file."""
        # Resets the _lock and file_path to None before dumping the data to .YAML to avoid issues with loading it
        # back.
        original = copy.deepcopy(self)
        original.file_path = None  # type: ignore
        original._lock_path = None  # type: ignore
        original.to_yaml(file_path=self.file_path)

    def start(self) -> None:
        """Configures the tracker file to indicate that the tracked processing runtime is currently running.

        All further attempts to start the same processing runtime for the same session's data will automatically abort
        with an error.

        Raises:
            TimeoutError: If the file lock for the target .YAML file cannot be acquired within the timeout period.
        """
        try:
            # Acquires the lock
            lock = FileLock(self._lock_path)
            with lock.acquire(timeout=10.0):
                # Loads tracker state from .yaml file
                self._load_state()

                # If the runtime is already running, aborts with an error
                if self._is_running:
                    message = (
                        f"Unable to start the processing runtime. The {self.file_path.name} tracker file indicates "
                        f"that the runtime is currently running from a different process. Only a single runtime "
                        f"instance is allowed to run at the same time."
                    )
                    console.error(message=message, error=RuntimeError)
                    raise RuntimeError(message)  # Fallback to appease mypy, should not be reachable

                # Otherwise, marks the runtime as running and saves the state back to the .yaml file.
                self._is_running = True
                self._is_complete = False
                self._encountered_error = False
                self._save_state()

        # If lock acquisition fails for any reason, aborts with an error
        except Timeout:
            message = (
                f"Unable to interface with the ProcessingTracker instance data cached inside the target .yaml file "
                f"{self.file_path.stem}. Specifically, unable to acquire the file lock before the timeout duration of "
                f"10 minutes has passed."
            )
            console.error(message=message, error=Timeout)
            raise Timeout(message)  # Fallback to appease mypy, should not be reachable

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

        try:
            # Acquires the lock
            lock = FileLock(self._lock_path)
            with lock.acquire(timeout=10.0):
                # Loads tracker state from .yaml file
                self._load_state()

                # If the runtime is not running, aborts with an error
                if not self._is_running:
                    message = (
                        f"Unable to report that the processing runtime encountered an error. The {self.file_path.name} "
                        f"tracker file indicates that the runtime is currently NOT running. A runtime has to be "
                        f"actively running to set the tracker to an error state."
                    )
                    console.error(message=message, error=RuntimeError)
                    raise RuntimeError(message)  # Fallback to appease mypy, should not be reachable

                # Otherwise, indicates that the runtime aborted with an error
                self._is_running = False
                self._is_complete = False
                self._encountered_error = True
                self._save_state()

        # If lock acquisition fails for any reason, aborts with an error
        except Timeout:
            message = (
                f"Unable to interface with the ProcessingTracker instance data cached inside the target .yaml file "
                f"{self.file_path.stem}. Specifically, unable to acquire the file lock before the timeout duration of "
                f"10 minutes has passed."
            )
            console.error(message=message, error=Timeout)
            raise Timeout(message)  # Fallback to appease mypy, should not be reachable

    def stop(self) -> None:
        """Mark processing as started.

        Raises:
            TimeoutError: If the file lock for the target .YAML file cannot be acquired within the timeout period.
        """

        try:
            # Acquires the lock
            lock = FileLock(self._lock_path)
            with lock.acquire(timeout=10.0):
                # Loads tracker state from .yaml file
                self._load_state()

                # If the runtime is not running, aborts with an error
                if not self._is_running:
                    message = (
                        f"Unable to stop (complete) the processing runtime. The {self.file_path.name} tracker file "
                        f"indicates that the runtime is currently NOT running. A runtime has to be actively running to "
                        f"mark it as complete and stop the runtime."
                    )
                    console.error(message=message, error=RuntimeError)
                    raise RuntimeError(message)  # Fallback to appease mypy, should not be reachable

                # Otherwise, marks the runtime as complete (stopped)
                self._is_running = False
                self._is_complete = True
                self._encountered_error = False
                self._save_state()

        # If lock acquisition fails for any reason, aborts with an error
        except Timeout:
            message = (
                f"Unable to interface with the ProcessingTracker instance data cached inside the target .yaml file "
                f"{self.file_path.stem}. Specifically, unable to acquire the file lock before the timeout duration of "
                f"10 minutes has passed."
            )
            console.error(message=message, error=Timeout)
            raise Timeout(message)  # Fallback to appease mypy, should not be reachable

    @property
    def is_complete(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing runtime has been completed
        successfully and False otherwise."""
        try:
            # Acquires the lock
            lock = FileLock(self._lock_path)
            with lock.acquire(timeout=10.0):
                # Loads tracker state from .yaml file
                self._load_state()
                return self._is_complete

            # If lock acquisition fails for any reason, aborts with an error
        except Timeout:
            message = (
                f"Unable to interface with the ProcessingTracker instance data cached inside the target .yaml file "
                f"{self.file_path.stem}. Specifically, unable to acquire the file lock before the timeout duration of "
                f"10 minutes has passed."
            )
            console.error(message=message, error=Timeout)
            raise Timeout(message)  # Fallback to appease mypy, should not be reachable

    @property
    def encountered_error(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing runtime aborted due to
        encountering an error and False otherwise."""
        try:
            # Acquires the lock
            lock = FileLock(self._lock_path)
            with lock.acquire(timeout=10.0):
                # Loads tracker state from .yaml file
                self._load_state()
                return self._encountered_error

            # If lock acquisition fails for any reason, aborts with an error
        except Timeout:
            message = (
                f"Unable to interface with the ProcessingTracker instance data cached inside the target .yaml file "
                f"{self.file_path.stem}. Specifically, unable to acquire the file lock before the timeout duration of "
                f"10 minutes has passed."
            )
            console.error(message=message, error=Timeout)
            raise Timeout(message)  # Fallback to appease mypy, should not be reachable

    @property
    def is_running(self) -> bool:
        """Returns True if the tracker wrapped by the instance indicates that the processing runtime is currently
        running and False otherwise."""
        try:
            # Acquires the lock
            lock = FileLock(self._lock_path)
            with lock.acquire(timeout=10.0):
                # Loads tracker state from .yaml file
                self._load_state()
                return self._is_running

            # If lock acquisition fails for any reason, aborts with an error
        except Timeout:
            message = (
                f"Unable to interface with the ProcessingTracker instance data cached inside the target .yaml file "
                f"{self.file_path.stem}. Specifically, unable to acquire the file lock before the timeout duration of "
                f"10 minutes has passed."
            )
            console.error(message=message, error=Timeout)
            raise Timeout(message)  # Fallback to appease mypy, should not be reachable
