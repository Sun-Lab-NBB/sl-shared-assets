from pathlib import Path

from ..data_classes import SessionData as SessionData
from .packaging_tools import calculate_directory_checksum as calculate_directory_checksum

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

def verify_session_checksum(session_path: Path) -> bool:
    """Verifies the integrity of the session's raw data by generating the checksum of the raw_data directory and
    comparing it against the checksum stored in the ax_checksum.txt file.

    Primarily, this function is used to verify data integrity after transferring it from a local PC to the remote
    server for long-term storage. This function is designed to do nothing if the checksum matches and to remove the
    'telomere.bin' marker file if it does not.

    Notes:
        Removing the telomere.bin marker file from session's raw_data folder marks the session as incomplete, excluding
        it from all further automatic processing.

    Args:
        session_path: The path to the session directory to be verified. Note, the input session directory must contain
            the 'raw_data' subdirectory.

    Returns:
        True if the checksum matches, False otherwise.
    """
