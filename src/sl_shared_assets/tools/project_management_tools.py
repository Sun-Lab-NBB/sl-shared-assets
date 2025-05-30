"""This module provides tools for managing the data of any Sun lab project. Tools from this module extend the
functionality of SessionData class via a convenient API that allows working with the data of multiple sessions making
up a given project."""

from pathlib import Path

import polars as pl
from ataraxis_base_utilities import console

from ..data_classes import SessionData
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
        "complete": [],  # Determines if the session data is complete. Incomplete sessions are excluded from processing.
        "verified": [],  # Determines if the session data integrity has been verified upon transfer to storage machine.
        "single_day_suite2p": [],  # Determines whether the session has been processed with the single-day s2p pipeline.
        "multi_day_suite2p": [],  # Determines whether the session has been processed with the multi-day s2p pipeline.
        "behavior": [],  # Determines whether the session has been processed with the behavior extraction pipeline.
        "dlc": [],  # Determines whether the session has been processed with the DeepLabCut pipeline.
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

        # If the session raw_data folder contains the verified.bin file, marks the session as verified.
        manifest["verified"].append(session_data.raw_data.verified_bin_path.exists())

        # If the session is incomplete or unverified, marks all processing steps as FALSE, as automatic processing is
        # disabled for incomplete sessions. If the session unverified, the case is even more severe, as its data may be
        # corrupted.
        if not manifest["complete"][-1] or not not manifest["verified"][-1]:
            manifest["single_day_suite2p"].append(False)
            manifest["multi_day_suite2p"].append(False)
            manifest["behavior"].append(False)
            manifest["dlc"].append(False)
            continue  # Cycles to the next session

        # If the session processed_data folder contains the single-day suite2p.bin file, marks the single-day suite2p
        # processing step as complete.
        manifest["single_day_suite2p"].append(session_data.processed_data.single_day_suite2p_bin_path.exists())

        # If the session processed_data folder contains the multi-day suite2p.bin file, marks the multi-day suite2p
        # processing step as complete.
        manifest["multi_day_suite2p"].append(session_data.processed_data.multi_day_suite2p_bin_path.exists())

        # If the session processed_data folder contains the behavior.bin file, marks the behavior processing step as
        # complete.
        manifest["behavior"].append(session_data.processed_data.behavior_data_path.exists())

        # If the session processed_data folder contains the dlc.bin file, marks the dlc processing step as
        # complete.
        manifest["dlc"].append(session_data.processed_data.dlc_bin_path.exists())

    # Converts the manifest dictionary to a Polars Dataframe
    schema = {
        "animal": pl.String,
        "session": pl.String,
        "raw_data": pl.String,
        "processed_data": pl.String,
        "type": pl.String,
        "complete": pl.Boolean,
        "verified": pl.Boolean,
        "single_day_suite2p": pl.Boolean,
        "multi_day_suite2p": pl.Boolean,
        "behavior": pl.Boolean,
        "dlc": pl.Boolean,
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

    # Unlinks the verified.bin marker if it exists. The presence or absence of the marker is used as the
    # primary heuristic for determining if the session data passed verification. Unlinking it early helps in the case
    # the verification procedure aborts unexpectedly for any reason.
    session_data.raw_data.verified_bin_path.unlink(missing_ok=True)

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

    # Otherwise, ensures that the session is marked with the verified.bin marker file.
    else:
        session_data.raw_data.verified_bin_path.touch(exist_ok=True)
