"""This module provides tools for managing the data of any Sun lab project. Tools from this module extend the
functionality of SessionData class via a convenient API that allows working with the data of multiple sessions making
up a given project."""

from pathlib import Path
from datetime import datetime

import pytz
import polars as pl
from filelock import FileLock
from ataraxis_base_utilities import LogLevel, console

from ..server import TrackerFileNames, ProcessingTracker
from ..data_classes import (
    SessionData,
    SessionTypes,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
)
from .transfer_tools import delete_directory, transfer_directory
from .packaging_tools import calculate_directory_checksum


def generate_project_manifest(raw_project_directory: Path, processed_data_root: Path | None = None) -> None:
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
        processed_data_root: The path to the root directory (volume) used to store processed data for all Sun lab
            projects if it is different from the parent of the 'raw_project_directory'.
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
    manifest: dict[str, list[str | bool | datetime | int]] = {
        "animal": [],  # Animal IDs.
        "session": [],  # Session names.
        "date": [],  # Session names stored as timezone-aware date-time objects in EST.
        "type": [],  # Type of the session (e.g., mesoscope experiment, run training, etc.).
        "system": [],  # Acquisition system used to acquire the session (e.g. mesoscope-vr, etc.).
        "notes": [],  # The experimenter notes about the session.
        # Determines whether the session data is complete (ran for the intended duration and has all expected data).
        "complete": [],
        # Determines whether the session data integrity has been verified upon transfer to a storage machine.
        "integrity": [],
        # Determines whether the session's data has been prepared for data processing.
        "prepared": [],
        # Determines whether the session's data has been archived for long-term storage.
        "archived": [],
        "suite2p": [],  # Determines whether the session has been processed with the single-day s2p pipeline.
        # Determines whether the session has been processed with the behavior extraction pipeline.
        "behavior": [],
        "video": [],  # Determines whether the session has been processed with the DeepLabCut pipeline.
        "dataset": [],  # Determines whether the session's data is ready to be integrated into a dataset.
    }

    # Resolves the path to the manifest .feather file to be created and the .lock file for the generated manifest
    manifest_path = raw_project_directory.joinpath(f"{raw_project_directory.stem}_manifest.feather")
    manifest_lock = manifest_path.with_suffix(manifest_path.suffix + ".lock")

    # Acquires the lock
    lock = FileLock(str(manifest_lock))
    with lock.acquire(timeout=20.0):
        # Loops over each session of every animal in the project and extracts session ID information and information
        # about which processing steps have been successfully applied to the session.
        for directory in session_directories:
            # Skips processing directories without files (sessions with empty raw-data directories)
            if len([file for file in directory.joinpath("raw_data").glob("*")]) == 0:
                continue

            # Instantiates the SessionData instance to resolve the paths to all session's data files and locations.
            session_data = SessionData.load(
                session_path=directory,
                processed_data_root=processed_data_root,
            )

            # Fills the manifest dictionary with data for the processed session:

            # Extracts ID and data path information from the SessionData instance
            manifest["animal"].append(session_data.animal_id)
            manifest["session"].append(session_data.session_name)
            manifest["type"].append(session_data.session_type)
            manifest["system"].append(session_data.acquisition_system)

            # Parses session name into the date-time object to simplify working with date-time data in the future
            date_time_components = session_data.session_name.split("-")
            date_time = datetime(
                year=int(date_time_components[0]),
                month=int(date_time_components[1]),
                day=int(date_time_components[2]),
                hour=int(date_time_components[3]),
                minute=int(date_time_components[4]),
                second=int(date_time_components[5]),
                microsecond=int(date_time_components[6]),
                tzinfo=pytz.UTC,
            )

            # Converts from UTC to EST / EDT for user convenience
            eastern = pytz.timezone("America/New_York")
            date_time = date_time.astimezone(eastern)
            manifest["date"].append(date_time)

            # Depending on the session type, instantiates the appropriate descriptor instance and uses it to read the
            # experimenter notes
            if session_data.session_type == SessionTypes.LICK_TRAINING:
                descriptor: LickTrainingDescriptor = LickTrainingDescriptor.from_yaml(  # type: ignore
                    file_path=session_data.raw_data.session_descriptor_path
                )
                manifest["notes"].append(descriptor.experimenter_notes)
            elif session_data.session_type == SessionTypes.RUN_TRAINING:
                descriptor: RunTrainingDescriptor = RunTrainingDescriptor.from_yaml(  # type: ignore
                    file_path=session_data.raw_data.session_descriptor_path
                )
                manifest["notes"].append(descriptor.experimenter_notes)
            elif session_data.session_type == SessionTypes.MESOSCOPE_EXPERIMENT:
                descriptor: MesoscopeExperimentDescriptor = MesoscopeExperimentDescriptor.from_yaml(  # type: ignore
                    file_path=session_data.raw_data.session_descriptor_path
                )
                manifest["notes"].append(descriptor.experimenter_notes)
            elif session_data.session_type == SessionTypes.WINDOW_CHECKING:
                # sl-experiment version 3.0.0 added session descriptors to Window Checking runtimes. Since the file
                # does not exist in prior versions, this section is written to statically handle the discrepancy.
                try:
                    descriptor: WindowCheckingDescriptor = WindowCheckingDescriptor.from_yaml(  # type: ignore
                        file_path=session_data.raw_data.session_descriptor_path
                    )
                    manifest["notes"].append(descriptor.experimenter_notes)
                except Exception:
                    manifest["notes"].append("N/A")
            else:
                manifest["notes"].append("N/A")

            # If the session raw_data folder contains the telomere.bin file, marks the session as complete.
            manifest["complete"].append(session_data.raw_data.telomere_path.exists())

            # Data verification status
            tracker = ProcessingTracker(
                file_path=session_data.raw_data.raw_data_path.joinpath(TrackerFileNames.INTEGRITY)
            )
            manifest["integrity"].append(tracker.is_complete)

            # If the session is incomplete or unverified, marks all processing steps as FALSE, as automatic processing
            # is disabled for incomplete sessions. If the session is unverified, the case is even more severe, as its
            # data may be corrupted.
            if not manifest["complete"][-1] or not manifest["integrity"][-1]:
                manifest["suite2p"].append(False)
                manifest["dataset"].append(False)
                manifest["behavior"].append(False)
                manifest["video"].append(False)
                manifest["prepared"].append(False)
                manifest["archived"].append(False)
                continue  # Cycles to the next session

            # Suite2p (single-day) processing status.
            tracker = ProcessingTracker(
                file_path=session_data.processed_data.processed_data_path.joinpath(TrackerFileNames.SUITE2P)
            )
            manifest["suite2p"].append(tracker.is_complete)

            # Behavior data processing status.
            tracker = ProcessingTracker(
                file_path=session_data.processed_data.processed_data_path.joinpath(TrackerFileNames.BEHAVIOR)
            )
            manifest["behavior"].append(tracker.is_complete)

            # DeepLabCut (video) processing status.
            tracker = ProcessingTracker(
                file_path=session_data.processed_data.processed_data_path.joinpath(TrackerFileNames.VIDEO)
            )
            manifest["video"].append(tracker.is_complete)

            # Preparation and Archiving status
            tracker = ProcessingTracker(
                file_path=session_data.raw_data.raw_data_path.joinpath(TrackerFileNames.PREPARATION)
            )
            manifest["prepared"].append(tracker.is_complete)
            tracker = ProcessingTracker(
                file_path=session_data.raw_data.raw_data_path.joinpath(TrackerFileNames.ARCHIVE)
            )
            manifest["archived"].append(tracker.is_complete)

            # Tracks whether the session's data is currently in the processing or dataset integration mode.
            manifest["dataset"].append(session_data.processed_data.p53_path.exists())

        # If all animal IDs are integer-convertible, stores them as numbers to promote proper sorting. Otherwise, stores
        # them as strings. The latter options are primarily kept for compatibility with Tyche data
        animal_type: type[pl.UInt64] | type[pl.String]
        if all([str(animal).isdigit() for animal in manifest["animal"]]):
            # Converts all strings to integers
            manifest["animal"] = [int(animal) for animal in manifest["animal"]]  # type: ignore
            animal_type = pl.UInt64  # Uint64 for future proofing
        else:
            animal_type = pl.String

        # Converts the manifest dictionary to a Polars Dataframe.
        schema = {
            "animal": animal_type,
            "date": pl.Datetime,
            "session": pl.String,
            "type": pl.String,
            "system": pl.String,
            "notes": pl.String,
            "complete": pl.UInt8,
            "integrity": pl.UInt8,
            "prepared": pl.UInt8,
            "archived": pl.UInt8,
            "suite2p": pl.UInt8,
            "dataset": pl.UInt8,
            "behavior": pl.UInt8,
            "video": pl.UInt8,
        }
        df = pl.DataFrame(manifest, schema=schema, strict=False)

        # Sorts the DataFrame by animal and then session. Since we assign animal IDs sequentially and 'name' sessions
        # based on acquisition timestamps, the sort order is chronological.
        sorted_df = df.sort(["animal", "session"])

        # Saves the generated manifest to the project-specific manifest .feather file for further processing.
        sorted_df.write_ipc(file=manifest_path, compression="lz4")


def resolve_checksum(
    session_path: Path,
    manager_id: int,
    regenerate_checksum: bool = False,
    processed_data_root: None | Path = None,
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
        session_path: The path to the session directory to be verified or re-checksummed.
        manager_id: The unique identifier of the manager process that manages the integrity verification runtime.
        regenerate_checksum: Determines whether to update the checksum stored in the ax_checksum.txt file before
            carrying out the verification. In this case, the verification necessarily succeeds and the session's
            reference checksum is changed to reflect the current state of the session data.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the session data root.
    """

    # Loads session data layout. If configured to do so, also creates the processed data hierarchy
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )

    # Initializes the ProcessingTracker instance for the verification tracker file
    tracker = ProcessingTracker(file_path=session_data.raw_data.raw_data_path.joinpath(TrackerFileNames.INTEGRITY))

    # Updates the tracker data to communicate that the verification process has started. This automatically clears
    # the previous 'completed' status.
    tracker.start(manager_id=manager_id)
    try:
        console.echo(
            message=f"Resolving the data integrity checksum for session '{session_data.session_name}'...",
            level=LogLevel.INFO,
        )

        # Regenerates the checksum for the raw_data directory. Note, if the 'regenerate_checksum' flag is True, this
        # guarantees that the check below succeeds as the function replaces the checksum in the ax_checksum.txt file
        # with the newly calculated value.
        calculated_checksum = calculate_directory_checksum(
            directory=session_data.raw_data.raw_data_path, batch=False, save_checksum=regenerate_checksum
        )

        # Loads the checksum stored inside the ax_checksum.txt file
        with session_data.raw_data.checksum_path.open() as f:
            stored_checksum = f.read().strip()

        # If the two checksums do not match, this likely indicates data corruption.
        if stored_checksum != calculated_checksum:
            tracker.error(manager_id=manager_id)
            console.echo(
                message=f"Session '{session_data.session_name}' raw data integrity: Compromised.", level=LogLevel.ERROR
            )

        else:
            # Sets the tracker to indicate that the verification runtime completed successfully.
            console.echo(
                message=f"Session '{session_data.session_name}' raw data integrity: Verified.", level=LogLevel.SUCCESS
            )
            tracker.stop(manager_id=manager_id)

    finally:
        # If the code reaches this section while the tracker indicates that the processing is still running,
        # this means that the verification runtime encountered an error.
        if tracker.is_running:
            tracker.error(manager_id=manager_id)

        # Updates or generates the manifest file inside the root raw data project directory
        generate_project_manifest(
            raw_project_directory=session_data.raw_data.root_path.joinpath(session_data.project_name),
            processed_data_root=processed_data_root,
        )


def reset_trackers(
    session_path: Path,
    trackers: tuple[TrackerFileNames, ...] | None = None,
    processed_data_root: None | Path = None,
) -> None:
    """Resets all requested tracker files for the target session to the original (unprocessed) state.

    This function loops over all specified tracker files and uses the 'abort' method of the ProcessingTracker class to
    reset them to the default state. Primarily, this function is designed to recover the tracker files when their
    pipelines are interrupted without going through the typical Python error handling loop. For example, this is the
    case if the pipeline runs for too long and is forcibly terminated by the SLURM manager of the server that executes
    the pipeline.

    Notes:
        If any of the target tracker files do not exist, the function silently skips processing these files.

    Args:
        session_path: The path to the root session directory for which to reset the trackers.
        trackers: A tuple that stores the TrackerFileNames instances, one for each tracker file to be reset. If this
            argument is set to None, this function resets all files defined in the TrackerFileNames enumeration.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the session data root.
    """

    # Loads session data layout. If configured to do so, also creates the processed data hierarchy
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )

    console.echo(
        message=f"Resetting processing trackers for session '{session_data.session_name}'...",
        level=LogLevel.INFO,
    )

    # If the user did not specify an explicit set of trackers to process, evaluates all valid tracker files.
    if trackers is None:
        trackers = tuple(TrackerFileNames)

    # Loops over and resets all requested trackers if they are found under the raw_data or processed_data session
    # directory.
    for tracker in trackers:
        # If the tracker file exists in the raw data directory, resets it by calling the 'abort' method.
        tracker_path = session_data.raw_data.raw_data_path.joinpath(str(tracker))
        if tracker_path.exists():
            processing_tracker = ProcessingTracker(file_path=tracker_path)
            processing_tracker.abort()
            console.echo(
                message=f"Tracker file '{tracker}' for session '{session_data.session_name}': Reset.",
                level=LogLevel.SUCCESS,
            )

        # If the tracker file exists in the processed data directory, resets it by calling the 'abort' method.
        tracker_path = session_data.processed_data.processed_data_path.joinpath(str(tracker))
        if tracker_path.exists():
            processing_tracker = ProcessingTracker(file_path=tracker_path)
            processing_tracker.abort()
            console.echo(
                message=f"Tracker file '{tracker}' for session '{session_data.session_name}': Reset",
                level=LogLevel.SUCCESS,
            )

    # Updates or generates the manifest file inside the root raw data project directory
    generate_project_manifest(
        raw_project_directory=session_data.raw_data.root_path.joinpath(session_data.project_name),
        processed_data_root=processed_data_root,
    )


def prepare_session(
    session_path: Path,
    manager_id: int,
    processed_data_root: Path | None,
) -> None:
    """Prepares the target session for processing.

    This function is primarily designed to be used on remote compute servers that use different data volumes for
    storage and processing. Since storage volumes are often slow, the session data needs to be copied to the fast
    volume before executing processing pipelines. In addition to copying the raw data, depending on configuration, this
    function also moves (archived) processed data and resets the requested processing pipeline trackers for the managed
    session.

    Notes:
        This function inverses the result of running the archive_session() function.
    """
    # Resolves the data hierarchy for the processed session
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )

    # Initializes the ProcessingTracker instances for the archiving and preparation pipelines (which are in essence the
    # inverses of each-other).
    archive_tracker = ProcessingTracker(
        file_path=session_data.raw_data.raw_data_path.joinpath(TrackerFileNames.ARCHIVE)
    )
    preparation_tracker = ProcessingTracker(
        file_path=session_data.raw_data.raw_data_path.joinpath(TrackerFileNames.PREPARATION)
    )

    # Updates the tracker data to communicate that the preparation process has started. This automatically clears
    # the previous 'completed' status.
    preparation_tracker.start(manager_id=manager_id)
    try:
        console.echo(
            message=f"Preparing session '{session_data.session_name}' for data processing...", level=LogLevel.INFO
        )

        # If the processed data root is different from the raw data root, copies the raw_data directory to the
        # session's source_data directory (a copy of raw_data stored on the processed_data volume)
        if session_data.raw_data.root_path != session_data.processed_data.root_path:
            console.echo(
                message=f"Transferring the 'raw_data' directory to the processed data root...", level=LogLevel.INFO
            )
            transfer_directory(
                source=session_data.raw_data.raw_data_path,
                destination=session_data.source_data.raw_data_path,
                num_threads=0,
                verify_integrity=False,
            )

            # If the session contains archived processed data, replaced the contents of the 'processed_data' folder
            # on the processed data volume with the contents of the 'processed_data' folder on the raw data (storage)
            # volume.
            if archive_tracker.is_complete and session_data.raw_data.processed_data_path.exists():
                console.echo(
                    message=f"Transferring the archived 'processed_data' directory to the processed data root...",
                    level=LogLevel.INFO,
                )
                transfer_directory(
                    source=session_data.raw_data.processed_data_path,
                    destination=session_data.processed_data.processed_data_path,
                    num_threads=0,
                    verify_integrity=False,
                )

                # Removes the transferred directory to ensure only a single copy of the 'processed_data' directory
                # exists on the processing machine. While not strictly necessary, this is a good error-preventing
                # practice.
                console.echo(
                    message=f"Removing the now-redundant archived 'processed_data' directory...",
                    level=LogLevel.INFO,
                )
                delete_directory(session_path.joinpath("processed_data"))

        # Preparation is complete
        preparation_tracker.stop(manager_id=manager_id)
        # Clears the archiving tracker state to properly reflect that the session is no longer archived
        archive_tracker.abort()
        console.echo(
            message=f"Session '{session_data.session_name}': Prepared for data processing.", level=LogLevel.SUCCESS
        )

    finally:
        # If the code reaches this section while the tracker indicates that the processing is still running,
        # this means that the runtime encountered an error.
        if preparation_tracker.is_running:
            preparation_tracker.error(manager_id=manager_id)

        # Updates or generates the manifest file inside the root raw data project directory
        generate_project_manifest(
            raw_project_directory=session_data.raw_data.root_path.joinpath(session_data.project_name),
            processed_data_root=processed_data_root,
        )


def archive_session(
    session_path: Path,
    manager_id: int,
    processed_data_root: Path | None = None,
) -> None:
    """Prepares the target session for long-term storage.

    This function is primarily designed to be used on remote compute servers that use different data volumes for
    storage and processing. It should be called for sessions that are no longer frequently processed or accessed to move
    all session data to the (slow) storage volume and free up the fast processing volume for working with other data.

    Notes:
        This function inverses the result of running the process_session() function.
    """
    # Resolves the data hierarchy for the processed session
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )

    # Initializes the ProcessingTracker instances for the archiving and preparation pipelines (which are in essence the
    # inverses of each-other).
    archive_tracker = ProcessingTracker(
        file_path=session_data.raw_data.raw_data_path.joinpath(TrackerFileNames.ARCHIVE)
    )
    preparation_tracker = ProcessingTracker(
        file_path=session_data.raw_data.raw_data_path.joinpath(TrackerFileNames.PREPARATION)
    )

    # Starts the runtime
    archive_tracker.start(manager_id=manager_id)
    try:
        console.echo(message=f"Arching session '{session_data.session_name}'...", level=LogLevel.INFO)

        # If the processed data root is different from the raw data root, transfers the processed_data directory from
        # the processed_data root to the raw_data root.
        if (
            session_data.raw_data.root_path != session_data.processed_data.root_path
            and not session_data.raw_data.processed_data_path.exists()
        ):
            console.echo(
                message=f"Transferring (archiving) 'processed_data' directory to the raw data volume...",
                level=LogLevel.INFO,
            )
            transfer_directory(
                source=session_data.processed_data.processed_data_path,
                destination=session_data.raw_data.processed_data_path,
                num_threads=0,
                verify_integrity=False,
            )

            # Removes the transferred directory to ensure that the data transfer can only occur once until the
            # processed data is prepared again.
            console.echo(
                message=f"Removing the 'processed_data' directory from the processed data volume...",
                level=LogLevel.INFO,
            )
            delete_directory(session_data.processed_data.processed_data_path)

            # Also removes the raw_data (source_data) directory from the processed data volume.
            if session_data.source_data.raw_data_path.exists():
                console.echo(
                    message=f"Removing the 'raw_data' directory from the processed data volume...",
                    level=LogLevel.INFO,
                )
                delete_directory(session_data.source_data.raw_data_path)

        # Archiving is complete
        archive_tracker.stop(manager_id=manager_id)
        # Clears the preparation tracker state to properly reflect that the session is no longer prepared
        preparation_tracker.abort()
        console.echo(message=f"Session '{session_data.session_name}': Archived.", level=LogLevel.SUCCESS)

    finally:
        # If the code reaches this section while the tracker indicates that the processing is still running,
        # this means that the runtime encountered an error.
        if archive_tracker.is_running:
            archive_tracker.error(manager_id=manager_id)

        # Updates or generates the manifest file inside the root raw data project directory
        generate_project_manifest(
            raw_project_directory=session_data.raw_data.root_path.joinpath(session_data.project_name),
            processed_data_root=processed_data_root,
        )


def resolve_p53_marker(
    session_path: Path,
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

        For the p53.bin marker to be created, the session must not be undergoing processing. For the p53 marker
        to be removed, the session must not be undergoing dataset integration.

    Args:
        session_path: The path to the session directory for which the p53.bin marker needs to be resolved. Note, the
            input session directory must contain the 'raw_data' subdirectory.
        processed_data_root: The root directory where to store the processed data hierarchy. This path has to point to
            the root directory where to store the processed data from all projects, and it will be automatically
            modified to include the project name, the animal name, and the session ID.
        remove: Determines whether this function is called to create or remove the p53.bin marker.
    """

    # Loads session data layout. If configured to do so, also creates the processed data hierarchy
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )

    # If the p53.bin marker exists and the runtime is configured to remove it, attempts to remove the marker file.
    if session_data.processed_data.p53_path.exists() and remove:
        # This section deals with a unique nuance related to the Sun lab processing server organization. Specifically,
        # the user accounts are not allowed to modify or create files in the data directories owned by the service
        # accounts. In turn, this prevents user accounts from modifying the processed data directory to indicate when
        # they are running a dataset integration pipeline on the processed data. To work around this problem, the
        # dataset integration pipeline now creates a 'semaphore' marker for each session that is currently being
        # integrated into a dataset. This semaphore marker is stored under the root user working directory, inside the
        # subdirectory called 'semaphore'.

        # The parent of the shared sun-lab processed data directory is the root 'working' volume. All user directories
        # are stored under this root working directory.
        if processed_data_root is None:
            # If the processed data root is not provided, sets it to the great-grandparent of the session directory.
            # This works assuming that the data is stored under: root/project/animal/session.
            processed_data_root = session_path.parents[2]
        working_root = processed_data_root.parent

        # Loops over each user directory and checks whether a semaphore marker exists for the processed session.
        for directory in working_root.iterdir():
            if (
                len([marker for marker in directory.joinpath("semaphore").glob(f"*{session_data.session_name}.bin")])
                > 0
            ):
                # Aborts with an error if the semaphore marker prevents the p53 marker from being removed.
                message = (
                    f"Unable to remove the dataset marker for the session' {session_data.session_name}' acquired "
                    f"for the animal '{session_data.animal_id}' under the '{session_data.project_name}' project. "
                    f"The session data is currently being integrated into a dataset by the owner the "
                    f"'{directory.stem}' user directory. Wait until the ongoing dataset integration is complete and "
                    f"repeat the command that produced this error."
                )
                console.error(message=message, error=RuntimeError)

        # If the session does not have a corresponding semaphore marker in any user directories, removes the p53 marker
        # file.
        session_data.processed_data.p53_path.unlink()
        message = (
            f"Dataset marker for the session '{session_data.session_name}' acquired for the animal "
            f"'{session_data.animal_id}' under the '{session_data.project_name}' project: Removed."
        )
        console.echo(message=message, level=LogLevel.SUCCESS)
        return  # Ends remove runtime

    # If the marker does not exist and the function is called in 'remove' mode, aborts the runtime early
    elif not session_data.processed_data.p53_path.exists() and remove:
        message = (
            f"Dataset marker for the session '{session_data.session_name}' acquired for the animal "
            f"'{session_data.animal_id}' under the '{session_data.project_name}' project: Does not exist. No actions "
            f"taken."
        )
        console.echo(message=message, level=LogLevel.SUCCESS)
        return  # Ends remove runtime

    elif session_data.processed_data.p53_path.exists():
        message = (
            f"Dataset marker for the session '{session_data.session_name}' acquired for the animal "
            f"'{session_data.animal_id}' under the '{session_data.project_name}' project: Already exists. No actions "
            f"taken."
        )
        console.echo(message=message, level=LogLevel.SUCCESS)
        return  # Ends create runtime

    # The rest of the runtime deals with determining whether it is safe to create the marker file.
    # Queries the type of the processed session
    session_type = session_data.session_type

    # Window checking sessions are not designed to be integrated into datasets, so they cannot be marked with the
    # p53.bin file. Similarly, any incomplete session is automatically excluded from dataset formation.
    if session_type == SessionTypes.WINDOW_CHECKING or not session_data.raw_data.telomere_path.exists():
        message = (
            f"Unable to generate the dataset marker for the session '{session_data.session_name}' acquired for the "
            f"animal '{session_data.animal_id}' under the '{session_data.project_name}' project, as the session is "
            f"incomplete or is of Window Checking type. These sessions must be manually evaluated and marked for "
            f"dataset inclusion by the experimenter. "
        )
        console.error(message=message, error=RuntimeError)

    # Training sessions collect similar data and share processing pipeline requirements
    error: bool = False
    if session_type == SessionTypes.LICK_TRAINING or session_type == SessionTypes.RUN_TRAINING:
        # Ensures that the session is not being processed with one of the supported pipelines.
        behavior_tracker = ProcessingTracker(
            file_path=session_data.processed_data.processed_data_path.joinpath(TrackerFileNames.BEHAVIOR)
        )
        video_tracker = ProcessingTracker(
            file_path=session_data.processed_data.processed_data_path.joinpath(TrackerFileNames.VIDEO)
        )
        if behavior_tracker.is_running or video_tracker.is_running:
            # Note, training runtimes do not require suite2p processing.
            error = True

    # Mesoscope experiment sessions require additional processing with suite2p
    elif session_type == SessionTypes.MESOSCOPE_EXPERIMENT:
        behavior_tracker = ProcessingTracker(
            file_path=session_data.processed_data.processed_data_path.joinpath(TrackerFileNames.BEHAVIOR)
        )
        suite2p_tracker = ProcessingTracker(
            file_path=session_data.processed_data.processed_data_path.joinpath(TrackerFileNames.SUITE2P)
        )
        video_tracker = ProcessingTracker(
            file_path=session_data.processed_data.processed_data_path.joinpath(TrackerFileNames.VIDEO)
        )
        console.echo(f"{behavior_tracker.is_running}")
        if behavior_tracker.is_running or video_tracker.is_running or suite2p_tracker.is_running:
            error = True

    # If the session is currently being processed by one or more pipelines, aborts with an error.
    if error:
        message = (
            f"Unable to generate the dataset marker for the session '{session_data.session_name}' acquired for the "
            f"animal '{session_data.animal_id}' under the '{session_data.project_name}' project, as it is "
            f"currently being processed by one of the data processing pipelines. Wait until the session is fully "
            f"processed by all pipelines and repeat the command that encountered this error."
        )
        console.error(message=message, error=RuntimeError)

    # If the runtime reached this point, the session is eligible for dataset integration. Creates the p53.bin marker
    # file, preventing the session from being processed again as long as the marker exists.
    session_data.processed_data.p53_path.touch()
    message = (
        f"Dataset marker for the session '{session_data.session_name}' acquired for the animal "
        f"'{session_data.animal_id}' under the '{session_data.project_name}' project: Created."
    )
    console.echo(message=message, level=LogLevel.SUCCESS)

    # Generates the manifest file inside the root raw data project directory
    generate_project_manifest(
        raw_project_directory=session_data.raw_data.root_path.joinpath(session_data.project_name),
        processed_data_root=processed_data_root,
    )


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

    def __init__(self, manifest_file: Path):
        # Reads the data from the target manifest file into the class attribute
        self._data: pl.DataFrame = pl.read_ipc(source=manifest_file, use_pyarrow=True)

        # Determines whether animal IDs are stored as strings or as numbers
        self._animal_string = False
        schema = self._data.collect_schema()
        if isinstance(schema["animal"], pl.String):
            self._animal_string = True

    def print_data(self) -> None:
        """Prints the entire contents of the manifest file to the terminal."""
        with pl.Config(
            set_tbl_rows=-1,  # Displays all rows (-1 means unlimited)
            set_tbl_cols=-1,  # Displays all columns (-1 means unlimited)
            set_tbl_hide_column_data_types=True,
            set_tbl_cell_alignment="LEFT",
            set_tbl_width_chars=250,  # Sets table width to 200 characters
            set_fmt_str_lengths=600,  # Allows longer strings to display properly (default is 32)
        ):
            print(self._data)

    def print_summary(self, animal: str | int | None = None) -> None:
        """Prints a summary view of the manifest file to the terminal, excluding the 'experimenter notes' data for
        each session.

        This data view is optimized for tracking which processing steps have been applied to each session inside the
        project.

        Args:
            animal: The ID of the animal for which to display the data. If an ID is provided, this method will only
                display the data for that animal. Otherwise, it will display the data for all animals.
        """
        summary_cols = [
            "animal",
            "date",
            "session",
            "type",
            "system",
            "complete",
            "integrity",
            "prepared",
            "archived",
            "suite2p",
            "behavior",
            "video",
            "dataset",
        ]

        # Retrieves the data
        df = self._data.select(summary_cols)

        # Optionally filters the data for the target animal
        if animal is not None:
            # Ensures that the 'animal' argument has the same type as the data inside the DataFrame.
            if self._animal_string:
                animal = str(animal)
            else:
                animal = int(animal)
            df = df.filter(pl.col("animal") == animal)

        # Ensures the data displays properly
        with pl.Config(
            set_tbl_rows=-1,
            set_tbl_cols=-1,
            set_tbl_width_chars=250,
            set_tbl_hide_column_data_types=True,
            set_tbl_cell_alignment="CENTER",
        ):
            print(df)

    def print_notes(self, animal: str | int | None = None) -> None:
        """Prints only animal, session, and notes data from the manifest file.

        This data view is optimized for experimenters to check what sessions have been recorded for each animal in the
        project and refresh their memory on the outcomes of each session using experimenter notes.

        Args:
            animal: The ID of the animal for which to display the data. If an ID is provided, this method will only
                display the data for that animal. Otherwise, it will display the data for all animals.
        """

        # Pre-selects the columns to display
        df = self._data.select(["animal", "date", "session", "type", "system", "notes"])

        # Optionally filters the data for the target animal
        if animal is not None:
            # Ensures that the 'animal' argument has the same type as the data inside the DataFrame.
            if self._animal_string:
                animal = str(animal)
            else:
                animal = int(animal)

            df = df.filter(pl.col("animal") == animal)

        #  Prints the extracted data
        with pl.Config(
            set_tbl_rows=-1,
            set_tbl_cols=-1,
            set_tbl_hide_column_data_types=True,
            set_tbl_cell_alignment="LEFT",
            set_tbl_width_chars=250,  # Wider columns for notes
            set_fmt_str_lengths=600,  # Allows very long strings for notes
        ):
            print(df)

    @property
    def animals(self) -> tuple[str, ...]:
        """Returns all unique animal IDs stored inside the manifest file.

        This provides a tuple of all animal IDs participating in the target project.
        """
        return tuple(
            [str(animal) for animal in self._data.select("animal").unique().sort("animal").to_series().to_list()]
        )

    def _get_filtered_sessions(
        self,
        animal: str | int | None = None,
        exclude_incomplete: bool = True,
        dataset_ready_only: bool = False,
        not_dataset_ready_only: bool = False,
    ) -> tuple[str, ...]:
        """This worker method is used to get a list of sessions with optional filtering.

        User-facing methods call this worker under-the-hood to fetch the filtered tuple of sessions.

        Args:
            animal: An optional animal ID to filter the sessions. If set to None, the method returns sessions for all
                animals.
            exclude_incomplete: Determines whether to exclude sessions not marked as 'complete' from the output
                list.
            dataset_ready_only: Determines whether to exclude sessions not marked as 'dataset' integration ready from
                the output list. Enabling this option only shows sessions that can be integrated into a dataset.
            not_dataset_ready_only: The opposite of 'dataset_ready_only'. Determines whether to exclude sessions marked
                as 'dataset' integration ready from the output list. Note, when both this and 'dataset_ready_only' are
                enabled, the 'dataset_ready_only' option takes precedence.

        Returns:
            The tuple of session IDs matching the filter criteria.

        Raises:
            ValueError: If the specified animal is not found in the manifest file.
        """
        data = self._data

        # Filter by animal if specified
        if animal is not None:
            # Ensures that the 'animal' argument has the same type as the data inside the DataFrame.
            if self._animal_string:
                animal = str(animal)
            else:
                animal = int(animal)

            if animal not in self.animals:
                message = f"Animal ID '{animal}' not found in the project manifest. Available animals: {self.animals}."
                console.error(message=message, error=ValueError)

            data = data.filter(pl.col("animal") == animal)

        # Optionally filters out incomplete sessions
        if exclude_incomplete:
            data = data.filter(pl.col("complete") == 1)

        # Optionally filters sessions based on their readiness for dataset integration.
        if dataset_ready_only:  # Dataset-ready option always takes precedence
            data = data.filter(pl.col("dataset") == 1)
        elif not_dataset_ready_only:
            data = data.filter(pl.col("dataset") == 0)

        # Formats and returns session IDs to the caller
        sessions = data.select("session").sort("session").to_series().to_list()
        return tuple(sessions)

    @property
    def sessions(self) -> tuple[str, ...]:
        """Returns all session IDs stored inside the manifest file.

        This property provides a tuple of all sessions, independent of the participating animal, that were recorded as
        part of the target project. Use the get_sessions() method to get the list of session tuples with filtering.
        """
        return self._get_filtered_sessions(animal=None, exclude_incomplete=False)

    def get_sessions(
        self,
        animal: str | int | None = None,
        exclude_incomplete: bool = True,
        dataset_ready_only: bool = False,
        not_dataset_ready_only: bool = False,
    ) -> tuple[str, ...]:
        """Returns requested session IDs based on selected filtering criteria.

        This method provides a tuple of sessions based on the specified filters. If no animal is specified, returns
        sessions for all animals in the project.

        Args:
            animal: An optional animal ID to filter the sessions. If set to None, the method returns sessions for all
                animals.
            exclude_incomplete: Determines whether to exclude sessions not marked as 'complete' from the output
                list.
            dataset_ready_only: Determines whether to exclude sessions not marked as 'dataset' integration ready from
                the output list. Enabling this option only shows sessions that can be integrated into a dataset.
            not_dataset_ready_only: The opposite of 'dataset_ready_only'. Determines whether to exclude sessions marked
                as 'dataset' integration ready from the output list. Note, when both this and 'dataset_ready_only' are
                enabled, the 'dataset_ready_only' option takes precedence.

        Returns:
            The tuple of session IDs matching the filter criteria.

        Raises:
            ValueError: If the specified animal is not found in the manifest file.
        """
        return self._get_filtered_sessions(
            animal=animal,
            exclude_incomplete=exclude_incomplete,
            dataset_ready_only=dataset_ready_only,
            not_dataset_ready_only=not_dataset_ready_only,
        )

    def get_session_info(self, session: str) -> pl.DataFrame:
        """Returns a Polars DataFrame that stores detailed information for the specified session.

        Since session IDs are unique, it is expected that filtering by session ID is enough to get the requested
        information.

        Args:
            session: The ID of the session for which to retrieve the data.

        Returns:
            A Polars DataFrame with the following columns: 'animal', 'date', 'notes', 'session', 'type', 'complete',
            'intensity_verification', 'suite2p', 'behavior', 'video', 'dataset'.
        """

        df = self._data
        df = df.filter(pl.col("session").eq(session))
        return df
