"""This module provides tools for managing the data of any Sun lab project. Tools from this module extend the
functionality of SessionData class via a convenient API that allows working with the data of multiple sessions making
up a given project."""

from pathlib import Path

import polars as pl
from ataraxis_base_utilities import console

from ..data_classes import SessionData, ProcessingTracker
from .packaging_tools import calculate_directory_checksum


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

    # Finds all raw data directories
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
        "raw_data": [],  # Server-side raw_data folder path.
        "processed_data": [],  # Server-side processed_data folder path.
        # Determines whether the session data is complete. Incomplete sessions are excluded from processing.
        "complete": [],
        # Determines whether the session data integrity has been verified upon transfer to storage machine.
        "integrity_verification": [],
        "suite2p_processing": [],  # Determines whether the session has been processed with the single-day s2p pipeline.
        "dataset_formation": [],  # Determines whether the session's data has been integrated into a dataset.
        # Determines whether the session has been processed with the behavior extraction pipeline.
        "behavior_processing": [],
        "video_processing": [],  # Determines whether the session has been processed with the DeepLabCut pipeline.
    }

    # Loops over each session of every animal in the project and extracts session ID information and information
    # about which processing steps have been successfully applied to the session.
    for directory in session_directories:
        # Instantiates the SessionData instance to resolve the paths to all session's data files and locations.
        session_data = SessionData.load(
            session_path=directory, processed_data_root=processed_project_directory, make_processed_data_directory=False
        )

        # Fills the manifest dictionary with data for the processed session:

        # Extracts ID and data path information from the SessionData instance
        manifest["animal"].append(session_data.animal_id)
        manifest["session"].append(session_data.session_name)
        manifest["type"].append(session_data.session_type)
        manifest["raw_data"].append(str(session_data.raw_data.raw_data_path))
        manifest["processed_data"].append(str(session_data.processed_data.processed_data_path))

        # If the session raw_data folder contains the telomere.bin file, marks the session as complete.
        manifest["complete"].append(session_data.raw_data.telomere_path.exists())

        # Data verification status
        tracker = ProcessingTracker(file_path=session_data.raw_data.integrity_verification_tracker_path)
        manifest["integrity_verification"].append(tracker.is_complete)

        # If the session is incomplete or unverified, marks all processing steps as FALSE, as automatic processing is
        # disabled for incomplete sessions. If the session unverified, the case is even more severe, as its data may be
        # corrupted.
        if not manifest["complete"][-1] or not not manifest["verified"][-1]:
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
        "raw_data": pl.String,
        "processed_data": pl.String,
        "type": pl.String,
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
