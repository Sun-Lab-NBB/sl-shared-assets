from pathlib import Path

from ..server import (
    TrackerFileNames as TrackerFileNames,
    ProcessingTracker as ProcessingTracker,
)
from ..data_classes import (
    SessionData as SessionData,
    SessionLock as SessionLock,
    SessionTypes as SessionTypes,
    RunTrainingDescriptor as RunTrainingDescriptor,
    LickTrainingDescriptor as LickTrainingDescriptor,
    WindowCheckingDescriptor as WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor as MesoscopeExperimentDescriptor,
)
from .transfer_tools import (
    delete_directory as delete_directory,
    transfer_directory as transfer_directory,
)
from .packaging_tools import calculate_directory_checksum as calculate_directory_checksum

def acquire_lock(
    session_path: Path, manager_id: int, processed_data_root: Path | None = None, reset_lock: bool = False
) -> None:
    """Acquires the target session's data lock for the specified manager process.

    Calling this function locks the target session's data to make it accessible only for the specified manager process.

    Notes:
        Each time this function is called, the release_lock() function must also be called to release the lock file.

    Args:
        session_path: The path to the session directory to be locked.
        manager_id: The unique identifier of the manager process that acquires the lock.
        reset_lock: Determines whether to reset the lock file before executing the runtime. This allows recovering
            from deadlocked runtimes, but otherwise should not be used to ensure that the lock performs its intended
            function of limiting access to session's data.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.
    """

def release_lock(session_path: Path, manager_id: int, processed_data_root: Path | None = None) -> None:
    """Releases the target session's data lock if it is owned by the specified manager process.

    Calling this function unlocks the session's data, making it possible for other manager processes to acquire the
    lock and work with the session's data. This step has to be performed by every manager process as part of its
    shutdown sequence if the manager called the acquire_lock() function.

    Args:
        session_path: The path to the session directory to be unlocked.
        manager_id: The unique identifier of the manager process that releases the lock.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.
    """

def resolve_checksum(
    session_path: Path,
    manager_id: int,
    processed_data_root: None | Path = None,
    reset_tracker: bool = False,
    regenerate_checksum: bool = False,
) -> None:
    """Verifies the integrity of the session's data by generating the checksum of the raw_data directory and comparing
    it against the checksum stored in the ax_checksum.txt file.

    Primarily, this function is used to verify data integrity after transferring it from the data acquisition system PC
    to the remote server for long-term storage.

    Notes:
        Any session that does not successfully pass checksum verification (or recreation) is automatically excluded
        from all further automatic processing steps.

        Since version 5.0.0, this function also supports recalculating and overwriting the checksum stored inside the
        ax_checksum.txt file. This allows this function to re-checksum session data, which is helpful if the
        experimenter deliberately alters the session's data post-acquisition (for example, to comply with new data
        storage guidelines).

    Args:
        session_path: The path to the session directory to be processed.
        manager_id: The unique identifier of the manager process that manages the runtime.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.
        reset_tracker: Determines whether to reset the tracker file before executing the runtime. This allows
            recovering from deadlocked runtimes, but otherwise should not be used to ensure runtime safety.
        regenerate_checksum: Determines whether to update the checksum stored in the ax_checksum.txt file before
            carrying out the verification. In this case, the verification necessarily succeeds, and the session's
            reference checksum is changed to reflect the current state of the session data.
    """

def prepare_session(
    session_path: Path, manager_id: int, processed_data_root: Path | None, reset_tracker: bool = False
) -> None:
    """Prepares the target session for data processing and dataset integration.

    This function is primarily designed to be used on remote compute servers that use different data volumes for
    storage and processing. Since storage volumes are often slow, the session data needs to be copied to the fast
    volume before executing processing pipelines. Typically, this function is used exactly once during each session's
    life cycle: when it is first transferred to the remote compute server.

    Args:
        session_path: The path to the session directory to be processed.
        manager_id: The unique identifier of the manager process that manages the runtime.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.
        reset_tracker: Determines whether to reset the tracker file before executing the runtime. This allows
            recovering from deadlocked runtimes, but otherwise should not be used to ensure runtime safety.

    Notes:
        This function inverses the result of running the archive_session() function.
    """

def archive_session(
    session_path: Path, manager_id: int, reset_tracker: bool = False, processed_data_root: Path | None = None
) -> None:
    """Prepares the target session for long-term (cold) storage.

    This function is primarily designed to be used on remote compute servers that use different data volumes for
    storage and processing. It should be called for sessions that are no longer frequently processed or accessed to move
    all session data to the (slow) storage volume and free up the fast processing volume for working with other data.
    Typically, this function is used exactly once during each session's life cycle: when the session's project is
    officially concluded.

    Args:
        session_path: The path to the session directory to be processed.
        manager_id: The unique identifier of the manager process that manages the runtime.
        reset_tracker: Determines whether to reset the tracker file before executing the runtime. This allows
            recovering from deadlocked runtimes, but otherwise should not be used to ensure runtime safety.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.

    Notes:
        This function inverses the result of running the prepare_session() function.
    """

def generate_project_manifest(
    raw_project_directory: Path, manager_id: int, processed_data_root: Path | None = None
) -> None:
    """Builds and saves the project manifest .feather file under the specified output directory.

    This function evaluates the input project directory and builds the 'manifest' file for the project. The file
    includes the descriptive information about every session stored inside the input project folder and the state of
    the session's data processing (which processing pipelines have been applied to each session). The file is created
    under the input raw project directory and uses the following name pattern: ProjectName_manifest.feather.

    Notes:
        The manifest file is primarily used to capture and move project state information between machines, typically
        in the context of working with data stored on a remote compute server or cluster.

    Args:
        raw_project_directory: The path to the root project directory used to store raw session data.
        manager_id: The unique identifier of the manager process that manages the runtime.
        processed_data_root: The path to the root directory (volume) used to store processed data for all Sun lab
            projects if it is different from the parent of the 'raw_project_directory'.
    """
