import polars as pl
from pathlib import Path
from natsort import natsorted
from ..data_classes import SessionData


def build_project_manifest(raw_project_directory: Path, processed_project_directory: Path | None, output_file: Path) -> None:

    # Finds all raw data directories
    session_directories = [directory.parent for directory in raw_project_directory.rglob('raw_data')]

    # Precreates the 'manifest' dictionary structure
    manifest = {
        "animal": [],  # Animal IDs.
        "session": [],  # Session names.
        "type": [],  # Type of the session (e.g., Experiment, Training, etc.).
        "raw_data": [],  # Server-side raw_data folder path.
        "processed_data": [],  # Server-side processed_data folder path.
        "complete": [],  # Determines if the session data is complete. Incomplete sessions are excluded from processing.
        "suite2p": [],  # Determines whether the session has been processed with the single-day suite2p pipeline.
        "behavior": [],  # Determines whether the session has been processed with the behavior extraction pipeline.
        "dlc": []  # Determines whether the session has been processed with the DeepLabCut pipeline.
    }

    # Loops over each session of every animal in the project and extracts session ID information and information
    # about which processing steps have been successfully applied to the session.
    for directory in session_directories:

        # Instantiates the SessionData instance to resolve the paths to all session's data files and locations.
        session_data = SessionData.load(
            session_path=directory,
            processed_data_root=processed_project_directory,
            make_processed_data_directory=False
        )

        # Fills the manifest dictionary with data for the processed session:

        # Extracts ID and data path information from the SessionData instance
        manifest["animal"].append(session_data.animal_id)
        manifest["session"].append(session_data.session_name)
        manifest["type"].append(session_data.session_type)
        manifest["raw_data"].append(session_data.raw_data.raw_data_path)
        manifest["processed_data"].append(session_data.processed_data.processed_data_path)

        # If the session raw_data folder contains the telomere.bin file, marks the session as complete. Otherwise,
        # marks it as incomplete.
        manifest["complete"].append(session_data.raw_data.telomere_path.exists())

        # If the session processed_data folder contains the suite2p.bin file, marks the suite2p processing step as
        # complete. Otherwise, marks the suite2p processing step as incomplete.
        manifest["suite2p"].append(session_data.processed_data.suite2p_bin_path.exists())

        # If the session processed_data folder contains the behavior.bin file, marks the behavior processing step as
        # complete. Otherwise, marks the behavior processing step as incomplete.
        manifest["behavior"].append(session_data.processed_data.behavior_data_path.exists())

        # If the session processed_data folder contains the dlc.bin file, marks the dlc processing step as
        # complete. Otherwise, marks the dlc processing step as incomplete.
        manifest["dlc"].append(session_data.processed_data.dlc_bin_path.exists())

    # Converts the manifest dictionary to a Polars Dataframe
    schema = {
        "animal": pl.String,
        "session": pl.String,
        "raw_data": pl.String,
        "processed_data": pl.String,
        "type": pl.String,
        "complete": pl.Boolean,
        "suite2p": pl.Boolean,
        "behavior": pl.Boolean,
        "dlc": pl.Boolean
    }
    df = pl.DataFrame(manifest, schema=schema)

    # Sorts the DataFrame by animal and then session. Since we assign animal IDs sequentially and 'name' sessions based
    # on acquisition timestamps, the sort order is chronological.
    sorted_df = df.sort(["animal", "session"])

    # Saves the generated manifest to the specified 'feather' file for further processing.
    sorted_df.write_ipc(
        file=output_file,
        compression="lz4"
    )


def verify_checksum(session_data: SessionData) -> bool:
    """
    Verifies that the stored checksum file for the session matches the calculated checksum.

    Args:
        session_directory: The absolute path to the session directory.
        session_data: The SessionData instance that has already been loaded.

    Returns:
        True if the stored checksum file matches the calculated checksum.
        False if a mismatch is found.
    """
    raw_data_dir = session_data.raw_data.raw_data_path
    checksum_file = raw_data_dir / "ax_checksum.txt"

    calculated_checksum = packaging_tools.calculate_directory_checksum(
        directory=raw_data_dir, batch=False, save_checksum=False
    )

    with open(checksum_file, "r") as f:
        stored_checksum = f.read().strip()

    if stored_checksum != calculated_checksum:
        message = (
            "Calculated checksum and ax_checksum.txt do not match.\n"
            f"Stored checksum: {stored_checksum}\n"
            f"Calculated checksum: {calculated_checksum}"
        )
        console.error(message=message, error=ValueError)
        return False

    return True


def sort_text_files(root_folder: Path, working_directory: Path):
    """
    Searches for and loads all 'session_data.yaml' files and organizes each session by project name.

    This function generates a .txt file for each unique project name, which contains the paths
    to all associated sessions.

    Args:
        root_folder: The absolute path to the root project directory on the BioHPC server.
        working_directory: The path to the directory where project-specific .txt files containing
                           all session paths for the same project are written to.
    """
    raw_data_paths = [folder for folder in root_folder.rglob("session_data.yaml")]

    projects_dict = {}

    for session_file in raw_data_paths:
        timestamp_path = session_file.parent.parent

        session_data = SessionData.load(
            session_path=timestamp_path,
            on_server=False,
        )
        project_name = session_data.project_name

        if project_name not in projects_dict:
            projects_dict[project_name] = []

        projects_dict[project_name].append(str(timestamp_path))

    for project_name, session_paths in projects_dict.items():
        output_file = working_directory / f"{project_name}.txt"
        with open(output_file, "w") as f:
            f.write("\n".join(session_paths) + "\n")