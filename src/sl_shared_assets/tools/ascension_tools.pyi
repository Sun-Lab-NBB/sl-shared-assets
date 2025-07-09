from pathlib import Path

from ..data_classes import (
    SessionData as SessionData,
    get_system_configuration_data as get_system_configuration_data,
)
from .transfer_tools import transfer_directory as transfer_directory
from .packaging_tools import calculate_directory_checksum as calculate_directory_checksum

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

def ascend_tyche_data(root_directory: Path) -> None:
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

        Since SessionData can only be created on a PC that has a valid acquisition system config, this function will
        only work on a machine that is part of an active Sun lab acquisition system.

    Args:
        root_directory: The directory that stores one or more Tyche animal folders. This can be conceptualized as the
            root directory for the Tyche project.
    """
