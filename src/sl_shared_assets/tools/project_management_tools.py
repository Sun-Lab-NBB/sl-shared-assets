"""This module provides tools for managing the data of any Sun lab project. Tools from this module extend the
functionality of SessionData class via a convenient API that allows working with the data of multiple sessions making
up a given project."""

from pathlib import Path

import polars as pl
from ataraxis_base_utilities import console

from ..data_classes import (
    SessionData,
    ProcessingTracker,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeExperimentDescriptor,
)
from .packaging_tools import calculate_directory_checksum

_valid_session_types = {"lick training", "run training", "mesoscope experiment", "window checking"}


class ProjectManifest:
    def __init__(self, manifest_file: Path):
        """Loads the data from a Sun lab project manifest.feather file and exposes methods for working with the data.

        The manifest file contains the snapshot of the entire managed project, specifying the available animals and
        sessions, as well as their current processing status.

        Args:
            manifest_file: The path to the .feather manifest file from which to load the data.
        """

        # Reads the data from the target manifest file into the class attribute
        self._data: pl.DataFrame = pl.read_ipc(source=manifest_file, use_pyarrow=True)

    def print_data(self) -> None:
        """Print the entire manifest DataFrame with full display options."""
        with pl.Config(
                set_tbl_rows=-1,  # Display all rows (-1 means unlimited)
                set_tbl_cols=-1,  # Display all columns (-1 means unlimited)
                set_tbl_width_chars=200,  # Set table width to 200 characters
                set_tbl_cell_alignment="LEFT",  # Left-align content
                set_fmt_str_lengths=100,  # Allow longer strings to display (default is 32)
        ):
            print(self._data)

    def print_summary(self) -> None:
        """Print a summary view without the notes column for better readability."""
        summary_cols = ["animal", "session", "type", "complete", "integrity_verification",
                        "suite2p_processing", "behavior_processing", "video_processing", "dataset_formation"]

        with pl.Config(
                set_tbl_rows=-1,
                set_tbl_cols=-1,
                set_tbl_width_chars=150,
        ):
            print(self._data.select(summary_cols))

    def print_notes(self, animal_id: str = None) -> None:
        """Print only animal, session, and notes columns for easier reading of experiment notes.

        Args:
            animal_id: Optional animal ID to filter by
        """
        df = self._data.select(["animal", "session", "type", "notes"])

        if animal_id is not None:
            df = df.filter(pl.col("animal") == animal_id)

        with pl.Config(
                set_tbl_rows=-1,
                set_tbl_cols=-1,
                set_tbl_width_chars=300,  # Wider for notes
                set_fmt_str_lengths=200,  # Allow very long strings for notes
        ):
            print(df)

    @property
    def animals(self) -> tuple[str, ...]:
        """Get all unique animal IDs in the manifest.

        Returns:
            Tuple of unique animal ID strings, sorted
        """
        return tuple(self._data.select("animal").unique().sort("animal").to_series().to_list())

    @property
    def sessions(self) -> tuple[str, ...]:
        """Get all session names in the manifest.

        Returns:
            Tuple of all session name strings, sorted
        """
        return tuple(self._data.select("session").sort("session").to_series().to_list())

    def get_sessions_for_animal(self, animal_id: str) -> tuple[str, ...]:
        """Get all sessions for a specific animal.

        Args:
            animal_id: The animal ID to filter by

        Returns:
            Tuple of session names for the specified animal, sorted

        Raises:
            ValueError: If animal_id is not found in the manifest
        """
        if animal_id not in self.animals:
            raise ValueError(f"Animal ID '{animal_id}' not found in manifest. Available animals: {self.animals}")

        sessions = (
            self._data.filter(pl.col("animal") == animal_id).select("session").sort("session").to_series().to_list()
        )

        return tuple(sessions)

    def get_session_info(self, animal_id: str = None, session_name: str = None) -> pl.DataFrame:
        """Get detailed information for sessions based on filters.

        Args:
            animal_id: Optional animal ID to filter by
            session_name: Optional session name to filter by

        Returns:
            Filtered DataFrame with session information
        """
        df = self._data

        if animal_id is not None:
            df = df.filter(pl.col("animal") == animal_id)

        if session_name is not None:
            df = df.filter(pl.col("session") == session_name)

        return df

    def get_complete_sessions(self, animal_id: str = None) -> pl.DataFrame:
        """Get all complete sessions, optionally filtered by animal.

        Args:
            animal_id: Optional animal ID to filter by

        Returns:
            DataFrame containing only complete sessions
        """
        df = self._data.filter(pl.col("complete") == True)

        if animal_id is not None:
            df = df.filter(pl.col("animal") == animal_id)

        return df

    def get_processed_sessions(self, processing_type: str, animal_id: str = None) -> pl.DataFrame:
        """Get sessions that have completed a specific processing pipeline.

        Args:
            processing_type: Type of processing to filter by
                           ('suite2p_processing', 'behavior_processing',
                            'video_processing', 'dataset_formation')
            animal_id: Optional animal ID to filter by

        Returns:
            DataFrame containing sessions with completed processing

        Raises:
            ValueError: If processing_type is not valid
        """
        valid_types = ["suite2p_processing", "behavior_processing", "video_processing", "dataset_formation"]

        if processing_type not in valid_types:
            raise ValueError(f"Invalid processing_type '{processing_type}'. Must be one of: {valid_types}")

        df = self._data.filter(pl.col(processing_type) == True)

        if animal_id is not None:
            df = df.filter(pl.col("animal") == animal_id)

        return df

    def get_session_count_by_animal(self) -> pl.DataFrame:
        """Get count of sessions per animal.

        Returns:
            DataFrame with animal IDs and their session counts
        """
        return self._data.group_by("animal").agg(pl.len().alias("session_count")).sort("animal")

    def get_processing_summary(self) -> pl.DataFrame:
        """Get summary of processing status across all sessions.

        Returns:
            DataFrame with counts and percentages for each processing type
        """
        total_sessions = self._data.height

        summary = []
        processing_columns = [
            "complete",
            "integrity_verification",
            "suite2p_processing",
            "behavior_processing",
            "video_processing",
            "dataset_formation",
        ]

        for col in processing_columns:
            completed = self._data.filter(pl.col(col) is True).height
            percentage = (completed / total_sessions) * 100 if total_sessions > 0 else 0
            summary.append(
                {
                    "processing_type": col,
                    "completed_sessions": completed,
                    "total_sessions": total_sessions,
                    "completion_percentage": round(percentage, 2),
                }
            )

        return pl.DataFrame(summary)


def generate_project_manifest(
    raw_project_directory: Path, output_directory: Path, processed_project_directory: Path | None = None
) -> None:
    """Builds and saves the project manifest .feather file under the specified output directory.

    This function evaluates the input project directory and builds the 'manifest' file for the project. The file
    includes the descriptive information about every session stored inside the input project folder and the state of
    session's data processing (which processing pipelines have been applied to each session). The file will be created
    under the 'output_path' directory and use the following name pattern: {ProjectName}}_manifest.feather.

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

    if not raw_project_directory.exists():
        message = (
            f"Unable to generate the project manifest file for the requested project {raw_project_directory.stem}. The "
            f"specified project directory does not exist."
        )
        console.error(message=message, error=FileNotFoundError)

    # Finds all session directories
    session_directories = [directory.parent for directory in raw_project_directory.rglob("raw_data")]

    if len(session_directories) == 0:
        message = (
            f"Unable to generate the project manifest file for the requested project {raw_project_directory.stem}. The "
            f"project does not contain any raw session data. To generate the manifest file, the project must contain "
            f"at least one valid experiment or training session."
        )
        console.error(message=message, error=FileNotFoundError)

    # Precreates the 'manifest' dictionary structure
    manifest: dict[str, list[str | bool]] = {
        "animal": [],  # Animal IDs.
        "session": [],  # Session names.
        "type": [],  # Type of the session (e.g., Experiment, Training, etc.).
        "notes": [],  # The experimenter notes about the session.
        # Determines whether the session data is complete (ran for the intended duration and has all expected data).
        "complete": [],
        # Determines whether the session data integrity has been verified upon transfer to storage machine.
        "integrity_verification": [],
        "suite2p_processing": [],  # Determines whether the session has been processed with the single-day s2p pipeline.
        # Determines whether the session has been processed with the behavior extraction pipeline.
        "behavior_processing": [],
        "video_processing": [],  # Determines whether the session has been processed with the DeepLabCut pipeline.
        "dataset_formation": [],  # Determines whether the session's data has been integrated into a dataset.
    }

    # Loops over each session of every animal in the project and extracts session ID information and information
    # about which processing steps have been successfully applied to the session.
    for directory in session_directories:

        # Skips processing directories without files (sessions with empty raw-data directories)
        if len([file for file in directory.joinpath("raw_data").glob("*")]) == 0:
            continue

        # Instantiates the SessionData instance to resolve the paths to all session's data files and locations.
        session_data = SessionData.load(
            session_path=directory,
            processed_data_root=processed_project_directory,
            make_processed_data_directory=False,
        )

        # Fills the manifest dictionary with data for the processed session:

        # Extracts ID and data path information from the SessionData instance
        manifest["animal"].append(session_data.animal_id)
        manifest["session"].append(session_data.session_name)
        manifest["type"].append(session_data.session_type)

        # Depending on the session type, instantiates the appropriate descriptor instance and uses it to read the
        # experimenter notes
        if session_data.session_type == "lick training":
            descriptor: LickTrainingDescriptor = LickTrainingDescriptor.from_yaml(  # type: ignore
                file_path=session_data.raw_data.session_descriptor_path
            )
            manifest["notes"].append(descriptor.experimenter_notes)
        elif session_data.session_type == "run training":
            descriptor: RunTrainingDescriptor = RunTrainingDescriptor.from_yaml(  # type: ignore
                file_path=session_data.raw_data.session_descriptor_path
            )
            manifest["notes"].append(descriptor.experimenter_notes)
        elif session_data.session_type == "mesoscope experiment":
            descriptor: MesoscopeExperimentDescriptor = MesoscopeExperimentDescriptor.from_yaml(  # type: ignore
                file_path=session_data.raw_data.session_descriptor_path
            )
            manifest["notes"].append(descriptor.experimenter_notes)
        elif session_data.session_type == "window checking":
            manifest["notes"].append("N/A")

        # If the session raw_data folder contains the telomere.bin file, marks the session as complete.
        manifest["complete"].append(session_data.raw_data.telomere_path.exists())

        # Data verification status
        tracker = ProcessingTracker(file_path=session_data.raw_data.integrity_verification_tracker_path)
        manifest["integrity_verification"].append(tracker.is_complete)

        # If the session is incomplete or unverified, marks all processing steps as FALSE, as automatic processing is
        # disabled for incomplete sessions. If the session unverified, the case is even more severe, as its data may be
        # corrupted.
        if not manifest["complete"][-1] or not not manifest["integrity_verification"][-1]:
            manifest["suite2p_processing"].append(False)
            manifest["dataset_formation"].append(False)
            manifest["behavior_processing"].append(False)
            manifest["video_processing"].append(False)
            continue  # Cycles to the next session

        # Suite2p (single-day) status
        tracker = ProcessingTracker(file_path=session_data.processed_data.suite2p_processing_tracker_path)
        manifest["suite2p_processing"].append(tracker.is_complete)

        # Dataset formation (integration) status. Tracks whether the session has been added to any dataset(s).
        tracker = ProcessingTracker(file_path=session_data.processed_data.dataset_formation_tracker_path)
        manifest["dataset_formation"].append(tracker.is_complete)

        # Dataset formation (integration) status. Tracks whether the session has been added to any dataset(s).
        tracker = ProcessingTracker(file_path=session_data.processed_data.behavior_processing_tracker_path)
        manifest["behavior_processing"].append(tracker.is_complete)

        # DeepLabCut (video) processing status.
        tracker = ProcessingTracker(file_path=session_data.processed_data.behavior_processing_tracker_path)
        manifest["video_processing"].append(tracker.is_complete)

    # Converts the manifest dictionary to a Polars Dataframe
    schema = {
        "animal": pl.String,
        "session": pl.String,
        "type": pl.String,
        "notes": pl.String,
        "complete": pl.Boolean,
        "integrity_verification": pl.Boolean,
        "suite2p_processing": pl.Boolean,
        "dataset_formation": pl.Boolean,
        "behavior_processing": pl.Boolean,
        "video_processing": pl.Boolean,
    }
    df = pl.DataFrame(manifest, schema=schema)

    # Sorts the DataFrame by animal and then session. Since we assign animal IDs sequentially and 'name' sessions based
    # on acquisition timestamps, the sort order is chronological.
    sorted_df = df.sort(["animal", "session"])

    # Saves the generated manifest to the project-specific manifest .feather file for further processing.
    sorted_df.write_ipc(
        file=output_directory.joinpath(f"{raw_project_directory.stem}_manifest.feather"), compression="lz4"
    )


def verify_session_checksum(
    session_path: Path, create_processed_data_directory: bool = True, processed_data_root: None | Path = None
) -> None:
    """Verifies the integrity of the session's raw data by generating the checksum of the raw_data directory and
    comparing it against the checksum stored in the ax_checksum.txt file.

    Primarily, this function is used to verify data integrity after transferring it from a local PC to the remote
    server for long-term storage. This function is designed to create the 'verified.bin' marker file if the checksum
    matches and to remove the 'telomere.bin' and 'verified.bin' marker files if it does not.

    Notes:
        Removing the telomere.bin marker file from session's raw_data folder marks the session as incomplete, excluding
        it from all further automatic processing.

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

    # Loads session data layout. If configured to do so, also creates the processed data hierarchy
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
        make_processed_data_directory=create_processed_data_directory,
    )

    # Initializes the ProcessingTracker instance for the verification tracker file
    tracker = ProcessingTracker(file_path=session_data.raw_data.integrity_verification_tracker_path)

    # Updates the tracker data to communicate that the verification process has started. This automatically clears
    # the previous 'completed' status.
    tracker.start()

    # Try starts here to allow for proper error-driven 'start' terminations of the tracker cannot acquire the lock for
    # a long time, or if another runtime is already underway.
    try:
        # Re-calculates the checksum for the raw_data directory
        calculated_checksum = calculate_directory_checksum(
            directory=session_data.raw_data.raw_data_path, batch=False, save_checksum=False
        )

        # Loads the checksum stored inside the ax_checksum.txt file
        with open(session_data.raw_data.checksum_path, "r") as f:
            stored_checksum = f.read().strip()

        # If the two checksums do not match, this likely indicates data corruption.
        if stored_checksum != calculated_checksum:
            # If the telomere.bin file exists, removes this file. This automatically marks the session as incomplete for
            # all other Sun lab runtimes.
            session_data.raw_data.telomere_path.unlink(missing_ok=True)

        else:
            # Sets the tracker to indicate that the verification runtime completed successfully.
            tracker.stop()

    finally:
        # If the code reaches this section while the tracker indicates that the processing is still running,
        # this means that the verification runtime encountered an error. Configures the tracker to indicate that this
        # runtime finished with an error to prevent deadlocking the runtime.
        if tracker.is_running:
            tracker.error()

