"""This module provides tools for translating ('ascending') old Tyche data to use the modern data structure used in the
Sun lab. The tools from this module will not work for any other data and also assume that the Tyche data has been
preprocessed with an early version of the Sun lab mesoscope processing pipeline. However, this module can be used as
an example for how to convert other data formats to match use the Sun lab data structure."""

from pathlib import Path
import datetime
import tempfile

import numpy as np
from ataraxis_base_utilities import LogLevel, console
from ataraxis_time.time_helpers import extract_timestamp_from_bytes

from ..data_classes import SessionData, ProjectConfiguration
from .transfer_tools import transfer_directory
from .packaging_tools import calculate_directory_checksum


def _generate_session_name(acquisition_path: Path) -> str:
    """Generates a session name using the last modification time of a zstack.mat or MotionEstimator.me file.

    This worker function uses one of the motion estimation files stored in each Tyche 'acquisition' subfolder to
    generate a modern Sun lab timestamp-based session name. This is used to translate the original Tyche session naming
    pattern into the pattern used by all modern Sun lab projects and pipelines.

    Args:
        acquisition_path: The absolute path to the target acquisition folder. These folders are found under the 'day'
            folders for each animal, e.g.: Tyche-A7/2022_01_03/1.

    Returns:
        The modernized session name.
    """

    # All well-formed sessions are expected to contain both the zstack.mat and the MotionEstimator.me file.
    # We use the last modification time from one of these files to infer when the session was carried out. This allows
    # us to gather the time information, which is missing from the original session naming pattern.
    source: Path
    if acquisition_path.joinpath("zstack.mat").exists():
        source = acquisition_path.joinpath("zstack.mat")
    elif acquisition_path.joinpath("MotionEstimator.me").exists():
        source = acquisition_path.joinpath("MotionEstimator.me")
    else:
        message = (
            f"Unable to find zstack.mat or MotionEstimator.me file in the target acquisition subfolder "
            f"{acquisition_path} of the session {acquisition_path.parent}. Manual intervention is required to ascend "
            f"the target session folder to the latest Sun lab data format."
        )
        console.error(message=message, error=FileNotFoundError)
        raise FileNotFoundError(message)  # Fall-back to appease mypy

    # Gets last modified time (available on all platforms) and converts it to a UTC timestamp object.
    mod_time = source.stat().st_mtime
    mod_datetime = datetime.datetime.fromtimestamp(mod_time)

    # Converts the timestamp to microseconds as uint64, then to an array of 8 uint8 bytes. The array is then reformatted
    # to match the session name pattern used in the modern Sun lab data pipelines.
    timestamp_microseconds = np.uint64(int(mod_datetime.timestamp() * 1_000_000))
    timestamp_bytes = np.array([(timestamp_microseconds >> (8 * i)) & 0xFF for i in range(8)], dtype=np.uint8)
    stamp = extract_timestamp_from_bytes(timestamp_bytes=timestamp_bytes)

    # Returns the generated session name to caller.
    return stamp


def _reorganize_data(session_data: SessionData, source_root: Path) -> bool:
    """Reorganizes and moves the session's data from the source folder in the old Tyche data hierarchy to the raw_data
    folder in the newly created modern hierarchy.

    This worker function is used to physically rearrange the data from the original Tyche data structure to the
    new data structure. It both moves the existing files to their new destinations and renames certain files to match
    the modern naming convention used in the Sun lab.

    Args:
        session_data: The initialized SessionData instance managing the 'ascended' (modernized) session data hierarchy.
        source_root: The absolute path to the old Tyche data hierarchy folder that stores session's data.

    Returns:
        True if the ascension process was successfully completed. False if the process encountered missing data or
        otherwise did not go as expected. When the method returns False, the runtime function requests user intervention
        to finalize the process manually.
    """

    # Resolves expected data targets:

    # These files should be present in all well-formed session data folders. While not all session folders are
    # well-formed, we will likely exclude any non-well-formed folders from processing.
    zstack_path = source_root.joinpath("zstack.mat")
    motion_estimator_path = source_root.joinpath("MotionEstimator.me")
    ops_path = source_root.joinpath("ops.json")
    mesoscope_frames_path = source_root.joinpath("mesoscope_frames")
    ax_checksum_path = source_root.joinpath("ax_checksum.txt")

    # These two file types are present for some, but not all folders. They are not as important as the group of files
    # above though, as, currently, the data stored in these files is not used during processing.
    frame_metadata_path = source_root.joinpath("frame_metadata.npz")
    metadata_path = source_root.joinpath("metadata.json")

    # This tracker is used to mark the session for manual intervention if any expected data is missing from the source
    # session folder. At the end of this function's runtime, it determines whether the function returns True or False
    data_missing = False

    # First, moves the mesoscope TIFF stacks to the newly created session data hierarchy as mesoscope_data subfolder
    if mesoscope_frames_path.exists():
        mesoscope_frames_path.rename(session_data.raw_data.mesoscope_data_path)
    else:
        data_missing = True

    # Then, moves 'loose' mesoscope-related data files to the mesoscope_data folder.
    if zstack_path.exists():
        zstack_path.rename(Path(session_data.raw_data.mesoscope_data_path).joinpath("zstack.mat"))
    else:
        data_missing = True

    if motion_estimator_path.exists():
        motion_estimator_path.rename(Path(session_data.raw_data.mesoscope_data_path).joinpath("MotionEstimator.me"))
    else:
        data_missing = True

    if ops_path.exists():
        ops_path.rename(Path(session_data.raw_data.mesoscope_data_path).joinpath("ops.json"))
    else:
        data_missing = True

    # If variant and invariant metadata files exist, also moves them to the mesoscope data folder and renames the
    # files to use the latest naming convention. Missing any of these files is not considered a user-intervention-worthy
    # situation.
    if frame_metadata_path.exists():
        frame_metadata_path.rename(
            Path(session_data.raw_data.mesoscope_data_path).joinpath("frame_variant_metadata.npz")
        )
    if metadata_path.exists():
        metadata_path.rename(Path(session_data.raw_data.mesoscope_data_path).joinpath("frame_invariant_metadata.json"))

    # Loops over all camera video files (using the .avi extension) and moves them to the camera_data folder.
    videos_found = 0
    for video in source_root.glob("*.avi"):
        videos_found += 1
        video.rename(Path(session_data.raw_data.camera_data_path).joinpath(video.name))
    if videos_found == 0:
        data_missing = True

    # Loops over all behavior log files (old GIMBL format) and moves them to the behavior_data folder.
    logs_found = 0
    for log in source_root.glob("Log Tyche-* ????-??-?? session *.json"):
        logs_found += 1
        log.rename(Path(session_data.raw_data.behavior_data_path).joinpath(log.name))
    if logs_found == 0:
        data_missing = True

    # Removes the checksum file if it exists. Due to file name and location changes, the session data folder has to
    # be re-checksummed after the reorganization anyway, so there is no need to keep the original file.
    ax_checksum_path.unlink(missing_ok=True)

    # Loops over all remaining contents of the directory.
    for path in source_root.glob("*"):
        # At this point, there should be no more subfolders left inside the root directory. If there are more
        # subfolders, this case requires user intervention
        if path.is_dir():
            data_missing = True

        # All non-subfolder files are moved to the root raw_data directory of the newly created session.
        else:
            path.rename(Path(session_data.raw_data.raw_data_path).joinpath(path.name))

    # Session data has been fully reorganized. Depending on whether there was any missing data during processing,
    # returns the boolean flag for whether user intervention is required
    if data_missing:
        return False
    else:
        return True


def ascend_tyche_data(root_directory: Path, output_root_directory: Path, server_root_directory: Path) -> None:
    """Reformats the old Tyche data to use the modern Sun lab layout and metadata files.

    This function is used to convert old Tyche data to the modern data management standard. This is used to make the
    data compatible with the modern Sun lab data workflows.

    Notes:
        This function is statically written to work with the raw Tyche dataset featured in the OSM manuscript:
        https://www.nature.com/articles/s41586-024-08548-w. Additionally, it assumes that the dataset has been
        preprocessed with the early Sun lab mesoscope compression pipeline. The function will not work for any other
        project or data hierarchy.

        As part of its runtime, the function automatically transfers the ascended session data to the BioHPC server.
        Since transferring the data over the network is the bottleneck of this pipeline, it runs in a single-threaded
        mode and is constrained by the communication channel between the local machine and the BioHPC server. Calling
        this function for a large number of sessions will result in a long processing time due to the network data
        transfer.

    Args:
        root_directory: The directory that stores one or more Tyche animal folders. This can be conceptualized as the
            root directory for the Tyche project.
        output_root_directory: The path to the local directory where to generate the converted Tyche project hierarchy.
            Typically, this is the 'root' directory where all other Sun lab projects are stored.
        server_root_directory: The path to the local filesystem-mounted BioHPC server storage directory. Note, this
            directory hs to be mapped to the local filesystem via the SMB or equivalent protocol.
    """
    # Generates a (shared) project configuration file.
    project_configuration = ProjectConfiguration()

    # Generates a temporary directory for NAS and Mesoscope paths. Since Tyche data is already backed up on the NAS and
    # we are not generating new data, these root paths are not needed, but have to be created as part of the pipeline.
    # Redirecting them to local temporary directories allows avoiding extra steps to manually remove these redundant
    # directories after runtime.
    temp_nas_dir = Path(tempfile.mkdtemp(prefix="nas_temp_"))
    temp_mesoscope_dir = Path(tempfile.mkdtemp(prefix="mesoscope_temp_"))

    # Statically defines project name and local root paths
    project_configuration.project_name = "Tyche"
    project_configuration.local_root_directory = output_root_directory
    project_configuration.local_server_directory = server_root_directory
    project_configuration.local_nas_directory = temp_nas_dir
    project_configuration.local_mesoscope_directory = temp_mesoscope_dir

    # Uses nonsensical google sheet IDs. Tyche project did not use Google Sheet processing like our modern projects do.
    project_configuration.water_log_sheet_id = "1xFh9Q2zT7pL3mVkJdR8bN6yXoE4wS5aG0cHu2Kf7D3v"
    project_configuration.surgery_sheet_id = "1xFh9Q2zT7pL3mVkJdR8bN6yXoE4wS5aG0cHu2Kf7D3v"

    # Dumps project configuration into the 'configuration' subfolder of the Tyche project.
    configuration_path = output_root_directory.joinpath("Tyche", "configuration", "project_configuration.yaml")
    project_configuration.save(path=configuration_path)

    # Assumes that root directory stores all animal folders to be processed
    for animal_folder in root_directory.iterdir():
        # Each animal folder is named to include project name and a static animal ID, e.g.: Tyche-A7. This extracts each
        # animal ID.
        animal_name = animal_folder.name.split(sep="-")[1]

        # Under each animal root folder, there are day folders that use YYYY-MM-DD timestamps
        for session_folder in animal_folder.iterdir():
            # Inside each day folder, there are one or more acquisitions (sessions)
            for acquisition_folder in session_folder.iterdir():
                # For each session, we extract the modification time from either (preferentially) zstack.mat or
                # MotionEstimator.me file. Any session without these files is flagged for additional user intervention.
                # This procedure generates timestamp-based session names, analogous to how our modern pipeline does it.
                session_name = _generate_session_name(acquisition_path=acquisition_folder)

                # Uses derived session name and the statically created project configuration file to create the
                # session data hierarchy using the output root. This generates a 'standard' Sun lab directory structure
                # for the Tyche data.
                session_data = SessionData.create(
                    session_name=session_name,
                    animal_id=animal_name,
                    project_configuration=project_configuration,
                    session_type="Experiment",
                    experiment_name=None,  # Has to be none, otherwise the system tries to copy a configuration file.
                )

                # Moves the data from the old hierarchy to the new hierarchy. If the process runs as expected, and
                # fully empties the source acquisition folder, destroys the folder. Otherwise, notifies the user that
                # the runtime did not fully process the session data and requests intervention.
                success = _reorganize_data(session_data, acquisition_folder)
                if not success:
                    message = (
                        f"Encountered issues when reorganizing {animal_name} session {session_name}. "
                        f"User intervention is required to finish data reorganization process for this session."
                    )
                    # noinspection PyTypeChecker
                    console.echo(message=message, level=LogLevel.WARNING)
                else:
                    # If the transfer process was successful, generates a new checksum for the moved data
                    calculate_directory_checksum(directory=Path(session_data.raw_data.raw_data_path))
                    # Next, copies the data to the BioHPC server for further processing
                    transfer_directory(
                        source=Path(session_data.raw_data.raw_data_path),
                        destination=Path(session_data.destinations.server_raw_data_path),
                        verify_integrity=False,
                    )
                    # Finally, removes the now-empty old session data directory.
                    acquisition_folder.rmdir()

            # If the loop above removed all acquisition folders, all data for that day has been successfully converted
            # to use the new session format. Removes the now-empty 'day' folder from the target animal
            if len([folder for folder in session_folder.iterdir()]) == 0:
                session_folder.rmdir()
