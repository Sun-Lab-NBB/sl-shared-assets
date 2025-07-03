from pathlib import Path

import polars as pl
from _typeshed import Incomplete

from ..data_classes import (
    SessionData as SessionData,
    ProcessingTracker as ProcessingTracker,
    RunTrainingDescriptor as RunTrainingDescriptor,
    LickTrainingDescriptor as LickTrainingDescriptor,
    MesoscopeExperimentDescriptor as MesoscopeExperimentDescriptor,
)
from .packaging_tools import calculate_directory_checksum as calculate_directory_checksum

_valid_session_types: Incomplete

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
    @property
    def sessions(self) -> tuple[str, ...]:
        """Returns all session IDs stored inside the manifest file.

        This provides a tuple of all sessions, independent of the participating animal, that were recorded as part
        of the target project.
        """
    def get_sessions_for_animal(
        self,
        animal: str | int,
        exclude_incomplete: bool = True,
        dataset_ready_only: bool = False,
        not_dataset_ready_only: bool = False,
    ) -> tuple[str, ...]:
        """Returns all session IDs for the target animal.

        This provides a tuple of all sessions performed by the target animal as part of the target project.

        Args:
            animal: The ID of the animal for which to get the session data.
            exclude_incomplete: Determines whether to exclude sessions not marked as 'complete' from the output
                list.
            dataset_ready_only: Determines whether to exclude sessions not marked as 'dataset' integration ready from
                the output list. Enabling this option only shows sessions that can be integrated into a dataset.
            not_dataset_ready_only: The opposite of 'dataset_ready_only'. Determines whether to exclude sessions marked
                as 'dataset' integration ready from the output list. Note, when both this and 'dataset_ready_only' are
                enabled, the 'dataset_ready_only' option takes precedence.

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
            A Polars DataFrame with the following columns: 'animal', 'date', 'notes', 'session', 'type', 'complete',
            'intensity_verification', 'suite2p', 'behavior', 'video',
            'dataset'.
        """

def generate_project_manifest(
    raw_project_directory: Path, output_directory: Path, processed_project_directory: Path | None = None
) -> None:
    """Builds and saves the project manifest .feather file under the specified output directory.

    This function evaluates the input project directory and builds the 'manifest' file for the project. The file
    includes the descriptive information about every session stored inside the input project folder and the state of
    the session's data processing (which processing pipelines have been applied to each session). The file will be
    created under the 'output_path' directory and use the following name pattern: {ProjectName}}_manifest.feather.

    Notes:
        The manifest file is primarily used to capture and move project state information between machines, typically
        in the context of working with data stored on a remote compute server or cluster. However, it can also be used
        on a local machine, since an up-to-date manifest file is required to run most data processing pipelines in the
        lab regardless of the runtime context.

    Args:
        raw_project_directory: The path to the root project directory used to store raw session data.
        output_directory: The path to the directory where to save the generated manifest file.
        processed_project_directory: The path to the root project directory used to store processed session data if it
            is different from the 'raw_project_directory'. Typically, this would be the case on remote compute server(s)
            and not on local machines.
    """

def verify_session_checksum(
    session_path: Path, create_processed_data_directory: bool = True, processed_data_root: None | Path = None
) -> None:
    """Verifies the integrity of the session's raw data by generating the checksum of the raw_data directory and
    comparing it against the checksum stored in the ax_checksum.txt file.

    Primarily, this function is used to verify data integrity after transferring it from a local PC to the remote
    server for long-term storage. This function is designed to create the 'verified.bin' marker file if the checksum
    matches and to remove the 'telomere.bin' and 'verified.bin' marker files if it does not.

    Notes:
        Removing the telomere.bin marker file from the session's raw_data folder marks the session as incomplete,
        excluding it from all further automatic processing.

        This function is also used to create the processed data hierarchy on the BioHPC server, when it is called as
        part of the data preprocessing runtime performed by a data acquisition system.

    Args:
        session_path: The path to the session directory to be verified. Note, the input session directory must contain
            the 'raw_data' subdirectory.
        create_processed_data_directory: Determines whether to create the processed data hierarchy during runtime.
        processed_data_root: The root directory where to store the processed data hierarchy. This path has to point to
            the root directory where to store the processed data from all projects, and it will be automatically
            modified to include the project name, the animal name, and the session ID.
    """

def resolve_p53_marker(
    session_path: Path,
    create_processed_data_directory: bool = True,
    processed_data_root: None | Path = None,
    remove: bool = False,
) -> None:
    """Depending on configuration, either creates or removes the p53.bin marker file for the target session.

    The marker file statically determines whether the session can be targeted by data processing or dataset formation
    pipelines.

    Notes:
        Since dataset integration relies on data processing outputs, it is essential to prevent processing pipelines
        from altering the data while it is integrated into a dataset. The p53.bin marker solves this issue by ensuring
        that only one type of runtimes (processing or dataset integration) is allowed to work with the session.

        For the p53.bin marker to be created, the session must currently not undergo any processing and must be
        successfully processed with the minimal set of pipelines for its session type. Removing the p53.bin marker does
        not have any dependencies and will be executed even if the session is currently undergoing dataset integration.
        Due to this limitation, it is only possible to call this function with the 'remove' flag manually (via the
        dedicated CLI).

    Args:
        session_path: The path to the session directory for which the p53.bin marker needs to be resolved. Note, the
            input session directory must contain the 'raw_data' subdirectory.
        create_processed_data_directory: Determines whether to create the processed data hierarchy during runtime.
        processed_data_root: The root directory where to store the processed data hierarchy. This path has to point to
            the root directory where to store the processed data from all projects, and it will be automatically
            modified to include the project name, the animal name, and the session ID.
        remove: Determines whether this function is called to create or remove the p53.bin marker.
    """
