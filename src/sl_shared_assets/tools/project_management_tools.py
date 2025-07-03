"""This module provides tools for managing the data of any Sun lab project. Tools from this module extend the
functionality of SessionData class via a convenient API that allows working with the data of multiple sessions making
up a given project."""

from pathlib import Path
from datetime import datetime

import pytz
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
            "complete",
            "integrity",
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
        df = self._data.select(["animal", "date", "session", "type", "notes"])

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
        return tuple(self._data.select("animal").unique().sort("animal").to_series().to_list())

    @property
    def sessions(self) -> tuple[str, ...]:
        """Returns all session IDs stored inside the manifest file.

        This provides a tuple of all sessions, independent of the participating animal, that were recorded as part
        of the target project.
        """
        return tuple(self._data.select("session").sort("session").to_series().to_list())

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

        # Ensures that the 'animal' argument has the same type as the data inside the DataFrame.
        if self._animal_string:
            animal = str(animal)
        else:
            animal = int(animal)

        if animal not in self.animals:
            message = f"Animal ID '{animal}' not found in manifest. Available animals: {self.animals}"
            console.error(message=message, error=ValueError)

        # Filters by animal ID
        data = self._data.filter(pl.col("animal") == animal)

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

        df = self._data
        df = df.filter(pl.col("session").eq(session))
        return df


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
        "type": [],  # Type of the session (e.g., Experiment, Training, etc.).
        "notes": [],  # The experimenter notes about the session.
        # Determines whether the session data is complete (ran for the intended duration and has all expected data).
        "complete": [],
        # Determines whether the session data integrity has been verified upon transfer to a storage machine.
        "integrity": [],
        "suite2p": [],  # Determines whether the session has been processed with the single-day s2p pipeline.
        # Determines whether the session has been processed with the behavior extraction pipeline.
        "behavior": [],
        "video": [],  # Determines whether the session has been processed with the DeepLabCut pipeline.
        "dataset": [],  # Determines whether the session's data is ready to be integrated into a dataset.
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
        manifest["integrity"].append(tracker.is_complete)

        # If the session is incomplete or unverified, marks all processing steps as FALSE, as automatic processing is
        # disabled for incomplete sessions. If the session is unverified, the case is even more severe, as its data may
        # be corrupted.
        if not manifest["complete"][-1] or not manifest["integrity"][-1]:
            manifest["suite2p"].append(False)
            manifest["dataset"].append(False)
            manifest["behavior"].append(False)
            manifest["video"].append(False)
            continue  # Cycles to the next session

        # Suite2p (single-day) processing status.
        tracker = ProcessingTracker(file_path=session_data.processed_data.suite2p_processing_tracker_path)
        manifest["suite2p"].append(tracker.is_complete)

        # Behavior data processing status.
        tracker = ProcessingTracker(file_path=session_data.processed_data.behavior_processing_tracker_path)
        manifest["behavior"].append(tracker.is_complete)

        # DeepLabCut (video) processing status.
        tracker = ProcessingTracker(file_path=session_data.processed_data.video_processing_tracker_path)
        manifest["video"].append(tracker.is_complete)

        # Tracks whether the session's data is ready for dataset integration. To be considered ready, the data must be
        # successfully processed with all relevant pipelines. Any session currently being processed with any processing
        # pipeline is considered NOT ready.
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
        "notes": pl.String,
        "complete": pl.UInt8,
        "integrity": pl.UInt8,
        "suite2p": pl.UInt8,
        "dataset": pl.UInt8,
        "behavior": pl.UInt8,
        "video": pl.UInt8,
    }
    df = pl.DataFrame(manifest, schema=schema, strict=False)

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

    # Loads session data layout. If configured to do so, also creates the processed data hierarchy
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
        make_processed_data_directory=create_processed_data_directory,
    )

    # If the p53.bin marker exists and the runtime is configured to remove it, removes the marker file. If the runtime
    # is configured to create the marker, aborts the runtime (as the marker already exists).
    if session_data.processed_data.p53_path.exists():
        if remove:
            session_data.processed_data.p53_path.unlink()
            return  # Ends remove runtime

        return  # Ends create runtime

    # If the marker does not exist and the function is called in 'remove' mode, aborts the runtime
    elif remove:
        return  # Ends remove runtime

    # The rest of the runtime deals with determining whether it is safe to create the marker file.
    # Queries the type of the processed session
    session_type = session_data.session_type

    # If the session type is not supported, aborts with an error
    if session_type not in _valid_session_types:
        message = (
            f"Unable to determine the mandatory processing pipelines for session {session_data.session_name} of animal "
            f"{session_data.animal_id} and project {session_data.processed_data}. The type of the session "
            f"{session_type} is not one of the supported session types: {', '.join(_valid_session_types)}."
        )
        console.error(message=message, error=ValueError)

    # Window checking sessions are not designed to be integrated into datasets, so they cannot be marked with p53.bin
    # file. Similarly, any incomplete session is automatically excluded from dataset formation.
    if session_type == "window checking" or not session_data.raw_data.telomere_path.exists():
        return

    # Training sessions collect similar data and share processing pipeline requirements
    if session_type == "lick training" or session_type == "run training":
        # If the session has not been successfully processed with the behavior processing pipeline, aborts without
        # creating the marker file. Also ensures that the video tracking pipeline is not actively running, although it
        # is not required
        behavior_tracker = ProcessingTracker(file_path=session_data.processed_data.behavior_processing_tracker_path)
        video_tracker = ProcessingTracker(file_path=session_data.processed_data.video_processing_tracker_path)
        if not behavior_tracker.is_complete or video_tracker.is_running:
            # Note, training runtimes do not require suite2p processing.
            return

    # Mesoscope experiment sessions require additional processing with suite2p
    if session_type == "mesoscope experiment":
        behavior_tracker = ProcessingTracker(file_path=session_data.processed_data.behavior_processing_tracker_path)
        suite2p_tracker = ProcessingTracker(file_path=session_data.processed_data.suite2p_processing_tracker_path)
        video_tracker = ProcessingTracker(file_path=session_data.processed_data.video_processing_tracker_path)

        # Similar to above, if the session is not processed with the behavior pipeline or the suite2p pipeline, aborts
        # without creating the marker file. Video tracker is not required for p53 marker creation, but the video
        # tracking pipeline must not be actively running.
        if not behavior_tracker.is_complete or not suite2p_tracker.is_complete or video_tracker.is_running:
            return

    # If the runtime reached this point, the session is eligible for dataset integration. Creates the p53.bin marker
    # file, preventing the session from being processed again as long as the marker exists.
    session_data.processed_data.p53_path.touch()
