"""This module provides classes jointly responsible for maintaining the Sun lab project data hierarchy across all
machines used to acquire, process, and store the data. Primarily, classes from this module are used to manage the
access to the data acquired as part of a single data acquisition session in a thread-safe and location-agnostic
fashion."""

import copy
from enum import StrEnum
import shutil as sh
from pathlib import Path
from dataclasses import field, dataclass

from filelock import FileLock
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig
from ataraxis_time.time_helpers import get_timestamp

from .configuration_data import AcquisitionSystems, get_system_configuration_data
from ..tools.transfer_tools import delete_directory


class SessionTypes(StrEnum):
    """Stores the data acquisition session types supported by all data acquisition systems used in the Sun lab.

    A data acquisition session is typically carried out to acquire experiment data, train the animal for the upcoming
    experiment sessions, or to assess the quality of surgical or other pre-experiment interventions. After acquisition,
    the session is treated as a uniform package whose components can be accessed via the SessionData class.

    Notes:
        Different acquisition systems support different session types and may not be suited for acquiring some of the
        session types listed in this enumeration.
    """

    LICK_TRAINING = "lick training"
    """A Mesoscope-VR session designed to teach animals to use the water delivery port while being head-fixed."""
    RUN_TRAINING = "run training"
    """A Mesoscope-VR session designed to teach animals to run on the treadmill while being head-fixed."""
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    """A Mesoscope-VR experiment session. The session uses Unity game engine to run virtual reality tasks and collects 
    brain activity data using 2-Photon Random Access Mesoscope (2P-RAM)."""
    WINDOW_CHECKING = "window checking"
    """A Mesoscope-VR session designed to evaluate the quality of the cranial window implantation procedure and the 
    suitability of the animal for being imaged with the Mesoscope. The session uses the Mesoscope to assess the quality 
    of the cell activity data."""


@dataclass()
class RawData:
    """Stores the paths to the directories and files that make up the 'raw_data' session-specific directory.

    The raw_data directory stores the data acquired during the session data acquisition runtime, before and after
    preprocessing. Since preprocessing does not irreversibly alter the data, any data in that folder is considered
    'raw,' event if preprocessing losslessly re-compresses the data for efficient transfer.

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
    includes the mesoscope-acquired .tiff files (brain activity data) and the MotionEstimator.me file (motion 
    estimation data). This directory is created for all sessions, but is only used (filled) by the sessions that use 
    the Mesoscope-VR system to acquire brain activity data."""
    behavior_data_path: Path = Path()
    """Stores the path to the directory that contains all non-video behavior data acquired during the session. 
    Primarily, this includes the .npz log files that store serialized data acquired by all hardware components of the 
    data acquisition system other than cameras and brain activity data acquisition devices (such as the Mesoscope)."""
    zaber_positions_path: Path = Path()
    """Stores the path to the zaber_positions.yaml file. This file contains the snapshot of all Zaber motor positions 
    at the end of the session. Zaber motors are used to position the LickPort, HeadBar, and Wheel Mesoscope-VR modules
    to support proper brain activity recording and behavior during the session. This file is only created for sessions 
    that use the Mesoscope-VR system."""
    session_descriptor_path: Path = Path()
    """Stores the path to the session_descriptor.yaml file. This file is filled jointly by the data acquisition system 
    and the experimenter. It contains session-specific information, such as the specific task parameters and the notes 
    made by the experimenter during runtime. Each supported session type uses a unique SessionDescriptor class to define
    the format and content of the session_descriptor.yaml file."""
    hardware_state_path: Path = Path()
    """Stores the path to the hardware_state.yaml file. This file contains the partial snapshot of the calibration 
    parameters used by the data acquisition system modules during the session. Primarily, it is used during data 
    processing to interpret the raw data stored inside .npz log files."""
    surgery_metadata_path: Path = Path()
    """Stores the path to the surgery_metadata.yaml file. This file contains the most actual information about the 
    surgical intervention(s) performed on the animal prior to the session."""
    session_data_path: Path = Path()
    """Stores the path to the session_data.yaml file. This path is used by the SessionData instance to save itself to 
    disk as a .yaml file. In turn, the cached data is reused to reinstate the same data hierarchy across all supported 
    destinations, enabling various libraries to interface with the session data."""
    experiment_configuration_path: Path = Path()
    """Stores the path to the experiment_configuration.yaml file. This file contains the snapshot of the 
    experiment runtime configuration used by the session. This file is only created for experiment sessions."""
    mesoscope_positions_path: Path = Path()
    """Stores the path to the mesoscope_positions.yaml file. This file contains the snapshot of the positions used
    by the Mesoscope at the end of the session. This includes both the physical position of the mesoscope objective and
    the 'virtual' tip, tilt, and fastZ positions set via ScanImage software. This file is only created for sessions that
    use the Mesoscope-VR system to acquire brain activity data."""
    window_screenshot_path: Path = Path()
    """Stores the path to the .png screenshot of the ScanImagePC screen. As a minimum, the screenshot should contain the
    image of the imaging plane and the red-dot alignment window. This is used to generate a visual snapshot of the 
    cranial window alignment and cell appearance for each experiment session. This file is only created for sessions 
    that use the Mesoscope-VR system to acquire brain activity data."""
    system_configuration_path: Path = Path()
    """Stores the path to the system_configuration.yaml file. This file contains the exact snapshot of the data 
    acquisition system configuration parameters used to acquire session data."""
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
    """Stores the path to the ubiquitin.bin file. This file is primarily used by the sl-experiment library to mark 
    local session data directories for deletion (purging). Typically, it is created once the data is safely moved to 
    the long-term storage destinations (NAS and Server) and the integrity of the moved data is verified on at least one 
    destination. During 'sl-purge' sl-experiment runtimes, the library discovers and removes all session data marked 
    with 'ubiquitin.bin' files from the machine that runs the command."""
    nk_path: Path = Path()
    """Stores the path to the nk.bin file. This file is used by the sl-experiment library to mark sessions undergoing
    runtime initialization. Since runtime initialization is a complex process that may encounter a runtime error, the 
    marker is used to discover sessions that failed to initialize. Since uninitialized sessions by definition do not 
    contain any valuable data, they are marked for immediate deletion from all managed destinations."""
    root_path: Path = Path()
    """Stores the path to the root directory of the volume that stores raw data from all Sun lab projects. Primarily,
    this is necessary for pipelines working with the data on the remote compute server to efficiently move it between 
    storage and working (processing) volumes."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the (wrapper) SessionData class is instantiated to regenerate the managed path
        hierarchy on any machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the session. Typically, this path is assembled
                using the following hierarchy: root/project/animal/session_id
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
        self.session_data_path = self.raw_data_path.joinpath("session_data.yaml")
        self.experiment_configuration_path = self.raw_data_path.joinpath("experiment_configuration.yaml")
        self.mesoscope_positions_path = self.raw_data_path.joinpath("mesoscope_positions.yaml")
        self.window_screenshot_path = self.raw_data_path.joinpath("window_screenshot.png")
        self.checksum_path = self.raw_data_path.joinpath("ax_checksum.txt")
        self.system_configuration_path = self.raw_data_path.joinpath("system_configuration.yaml")
        self.telomere_path = self.raw_data_path.joinpath("telomere.bin")
        self.ubiquitin_path = self.raw_data_path.joinpath("ubiquitin.bin")
        self.nk_path = self.raw_data_path.joinpath("nk.bin")

        # Infers the path to the root raw data directory under which the session's project is stored. This assumes that
        # the raw_data directory is found under root/project/animal/session_id/raw_data
        self.root_path = root_directory_path.parents[3]

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories.

        This method is called each time the (wrapper) SessionData class is instantiated and allowed to generate
        missing data directories.
        """
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
    """Stores the path to the root processed_data directory of the session. This directory stores the processed session 
    data, generated from raw_data directory contents by various data processing pipelines."""
    camera_data_path: Path = Path()
    """Stores the path to the directory that contains video tracking data generated by the Sun lab DeepLabCut-based 
    video processing pipeline(s)."""
    mesoscope_data_path: Path = Path()
    """Stores path to the directory that contains processed brain activity (cell) data generated by sl-suite2p 
    processing pipelines (single-day and multi-day). This directory is only used by sessions acquired with 
    the Mesoscope-VR system."""
    behavior_data_path: Path = Path()
    """Stores the path to the directory that contains the non-video and non-brain-activity data extracted from 
    .npz log files by the sl-behavior log processing pipeline."""
    root_path: Path = Path()
    """Stores the path to the root directory of the volume that stores processed data from all Sun lab projects. 
    Primarily, this is necessary for pipelines working with the data on the remote compute server to efficiently move it
    between storage and working (processing) volumes."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the (wrapper) SessionData class is instantiated to regenerate the managed path
        hierarchy on any machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the session. Typically, this path is assembled
                using the following hierarchy: root/project/animal/session_id
        """
        # Generates the managed paths
        self.processed_data_path = root_directory_path
        self.camera_data_path = self.processed_data_path.joinpath("camera_data")
        self.mesoscope_data_path = self.processed_data_path.joinpath("mesoscope_data")
        self.behavior_data_path = self.processed_data_path.joinpath("behavior_data")

        # Infers the path to the root processed data directory under which the session's project is stored. This
        # assumes that the processed_data directory is found under root/project/animal/session_id/processed_data
        self.root_path = root_directory_path.parents[3]

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories.

        This method is called each time the (wrapper) SessionData class is instantiated and allowed to generate
        missing data directories.
        """

        ensure_directory_exists(self.processed_data_path)
        ensure_directory_exists(self.camera_data_path)
        ensure_directory_exists(self.behavior_data_path)


@dataclass()
class TrackingData:
    """Stores the paths to the directories and files that make up the 'tracking_data' session-specific directory.

    This directory was added in version 5.0.0 to store the ProcessingTracker files and .lock files for pipelines and
    tasks used to work with session's data after acquisition.
    """

    tracking_data_path: Path = Path()
    """Stores the path to the root tracking_data directory of the session. This directory stores the .yaml 
    ProcessingTracker files and the .lock FileLock files that jointly ensure that session's data is accessed in a 
    thread-safe way while being processed by multiple different processes and pipelines."""
    session_lock_path: Path = Path()
    """Stores the path to the session's session_lock.yaml file. This file is used to ensure that only a single 
    manager process has exclusive access to the session's data on the remote compute server. This allows multiple 
    data processing pipelines to safely run for the same session without compromising session data integrity. This 
    file is intended to be used through the SessionLock class."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        This method is called each time the (wrapper) SessionData class is instantiated to regenerate the managed path
        hierarchy on any machine that instantiates the class.

        Args:
            root_directory_path: The path to the top-level directory of the session. Typically, this path is assembled
                using the following hierarchy: root/project/animal/session_id
        """
        # Generates the managed paths
        self.tracking_data_path = root_directory_path
        self.session_lock_path = self.tracking_data_path.joinpath("session_lock.yaml")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories.

        This method is called each time the (wrapper) SessionData class is instantiated and allowed to generate
        missing data directories.
        """

        ensure_directory_exists(self.tracking_data_path)


@dataclass
class SessionData(YamlConfig):
    """Stores and manages the data layout of a single Sun lab data acquisition session.

    The primary purpose of this class is to maintain the session data structure across all supported destinations
    and to provide a unified data access interface shared by all Sun lab libraries. It is specifically designed for
    working with the data from a single session, performed by a single animal under the specific project. The class is
    used to manage both raw and processed data: it follows the data through acquisition, preprocessing, and processing
    stages of the Sun lab data workflow. This class serves as an entry point for all interactions with the managed
    session's data.

    Notes:
        The class is not designed to be instantiated directly. Instead, use the create() method to generate a new
        session or load() method to access the data of an already existing session.

        When the class is used to create a new session, it generates the new session's name using the current UTC
        timestamp, accurate to microseconds. This ensures that each session 'name' is unique and preserves the overall
        session order.
    """

    project_name: str
    """Stores the name of the project for which the session was acquired."""
    animal_id: str
    """Stores the unique identifier of the animal that participates in the session."""
    session_name: str
    """Stores the name (timestamp-based ID) of the session."""
    session_type: str | SessionTypes
    """Stores the type of the session. Has to be set to one of the supported session types, defined in the SessionTypes
    enumeration exposed by the sl-shared-assets library.
    """
    acquisition_system: str | AcquisitionSystems = AcquisitionSystems.MESOSCOPE_VR
    """Stores the name of the data acquisition system that acquired the data. Has to be set to one of the supported 
    acquisition systems, defined in the AcquisitionSystems enumeration exposed by the sl-shared-assets library."""
    experiment_name: str | None = None
    """Stores the name of the experiment performed during the session. If the session_type field indicates that the 
    session is an experiment, this field communicates the specific experiment configuration used by the session. During 
    runtime, this name is used to load the specific experiment configuration data stored in a .yaml file with the same 
    name. If the session is not an experiment session, this field should be left as Null (None)."""
    python_version: str = "3.11.13"
    """Stores the Python version that was used to acquire session data."""
    sl_experiment_version: str = "3.0.0"
    """Stores the version of the sl-experiment library that was used to acquire the session data."""
    raw_data: RawData = field(default_factory=lambda: RawData())
    """Stores absolute paths to all directories and files that jointly make the session's raw data hierarchy. This 
    hierarchy is initially resolved by the acquisition system that acquires the session and used to store all data 
    acquired during the session runtime."""
    processed_data: ProcessedData = field(default_factory=lambda: ProcessedData())
    """Stores absolute paths to all directories and files that jointly make the session's processed data hierarchy. 
    Processed data encompasses all data generated from the raw data as part of data processing."""
    source_data: RawData = field(default_factory=lambda: RawData())
    """Stores absolute paths to the same data as the 'raw_data' field, but with all paths resolved relative to the 
    'processed_data' root. On systems that use the same root for processed and raw data, the source and raw directories 
    are identical. On systems that use different root directories for processed and raw data, the source and raw 
    directories are different. This is used to optimize data processing on the remote compute server by temporarily 
    copying all session data to the fast processed data volume."""
    archived_data: ProcessedData = field(default_factory=lambda: ProcessedData())
    """Similar to the 'source_data' field, stores the absolute path to the same data as the 'processed_data' field, but 
    with all paths resolved relative to the 'raw_data' root. This path is used as part of the session data archiving 
    process to collect all session data (raw and processed) on the slow 'storage' volume of the remote compute server.
    """
    tracking_data: TrackingData = field(default_factory=lambda: TrackingData())
    """Stores absolute paths to all directories and files that jointly make the session's tracking data hierarchy. This 
    hierarchy is used during all stages of data processing to track the processing progress and ensure only a single 
    manager process can modify the session's data at any given time, ensuring access safety."""

    def __post_init__(self) -> None:
        """Ensures raw_data, processed_data, and source_data are always instances of RawData and ProcessedData."""
        if not isinstance(self.raw_data, RawData):
            self.raw_data = RawData()

        if not isinstance(self.processed_data, ProcessedData):
            self.processed_data = ProcessedData()

        if not isinstance(self.source_data, RawData):
            self.raw_data = RawData()

        if not isinstance(self.archived_data, ProcessedData):
            self.archived_data = ProcessedData()

        if not isinstance(self.tracking_data, TrackingData):
            self.raw_data = RawData()

    @classmethod
    def create(
        cls,
        project_name: str,
        animal_id: str,
        session_type: SessionTypes | str,
        python_version: str,
        sl_experiment_version: str,
        experiment_name: str | None = None,
        session_name: str | None = None,
    ) -> "SessionData":
        """Creates a new SessionData object and generates the new session's data structure on the local PC.

        This method is intended to be called exclusively by the sl-experiment library to create new training or
        experiment sessions and generate the session data directory tree.

        Notes:
            To load an already existing session data structure, use the load() method instead.

            This method automatically dumps the data of the created SessionData instance into the session_data.yaml file
            inside the root 'raw_data' directory of the created hierarchy. It also finds and dumps other configuration
            files, such as experiment_configuration.yaml and system_configuration.yaml into the same 'raw_data'
            directory. If the session's runtime is interrupted unexpectedly, the acquired data can still be processed
            using these pre-saved class instances.

        Args:
            project_name: The name of the project for which the session is carried out.
            animal_id: The ID code of the animal participating in the session.
            session_type: The type of the session. Has to be one of the supported session types exposed by the
                SessionTypes enumeration.
            python_version: The string that specifies the Python version used to collect session data. Has to be
                specified using the major.minor.patch version format.
            sl_experiment_version: The string that specifies the version of the sl-experiment library used to collect
                session data. Has to be specified using the major.minor.patch version format.
            experiment_name: The name of the experiment executed during the session. This optional argument is only
                used for experiment sessions. Note! The name passed to this argument has to match the name of the
                experiment configuration .yaml file.
            session_name: An optional session name override. Generally, this argument should not be provided for most
                sessions. When provided, the method uses this name instead of generating a new timestamp-based name.
                This is only used during the 'ascension' runtime to convert old data structures to the modern
                lab standards.

        Returns:
            An initialized SessionData instance that stores the layout of the newly created session's data.
        """

        # Need to convert to tuple to support Python 3.11
        if session_type not in tuple(SessionTypes):
            message = (
                f"Invalid session type '{session_type}' encountered when creating a new SessionData instance. "
                f"Use one of the supported session types from the SessionTypes enumeration."
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

        # Resolves but does not make processed_data directories. All runtimes that require access to 'processed_data'
        # are configured to generate those directories if necessary, so there is no need to make them here.
        processed_data = ProcessedData()
        processed_data.resolve_paths(root_directory_path=session_path.joinpath("processed_data"))

        # Added in version 5.0.0. While source data is not used when the session is created (and is set to the same
        # directory as raw_data), it is created here for completeness.
        source_data = RawData()
        source_data.resolve_paths(root_directory_path=session_path.joinpath("source_data"))

        # Added in version 5.0.0. While processed data is not used when the session is created (and is set to the same
        # directory as processed_data), it is created here for completeness.
        archived_data = ProcessedData()
        archived_data.resolve_paths(root_directory_path=session_path.joinpath("archived_data"))

        # Similar to source_data, tracking data uses the same root as raw_data and is not used during data acquisition.
        # Tracking data is used during data processing on the remote compute server(s) to ensure multiple pipelines
        # can work with the session's data without collision.
        tracking_data = TrackingData()
        tracking_data.resolve_paths(root_directory_path=session_path.joinpath("tracking_data"))

        # Packages the sections generated above into a SessionData instance
        # noinspection PyArgumentList
        instance = SessionData(
            project_name=project_name,
            animal_id=animal_id,
            session_name=session_name,
            session_type=session_type,
            acquisition_system=acquisition_system.name,
            raw_data=raw_data,
            source_data=source_data,
            processed_data=processed_data,
            experiment_name=experiment_name,
            python_version=python_version,
            sl_experiment_version=sl_experiment_version,
        )

        # Saves the configured instance data to the session's folder so that it can be reused during processing or
        # preprocessing.
        instance.save()

        # Also saves the SystemConfiguration and ExperimentConfiguration instances to the same folder using the paths
        # resolved for the RawData instance above.

        # Dumps the acquisition system's configuration data to the session's folder
        acquisition_system.save(path=instance.raw_data.system_configuration_path)

        if experiment_name is not None:
            # Copies the experiment_configuration.yaml file to the session's folder
            experiment_configuration_path = acquisition_system.paths.root_directory.joinpath(
                project_name, "configuration", f"{experiment_name}.yaml"
            )
            sh.copy2(experiment_configuration_path, instance.raw_data.experiment_configuration_path)

        # All newly created sessions are marked with the 'nk.bin' file. If the marker is not removed during runtime,
        # the session becomes a valid target for deletion (purging) runtimes operating from the main acquisition
        # machine of any data acquisition system.
        instance.raw_data.nk_path.touch()

        # Returns the initialized SessionData instance to caller
        return instance

    @classmethod
    def load(
        cls,
        session_path: Path,
        processed_data_root: Path | None = None,
    ) -> "SessionData":
        """Loads the SessionData instance from the target session's session_data.yaml file.

        This method is used to load the data layout information of an already existing session. Primarily, this is used
        when processing session data. Due to how SessionData is stored and used in the lab, this method always loads the
        data layout from the session_data.yaml file stored inside the 'raw_data' session subfolder. Currently, all
        interactions with Sun lab data require access to the 'raw_data' folder of each session.

        Notes:
            To create a new session, use the create() method instead.

        Args:
            session_path: The path to the root directory of an existing session, e.g.: root/project/animal/session.
            processed_data_root: If processed data is kept on a drive different from the one that stores raw data,
                provide the path to the root project directory (directory that stores all Sun lab projects) on that
                drive. The method will automatically resolve the project/animal/session/processed_data hierarchy using
                this root path. If raw and processed data are kept on the same drive, keep this set to None.

        Returns:
            An initialized SessionData instance for the session whose data is stored at the provided path.

        Raises:
            FileNotFoundError: If multiple or no 'session_data.yaml' file instances are found under the input session
                path directory.

        """
        # To properly initialize the SessionData instance, the provided path should contain a single session_data.yaml
        # file at any hierarchy level.
        session_data_files = [file for file in session_path.rglob("*session_data.yaml")]
        if len(session_data_files) != 1:
            message = (
                f"Unable to load the SessionData class for the target session. Expected a single session_data.yaml "
                f"file to be located under the directory tree specified by the input path: {session_path}. Instead, "
                f"encountered {len(session_data_files)} candidate files. This indicates that the input path does not "
                f"point to a valid session directory."
            )
            console.error(message=message, error=FileNotFoundError)

        # If a single candidate is found (as expected), extracts it from the list and uses it to resolve the
        # session data hierarchy.
        session_data_path = session_data_files.pop()

        # Loads class data from the.yaml file
        instance: SessionData = cls.from_yaml(file_path=session_data_path)  # type: ignore

        # The method assumes that the 'donor' .yaml file is always stored inside the raw_data directory of the session
        # to be processed. In turn, that directory is expected to be found under the path root/project/animal/session.
        # The code below uses this heuristic to discover the raw data root based on the session data file path.
        local_root = session_data_path.parents[4]  # Raw data root session directory

        # Unless a different root is provided for processed data, it uses the same root as raw_data.
        if processed_data_root is None:
            processed_data_root = local_root

        # RAW DATA
        instance.raw_data.resolve_paths(
            root_directory_path=local_root.joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "raw_data"
            )
        )

        # PROCESSED DATA
        instance.processed_data.resolve_paths(
            root_directory_path=processed_data_root.joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "processed_data"
            )
        )

        # If the processed data root is different from the raw data root, resolves the path to the 'source' and
        # 'archive' data directories. Otherwise, uses the same paths as 'raw' and 'processed' data directories.
        if processed_data_root != local_root:
            # SOURCE DATA
            instance.source_data.resolve_paths(
                root_directory_path=processed_data_root.joinpath(
                    instance.project_name, instance.animal_id, instance.session_name, "source_data"
                )
            )
            # Note, since source data is populated as part of the 'preparation' runtime, does not make the directories.

            # ARCHIVED DATA
            instance.archived_data.resolve_paths(
                root_directory_path=local_root.joinpath(
                    instance.project_name, instance.animal_id, instance.session_name, "archived_data"
                )
            )

            # If the session has been processed with the processed data root previously matching the raw data root,
            # ensures that there is no 'processed_data' directory on the raw data root. In other words, ensures that
            # the session data always has only a single copy of the 'processed_data' directory.
            old_processed_data_path = local_root.joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "processed_data"
            )
            delete_directory(old_processed_data_path)

        else:
            # SOURCE DATA
            instance.source_data.resolve_paths(
                root_directory_path=processed_data_root.joinpath(
                    instance.project_name, instance.animal_id, instance.session_name, "raw_data"
                )
            )

            # ARCHIVED DATA
            instance.archived_data.resolve_paths(
                root_directory_path=local_root.joinpath(
                    instance.project_name, instance.animal_id, instance.session_name, "processed_data"
                )
            )

        # Similar to source_data, archived data is populated as part of the 'archiving' pipeline, so directories for
        # this data are not resolved.

        # If there is no archived processed data, ensures that processed data hierarchy exists.
        if not instance.archived_data.processed_data_path.exists():
            instance.processed_data.make_directories()

        # TRACKING DATA
        instance.tracking_data.resolve_paths(
            root_directory_path=local_root.joinpath(
                instance.project_name, instance.animal_id, instance.session_name, "tracking_data"
            )
        )
        instance.tracking_data.make_directories()  # Ensures tracking data directories exist

        # Returns the initialized SessionData instance to caller
        return instance

    def runtime_initialized(self) -> None:
        """Ensures that the 'nk.bin' marker file is removed from the session's raw_data folder.

        The 'nk.bin' marker is generated as part of the SessionData initialization (creation) process to mark sessions
        that did not fully initialize during runtime. This service method is designed to be called by the sl-experiment
        library classes to remove the 'nk.bin' marker when it is safe to do so. It should not be called by end-users.
        """
        self.raw_data.nk_path.unlink(missing_ok=True)

    def save(self) -> None:
        """Saves the instance data to the 'raw_data' directory of the managed session as a 'session_data.yaml' file.

        This is used to save the data stored in the instance to disk so that it can be reused during further stages of
        data processing. The method is intended to only be used by the SessionData instance itself during its
        create() method runtime.
        """

        # Generates a copy of the original class to avoid modifying the instance that will be used for further
        # processing
        origin = copy.deepcopy(self)

        # Resets all path fields to null. These fields are not loaded from the disk when the instance is loaded, so
        # setting them to null has no negative consequences. Conversely, keeping these fields with Path objects
        # prevents the SessionData instance from being loaded from the disk.
        origin.raw_data = None  # type: ignore
        origin.processed_data = None  # type: ignore
        origin.source_data = None  # type: ignore
        origin.archived_data = None  # type: ignore
        origin.tracking_data = None  # type: ignore

        # Converts StringEnum instances to strings
        origin.session_type = str(origin.session_type)
        origin.acquisition_system = str(origin.acquisition_system)

        # Saves instance data as a .YAML file
        origin.to_yaml(file_path=self.raw_data.session_data_path)


@dataclass()
class SessionLock(YamlConfig):
    """Provides thread-safe session locking to ensure exclusive access during data processing.

    This class manages a lock file that tracks which manager process currently has exclusive access to a data
    acquisition session's data. It prevents race conditions when multiple manager processes attempt to modify session
    data simultaneously. Primarily, this class is used on remote compute server(s).

    Notes:
        The lock owner is identified by a manager process ID, allowing distributed processing across
        multiple jobs while maintaining data integrity.
    """

    file_path: Path
    """Stores the absolute path to the .yaml file that stores the lock state on disk."""

    _manager_id: int = -1
    """Stores the unique identifier of the manager process that holds the lock. A value of -1 indicates no lock."""

    _lock_path: str = field(init=False)
    """Stores the absolute path to the .lock file ensuring thread-safe access to the lock state."""

    def __post_init__(self) -> None:
        """Initializes the lock file path based on the .yaml file path."""
        if self.file_path is not None:
            self._lock_path = str(self.file_path.with_suffix(self.file_path.suffix + ".lock"))
        else:
            self._lock_path = ""

    def _load_state(self) -> None:
        """Loads the current lock state from the .yaml file."""
        if self.file_path.exists():
            instance: SessionLock = self.from_yaml(self.file_path)  # type: ignore
            self._manager_id = copy.copy(instance._manager_id)
        else:
            # Creates a new lock file with the default state (unlocked)
            self._save_state()

    def _save_state(self) -> None:
        """Saves the current lock state to the .yaml file."""
        # Creates a copy without file paths for clean serialization
        original = copy.deepcopy(self)
        original.file_path = None  # type: ignore
        original._lock_path = None  # type: ignore
        original.to_yaml(file_path=self.file_path)

    def acquire(self, manager_id: int) -> None:
        """Acquires the session access lock.

        Args:
            manager_id: The unique identifier of the manager process requesting the lock.

        Raises:
            TimeoutError: If the .lock file cannot be acquired for a long period of time due to being held by another
                process.
            RuntimeError: If the lock is held by another process and forcing lock acquisition is disabled.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            self._load_state()

            # Checks if the session is already locked by another process
            if self._manager_id != -1 and self._manager_id != manager_id:
                message = (
                    f"Unable to acquire the {self.file_path.parents[1].name} session's lock for the manager with "
                    f"id {manager_id}. The lock file indicates that the lock is already held by the process with id "
                    f"{self._manager_id}, preventing other processes from interfacing with the session lock. Call the "
                    f"command that produced this error with the '--reset-tracker' flag to override this safety "
                    f"feature or wait for the lock to be released."
                )
                console.error(message=message, error=RuntimeError)
                raise RuntimeError(message)

            # The lock is free or already owned by this manager. If the lock is free, locks the session for the current
            # manager. If it is already owned by this manager, it does nothing.
            self._manager_id = manager_id
            self._save_state()

    def release(self, manager_id: int) -> None:
        """Releases the session access lock.

        Args:
            manager_id: The unique identifier of the manager process releasing the lock.

        Raises:
            TimeoutError: If the .lock file cannot be acquired for a long period of time due to being held by another
                process.
            RuntimeError: If the lock is held by another process.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            self._load_state()

            if self._manager_id != manager_id:
                message = (
                    f"Unable to release the {self.file_path.parents[1].name} session's lock from the manager with "
                    f"id {manager_id}. The lock file indicates that the lock is held by the process with id "
                    f"{self._manager_id}, preventing other processes from interfacing with the session lock."
                )
                console.error(message=message, error=RuntimeError)
                raise RuntimeError(message)  # Fallback to appease mypy, should not be reachable

            # Releases the lock
            self._manager_id = -1
            self._save_state()

    def force_release(self) -> None:
        """Forcibly releases the session access lock regardless of ownership.

        This method should only be used for emergency recovery from improper processing shutdowns. It can be called by
        any process to unlock any session, but it does not attempt to terminate the processes that the lock's owner
        might have deployed to work with the session's data.

        Raises:
            TimeoutError: If the .lock file cannot be acquired for a long period of time due to being held by another
                process.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            # Hard reset regardless of the current tracker state
            self._manager_id = -1
            self._save_state()

    def check_owner(self, manager_id: int) -> None:
        """Ensures that the managed session is locked for processing by the specified manager process.

        This method is used by worker functions to ensure it is safe to interact with the session's data. It is designed
        to abort the runtime with an error if the session's lock file is owned by a different manager process.

        Args:
            manager_id: The unique identifier of the manager process attempting to access the session's data.

        Raises:
            TimeoutError: If the .lock file cannot be acquired for a long period of time due to being held by another
                process.
            ValueError: If the lock file is held by a different manager process.
        """
        lock = FileLock(self._lock_path)
        with lock.acquire(timeout=10.0):
            self._load_state()
            if self._manager_id != manager_id:
                message = (
                    f"Unable to access the {self.file_path.parents[1].name} session's data from manager process "
                    f"{manager_id}, as the session is currently locked by another manager process with ID "
                    f"{self._manager_id}."
                )
                console.error(message=message, error=ValueError)
