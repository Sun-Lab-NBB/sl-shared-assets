from pathlib import Path

import polars as pl

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
            carrying out the verification. In this case, the verification necessarily succeeds and the session's
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
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.
        reset_tracker: Determines whether to reset the tracker file before executing the runtime. This allows
            recovering from deadlocked runtimes, but otherwise should not be used to ensure runtime safety.

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

class ProjectManifest:
    """Wraps the contents of a Sun lab project manifest .feather file and exposes methods for visualizing and
    working with the data stored inside the file.

    This class functions as a high-level API for working with Sun lab projects. It is used both to visualize the
    current state of various projects and during automated data processing to determine which processing steps to
    apply to different sessions.

    Args:
        manifest_file: The path to the .feather manifest file that stores the target project's state data.

    Attributes:
        _data: Stores the manifest data as a Polars DataFrame.
        _animal_string: Determines whether animal IDs are stored as strings or unsigned integers.
    """

    _data: pl.DataFrame
    _animal_string: bool
    def __init__(self, manifest_file: Path) -> None: ...
    def print_data(self) -> None:
        """Prints the entire contents of the manifest file to the terminal."""
    def print_summary(self, animal: str | int | None = None) -> None:
        """Prints a summary view of the manifest file to the terminal, excluding the 'experimenter notes' data for
        each session.

        This data view is optimized for tracking which processing steps have been applied to each session inside the
        project.

        Args:
            animal: The ID of the animal for which to display the data. If an ID is provided, this method will only
                display the data for that animal. Otherwise, it will display the data for all animals.
        """
    def print_notes(self, animal: str | int | None = None) -> None:
        """Prints only animal, session, and notes data from the manifest file.

        This data view is optimized for experimenters to check what sessions have been recorded for each animal in the
        project and refresh their memory on the outcomes of each session using experimenter notes.

        Args:
            animal: The ID of the animal for which to display the data. If an ID is provided, this method will only
                display the data for that animal. Otherwise, it will display the data for all animals.
        """
    @property
    def animals(self) -> tuple[str, ...]:
        """Returns all unique animal IDs stored inside the manifest file.

        This provides a tuple of all animal IDs participating in the target project.
        """
    def _get_filtered_sessions(
        self, animal: str | int | None = None, exclude_incomplete: bool = True
    ) -> tuple[str, ...]:
        """This worker method is used to get a list of sessions with optional filtering.

        User-facing methods call this worker under-the-hood to fetch the filtered tuple of sessions.

        Args:
            animal: An optional animal ID to filter the sessions. If set to None, the method returns sessions for all
                animals.
            exclude_incomplete: Determines whether to exclude sessions not marked as 'complete' from the output
                list.

        Returns:
            The tuple of session IDs matching the filter criteria.

        Raises:
            ValueError: If the specified animal is not found in the manifest file.
        """
    @property
    def sessions(self) -> tuple[str, ...]:
        """Returns all session IDs stored inside the manifest file.

        This property provides a tuple of all sessions, independent of the participating animal, that were recorded as
        part of the target project. Use the get_sessions() method to get the list of session tuples with filtering.
        """
    def get_sessions(self, animal: str | int | None = None, exclude_incomplete: bool = True) -> tuple[str, ...]:
        """Returns requested session IDs based on selected filtering criteria.

        This method provides a tuple of sessions based on the specified filters. If no animal is specified, returns
        sessions for all animals in the project.

        Args:
            animal: An optional animal ID to filter the sessions. If set to None, the method returns sessions for all
                animals.
            exclude_incomplete: Determines whether to exclude sessions not marked as 'complete' from the output
                list.

        Returns:
            The tuple of session IDs matching the filter criteria.

        Raises:
            ValueError: If the specified animal is not found in the manifest file.
        """
    def get_session_info(self, session: str) -> pl.DataFrame:
        """Returns a Polars DataFrame that stores detailed information for the specified session.

        Since session IDs are unique, it is expected that filtering by session ID is enough to get the requested
        information.

        Args:
            session: The ID of the session for which to retrieve the data.

        Returns:
            A Polars DataFrame with the following columns: 'animal', 'date', 'notes', 'session', 'type', 'system',
            'complete', 'integrity', 'suite2p', 'behavior', 'video', 'archived'.
        """
