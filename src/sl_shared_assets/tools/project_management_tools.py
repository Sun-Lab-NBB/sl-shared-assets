"""This module provides tools for managing the data of any Sun lab project. Tools from this module are primarily used
to support data processing pipelines that make up the Sun lab data workflow and run on the remote compute server."""

from pathlib import Path
from datetime import datetime

import pytz
import polars as pl
from filelock import FileLock
from ataraxis_base_utilities import LogLevel, console

from ..server import TrackerFileNames, ProcessingTracker
from ..data_classes import (
    SessionData,
    SessionLock,
    SessionTypes,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
)
from .transfer_tools import delete_directory, transfer_directory
from .packaging_tools import calculate_directory_checksum


def acquire_lock(
    session_path: Path, manager_id: int, processed_data_root: Path | None = None, reset_lock: bool = False
) -> None:
    """Acquires the target session's data lock for the specified manager process.

    Calling this function locks the target session's data to make it accessible only for the specified manager process.

    Notes:
        Each time this function is called, the release_lock() function must also be called to release the lock file.

    Args:
        session_path: The path to the session directory to be locked.
        manager_id: The unique identifier of the manager process that acquires the lock.
        reset_lock: Determines whether to reset the lock file before executing the runtime. This allows recovering
            from deadlocked runtimes, but otherwise should not be used to ensure that the lock performs its intended
            function of limiting access to session's data.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.
    """

    # Resolves the session directory hierarchy
    session = SessionData.load(session_path=session_path, processed_data_root=processed_data_root)

    # Instantiates the lock instance for the session
    lock = SessionLock(file_path=session.tracking_data.session_lock_path)

    # If requested, forcibly resets the lock state before re-acquiring the lock for the specified manager
    if reset_lock:
        lock.force_release()

    # Acquires the lock for the specified manager.
    lock.acquire(manager_id=manager_id)


def release_lock(session_path: Path, manager_id: int, processed_data_root: Path | None = None) -> None:
    """Releases the target session's data lock if it is owned by the specified manager process.

    Calling this function unlocks the session's data, making it possible for other manager processes to acquire the
    lock and work with the session's data. This step has to be performed by every manager process as part of its
    shutdown sequence if the manager called the acquire_lock() function.

    Args:
        session_path: The path to the session directory to be unlocked.
        manager_id: The unique identifier of the manager process that releases the lock.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.
    """

    # Resolves the session directory hierarchy
    session = SessionData.load(session_path=session_path, processed_data_root=processed_data_root)

    # Releases the lock for the target session
    lock = SessionLock(file_path=session.tracking_data.session_lock_path)
    lock.release(manager_id=manager_id)


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
            carrying out the verification. In this case, the verification necessarily succeeds, and the session's
            reference checksum is changed to reflect the current state of the session data.
    """

    # Loads session data layout. If configured to do so, also creates the processed data hierarchy
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )

    # Ensures that the manager process is holding the session lock
    lock = SessionLock(file_path=session_data.tracking_data.session_lock_path)
    lock.check_owner(manager_id=manager_id)

    # Initializes the ProcessingTracker instance
    tracker = ProcessingTracker(
        file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.CHECKSUM)
    )

    # If requested, reset the tracker to the default state before starting the checksum resolution process.
    if reset_tracker:
        tracker.abort()

    # Updates the tracker data to communicate that the process has started. This automatically clears the previous
    # processing status stored in the file.
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
            # Sets the tracker to indicate that the runtime completed successfully.
            tracker.stop(manager_id=manager_id)
            console.echo(
                message=f"Session '{session_data.session_name}' raw data integrity: Verified.", level=LogLevel.SUCCESS
            )

    finally:
        # If the code reaches this section while the tracker indicates that the processing is still running,
        # this means that the runtime encountered an error.
        if tracker.is_running:
            tracker.error(manager_id=manager_id)

        # Updates or generates the manifest file inside the root raw data project directory
        generate_project_manifest(
            raw_project_directory=session_data.raw_data.root_path.joinpath(session_data.project_name),
            processed_data_root=processed_data_root,
            manager_id=manager_id,
        )


def prepare_session(
    session_path: Path,
    manager_id: int,
    processed_data_root: Path | None,
    reset_tracker: bool = False,
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
    # Resolves the data hierarchy for the processed session
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )

    # Ensures that the manager process is holding the session lock
    lock = SessionLock(file_path=session_data.tracking_data.session_lock_path)
    lock.check_owner(manager_id=manager_id)

    # Initializes the ProcessingTracker instances for preparation and archiving pipelines.
    preparation_tracker = ProcessingTracker(
        file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.PREPARATION)
    )
    archiving_tracker = ProcessingTracker(
        file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.ARCHIVING)
    )

    # Explicitly prevents colliding with ongoing archiving runtimes.
    if archiving_tracker.is_running:
        message = (
            f"Unable to prepare the session '{session_data.session_name}' for data processing, as it is currently "
            f"being archived. Abort the archiving process or wait for it to complete before retrying."
        )
        console.error(message=message, error=RuntimeError)

    # Resets the preparation tracker, if requested.
    if reset_tracker:
        preparation_tracker.abort()

    # Starts the preparation runtime
    preparation_tracker.start(manager_id=manager_id)
    try:
        console.echo(
            message=f"Preparing session '{session_data.session_name}' for data processing...", level=LogLevel.INFO
        )

        # If the session uses different roots for 'raw' and 'source' data, copies raw_data folder to the path
        # specified by the 'source_data'.
        if session_data.raw_data.root_path != session_data.source_data.root_path:
            console.echo(
                message=f"Copying the 'raw_data' directory to the working volume as the 'source_data' directory...",
                level=LogLevel.INFO,
            )
            transfer_directory(
                source=session_data.raw_data.raw_data_path,
                destination=session_data.source_data.raw_data_path,
                num_threads=0,
                verify_integrity=False,
                remove_source=False,
            )

        # If the session contains archived processed data, restores the data to the working root.
        if (
            session_data.archived_data.root_path != session_data.processed_data.root_path
            and archiving_tracker.is_complete
            and session_data.archived_data.processed_data_path.exists()
        ):
            console.echo(
                message=(
                    f"Transferring the 'archived_data' directory to the working volume as the 'processed_data' "
                    f"directory..."
                ),
                level=LogLevel.INFO,
            )
            transfer_directory(
                source=session_data.archived_data.processed_data_path,
                destination=session_data.processed_data.processed_data_path,
                num_threads=0,
                verify_integrity=False,
                remove_source=True,
            )

        # Preparation is complete
        preparation_tracker.stop(manager_id=manager_id)
        archiving_tracker.abort()  # Resets the state of the archiving tracker, as the session is no longer archived.
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
            manager_id=manager_id,
        )


def archive_session(
    session_path: Path,
    manager_id: int,
    reset_tracker: bool = False,
    processed_data_root: Path | None = None,
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
        reset_tracker: Determines whether to reset the tracker file before executing the runtime. This allows
            recovering from deadlocked runtimes, but otherwise should not be used to ensure runtime safety.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects,
            if different from the 'session_path' root.

    Notes:
        This function inverses the result of running the prepare_session() function.
    """
    # Resolves the data hierarchy for the processed session
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )

    # Ensures that the manager process is holding the session lock
    lock = SessionLock(file_path=session_data.tracking_data.session_lock_path)
    lock.check_owner(manager_id=manager_id)

    # Initializes the ProcessingTracker instances for preparation and archiving pipelines.
    preparation_tracker = ProcessingTracker(
        file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.PREPARATION)
    )
    archiving_tracker = ProcessingTracker(
        file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.ARCHIVING)
    )

    # Explicitly prevents colliding with ongoing preparation runtimes.
    if preparation_tracker.is_running:
        message = (
            f"Unable to archive the session '{session_data.session_name}' for long-term storage, as it is currently "
            f"being prepared for data processing. Abort the preparation process or wait for it to complete before "
            f"retrying."
        )
        console.error(message=message, error=RuntimeError)

    # Resets the archiving tracker, if requested.
    if reset_tracker:
        archiving_tracker.abort()

    # Starts the archiving runtime.
    archiving_tracker.start(manager_id=manager_id)
    try:
        console.echo(message=f"Arching session '{session_data.session_name}'...", level=LogLevel.INFO)

        # If the 'processed_data' root is different from the 'archived_data' root, transfers the 'processed_data'
        # directory to the paths specified by 'archived_data'.
        if (
            session_data.processed_data.root_path != session_data.archived_data.root_path
            and session_data.processed_data.processed_data_path.exists()
        ):
            console.echo(
                message=(
                    f"Transferring (archiving) the 'processed_data' directory to the storage volume as the "
                    f"'archived_data' directory..."
                ),
                level=LogLevel.INFO,
            )
            transfer_directory(
                source=session_data.processed_data.processed_data_path,
                destination=session_data.archived_data.processed_data_path,
                num_threads=0,
                verify_integrity=False,
                remove_source=True,
            )

        # Also ensures that the 'source_data' folder is removed from the working volume.
        if session_data.raw_data.root_path != session_data.source_data.root_path:
            console.echo(
                message=f"Removing the redundant 'source_data' directory from the working volume...",
                level=LogLevel.INFO,
            )
            delete_directory(session_data.source_data.raw_data_path)

        # Archiving is complete
        archiving_tracker.stop(manager_id=manager_id)
        preparation_tracker.abort()  # Resets the preparation tracker, as the session is no longer prepared.
        console.echo(message=f"Session '{session_data.session_name}': Archived.", level=LogLevel.SUCCESS)

    finally:
        # If the code reaches this section while the tracker indicates that the processing is still running,
        # this means that the runtime encountered an error.
        if archiving_tracker.is_running:
            archiving_tracker.error(manager_id=manager_id)

        # Updates or generates the manifest file inside the root raw data project directory
        generate_project_manifest(
            raw_project_directory=session_data.raw_data.root_path.joinpath(session_data.project_name),
            processed_data_root=processed_data_root,
            manager_id=manager_id,
        )


def generate_project_manifest(
    raw_project_directory: Path,
    manager_id: int,
    processed_data_root: Path | None = None,
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

    if not raw_project_directory.exists():
        message = (
            f"Unable to generate the project manifest file for the requested project {raw_project_directory.stem}. "
            f"The specified project directory does not exist."
        )
        console.error(message=message, error=FileNotFoundError)

    # Finds all session directories for the target project
    session_directories = [directory.parent for directory in raw_project_directory.rglob("raw_data")]

    if len(session_directories) == 0:
        message = (
            f"Unable to generate the project manifest file for the requested project {raw_project_directory.stem}. The "
            f"project does not contain any raw session data. To generate the manifest file, the project must contain "
            f"the data for at least one session."
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
        # Determines whether the session has been processed with the single-day s2p pipeline.
        "suite2p": [],
        # Determines whether the session has been processed with the behavior extraction pipeline.
        "behavior": [],
        # Determines whether the session has been processed with the DeepLabCut pipeline.
        "video": [],
        # Determines whether the session's data has been archived for long-term storage.
        "archived": [],
    }

    # Resolves the path to the manifest .feather file to be created and the .lock file to ensure only a single process
    # can be working on the manifest file at the same time.
    manifest_path = raw_project_directory.joinpath(f"{raw_project_directory.stem}_manifest.feather")
    manifest_lock = manifest_path.with_suffix(manifest_path.suffix + ".lock")

    # Also instantiates the processing tracker for the manifest file in the same directory. Note, unlike for most other
    # runtimes, the tracker is NOT used to limit the ability of other processes to run the manifest generation. That
    # job is handled to the manifest lock file. Instead, the tracker is used to communicate whether the manifest
    # generation runs as expected or encounters an error.
    runtime_tracker = ProcessingTracker(file_path=raw_project_directory.joinpath(TrackerFileNames.MANIFEST))

    # Since the exclusivity of the data manifest generation runtime is enforced through the manifest .lock file, this
    # runtime always resets the processing tracker file.
    runtime_tracker.abort()

    # Acquires the lock file, ensuring only this specific process can work with the manifest data.
    lock = FileLock(str(manifest_lock))
    with lock.acquire(timeout=20.0):
        # Starts the manifest generation process.
        runtime_tracker.start(manager_id=manager_id)
        try:
            # Loops over each session of every animal in the project and extracts session ID information and
            # information about which processing steps have been successfully applied to the session.
            for directory in session_directories:
                # Skips processing directories without files (sessions with empty raw_data directories)
                if len([file for file in directory.joinpath("raw_data").glob("*")]) == 0:
                    continue

                # Instantiates the SessionData instance to resolve the paths to all session's data files and locations.
                session_data = SessionData.load(
                    session_path=directory,
                    processed_data_root=processed_data_root,
                )

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

                # Depending on the session type, instantiates the appropriate descriptor instance and uses it to read
                # the experimenter notes
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
                    # Raises an error if an unsupported session type is encountered.
                    message = (
                        f"Unsupported session type '{session_data.session_type}' encountered for session "
                        f"'{directory.stem}' when generating the manifest file for the project "
                        f"{raw_project_directory.stem}. Currently, only the following session types are supported: "
                        f"{tuple(SessionTypes)}."
                    )
                    console.error(message=message, error=ValueError)
                    raise ValueError(message)  # Fallback to appease mypy, should not be reachable

                # If the session raw_data folder contains the telomere.bin file, marks the session as complete.
                manifest["complete"].append(session_data.raw_data.telomere_path.exists())

                # Data integrity verification status
                tracker = ProcessingTracker(
                    file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.CHECKSUM)
                )
                manifest["integrity"].append(tracker.is_complete)

                # If the session is incomplete or unverified, marks all processing steps as FALSE, as automatic
                # processing is disabled for incomplete sessions and, therefore, it could not have been processed.
                if not manifest["complete"][-1] or not manifest["integrity"][-1]:
                    manifest["suite2p"].append(False)
                    manifest["behavior"].append(False)
                    manifest["video"].append(False)
                    manifest["prepared"].append(False)
                    manifest["archived"].append(False)
                    continue  # Cycles to the next session

                # Session data preparation (for processing) status.
                tracker = ProcessingTracker(
                    file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.PREPARATION)
                )
                manifest["prepared"].append(tracker.is_complete)

                # Suite2p (single-day) processing status.
                tracker = ProcessingTracker(
                    file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.SUITE2P)
                )
                manifest["suite2p"].append(tracker.is_complete)

                # Behavior data processing status.
                tracker = ProcessingTracker(
                    file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.BEHAVIOR)
                )
                manifest["behavior"].append(tracker.is_complete)

                # DeepLabCut (video) processing status.
                tracker = ProcessingTracker(
                    file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.VIDEO)
                )
                manifest["video"].append(tracker.is_complete)

                # Session data archiving status.
                tracker = ProcessingTracker(
                    file_path=session_data.tracking_data.tracking_data_path.joinpath(TrackerFileNames.ARCHIVING)
                )
                manifest["archived"].append(tracker.is_complete)

            # If all animal IDs are integer-convertible, stores them as numbers to promote proper sorting.
            # Otherwise, stores them as strings. The latter options are primarily kept for compatibility with Tyche
            # data.
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
                "suite2p": pl.UInt8,
                "behavior": pl.UInt8,
                "video": pl.UInt8,
                "archived": pl.UInt8,
            }
            df = pl.DataFrame(manifest, schema=schema, strict=False)

            # Sorts the DataFrame by animal and then session. Since animal IDs are monotonically increasing according to
            # Sun lab standards and session 'names' are based on acquisition timestamps, the sort order is
            # chronological.
            sorted_df = df.sort(["animal", "session"])

            # Saves the generated manifest to the project-specific manifest .feather file for further processing.
            sorted_df.write_ipc(file=manifest_path, compression="lz4")

            # The processing is now complete.
            runtime_tracker.stop(manager_id=manager_id)

        finally:
            # If the tracker indicates that the processing is still running, the runtime has encountered an error.
            if runtime_tracker.is_running:
                tracker.error(manager_id=manager_id)


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
            "suite2p",
            "behavior",
            "video",
            "archived",
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
            set_tbl_width_chars=100,  # Wider columns for notes
            set_fmt_str_lengths=800,  # Allows very long strings for notes
        ):
            print(df)

    @property
    def animals(self) -> tuple[str, ...]:
        """Returns all unique animal IDs stored inside the manifest file.

        This provides a tuple of all animal IDs participating in the target project.
        """

        # If animal IDs are stored as integers, converts them to string to support consistent return types.
        return tuple(
            [str(animal) for animal in self._data.select("animal").unique().sort("animal").to_series().to_list()]
        )

    def _get_filtered_sessions(
        self,
        animal: str | int | None = None,
        exclude_incomplete: bool = True,
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
    ) -> tuple[str, ...]:
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
        return self._get_filtered_sessions(
            animal=animal,
            exclude_incomplete=exclude_incomplete,
        )

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

        df = self._data
        df = df.filter(pl.col("session").eq(session))
        return df
