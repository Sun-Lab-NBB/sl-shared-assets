"""This module provides the assets that maintain the Sun lab analysis dataset data hierarchy across all machines used to
process and store the data.
"""

import copy
from pathlib import Path
from dataclasses import field, dataclass

import polars as pl
from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from .session_data import SessionTypes
from .configuration_data import AcquisitionSystems


@dataclass(frozen=True)
class SessionMetadata:
    """Encapsulates the identity metadata for a single data acquisition session.

    This class is used to identify sessions included in an analysis dataset. It provides the minimum information
    necessary to locate and access the session's data within a project's data hierarchy.
    """

    session: str
    """The unique identifier of the session. Session names follow the format 'YYYY-MM-DD-HH-MM-SS-microseconds' and
    encode the session's acquisition timestamp."""
    animal: str
    """The unique identifier of the animal that participated in the session."""


@dataclass()
class DatasetTrackingData:
    """Provides the path to the directory that stores the .yaml and .lock files used by ProcessingTracker instances to
    track the runtime status of the dataset forging and multi-day analysis pipelines.
    """

    tracking_data_path: Path = Path()
    """The path to the root directory that stores the dataset's tracking data."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        Args:
            root_directory_path: The path to the top-level tracking data directory of the dataset's data hierarchy.
        """
        self.tracking_data_path = root_directory_path

    def make_directories(self) -> None:
        """Ensures that the root directory exists, creating it if missing."""
        ensure_directory_exists(self.tracking_data_path)


@dataclass()
class DatasetSessionData:
    """Provides paths and access to the assembled data files for a single session within the dataset.

    Each session in the dataset has its own directory containing the forged data and metadata feather files.
    When loaded, data is memory-mapped as Polars dataframes for efficient access.
    """

    session_path: Path = Path()
    """The path to the session's directory within the dataset hierarchy (dataset/animal/session)."""
    data_path: Path = Path()
    """The path to the data.feather file containing the forged session data."""
    metadata_path: Path = Path()
    """The path to the metadata.feather file containing session metadata."""
    data: pl.DataFrame | None = None
    """The memory-mapped contents of the session's data.feather file as a Polars dataframe."""
    metadata: pl.DataFrame | None = None
    """The memory-mapped contents of the session's metadata.feather file as a Polars dataframe."""

    def resolve_paths(self, session_directory: Path) -> None:
        """Resolves all paths managed by the class instance.

        Args:
            session_directory: The path to the session's directory within the dataset hierarchy.
        """
        self.session_path = session_directory
        self.data_path = session_directory.joinpath("data.feather")
        self.metadata_path = session_directory.joinpath("metadata.feather")

    def make_directories(self) -> None:
        """Ensures that the session directory exists, creating it if missing."""
        ensure_directory_exists(self.session_path)

    def load_data(self) -> None:
        """Loads the session's data by memory-mapping its feather files as Polars dataframes."""
        if self.data_path.exists():
            self.data = pl.read_ipc(source=self.data_path, use_pyarrow=True, memory_map=True, rechunk=True)
        if self.metadata_path.exists():
            self.metadata = pl.read_ipc(source=self.metadata_path, use_pyarrow=True, memory_map=True, rechunk=True)

    def release_data(self) -> None:
        """Releases the memory-mapped dataframes by setting them to None."""
        self.data = None
        self.metadata = None


@dataclass
class DatasetData(YamlConfig):
    """Defines the structure and the metadata of an analysis dataset.

    An analysis dataset aggregates multiple data acquisition sessions of the same type, recorded across different
    animals by the same acquisition system. This class encapsulates the information necessary to access the dataset's
    assembled (forged) data stored on disk and functions as the entry point for all interactions with the dataset.

    Notes:
        Do not initialize this class directly. Instead, use the create() method when creating new datasets or the
        load() method when accessing data for an existing dataset.

        Datasets are created using a pre-filtered set of session + animal pairs, typically obtained through the
        session filtering functionality in sl-forgery. The dataset stores only the assembled data, not raw or
        processed data.
    """

    name: str
    """The unique name of the dataset."""
    project: str
    """The name of the project from which the dataset's sessions originate."""
    session_type: str | SessionTypes
    """The type of data acquisition sessions included in the dataset. All sessions in a dataset must be of the
    same type."""
    acquisition_system: str | AcquisitionSystems
    """The name of the data acquisition system used to acquire all sessions in the dataset."""
    sessions: tuple[SessionMetadata, ...] = field(default_factory=tuple)
    """The collection of session + animal pairs included in the dataset. This should be a pre-filtered set of sessions
    that meet the dataset's inclusion criteria."""
    tracking_data: DatasetTrackingData = field(default_factory=DatasetTrackingData)
    """Defines the dataset's tracking data hierarchy for forging and multi-day analysis pipelines."""
    dataset_data_path: Path = field(default_factory=Path)
    """The path to the dataset_data.yaml file. This path is used by the DatasetData instance to save itself to disk."""
    session_data_cache: dict[str, DatasetSessionData] = field(default_factory=dict, repr=False)
    """Cache for DatasetSessionData instances, keyed by 'animal/session'."""

    def __post_init__(self) -> None:
        """Validates and initializes the dataset configuration."""
        # Ensures enumeration-mapped arguments are stored as proper enumeration types.
        if isinstance(self.session_type, str):
            self.session_type = SessionTypes(self.session_type)
        if isinstance(self.acquisition_system, str):
            self.acquisition_system = AcquisitionSystems(self.acquisition_system)

        # Ensures that the sessions field is a tuple of SessionMetadata instances.
        if self.sessions and not isinstance(self.sessions[0], SessionMetadata):
            # noinspection PyUnresolvedReferences
            self.sessions = tuple(SessionMetadata(session=s["session"], animal=s["animal"]) for s in self.sessions)

        # Ensures tracking data instance is properly initialized.
        if not isinstance(self.tracking_data, DatasetTrackingData):
            self.tracking_data = DatasetTrackingData()

    @classmethod
    def create(
        cls,
        name: str,
        project: str,
        session_type: SessionTypes | str,
        acquisition_system: AcquisitionSystems | str,
        sessions: tuple[SessionMetadata, ...] | set[SessionMetadata],
        datasets_root: Path,
    ) -> DatasetData:
        """Creates a new analysis dataset and initializes its data structure on disk.

        Notes:
            To access the data of an already existing dataset, use the load() method.

        Args:
            name: The unique name for the dataset.
            project: The name of the project from which the dataset's sessions originate.
            session_type: The type of data acquisition sessions included in the dataset.
            acquisition_system: The name of the data acquisition system used to acquire all sessions.
            sessions: The pre-filtered collection of session + animal pairs to include in the dataset.
            datasets_root: The path to the root directory where datasets are stored.

        Returns:
            An initialized DatasetData instance that stores the structure and the metadata of the created dataset.

        Raises:
            ValueError: If the session_type or acquisition_system is invalid, or if no sessions are provided.
            FileExistsError: If a dataset with the same name already exists.
        """
        # Validates inputs
        if isinstance(session_type, str):
            session_type = SessionTypes(session_type)
        if isinstance(acquisition_system, str):
            acquisition_system = AcquisitionSystems(acquisition_system)

        # Converts sessions to tuple if provided as set
        if isinstance(sessions, set):
            sessions = tuple(sessions)

        if not sessions:
            message = "Cannot create a dataset with no sessions. Provide at least one session + animal pair."
            console.error(message=message, error=ValueError)
            raise ValueError(message)  # Fallback for mypy

        # Constructs the dataset root directory path
        dataset_path = datasets_root.joinpath(name)

        # Prevents overwriting existing datasets
        if dataset_path.exists():
            message = (
                f"Unable to create the dataset '{name}'. A dataset with this name already exists at {dataset_path}. "
                f"Use a different name or delete the existing dataset first."
            )
            console.error(message=message, error=FileExistsError)
            raise FileExistsError(message)  # Fallback for mypy

        # Generates the dataset's tracking directory
        tracking_data = DatasetTrackingData()
        tracking_data.resolve_paths(root_directory_path=dataset_path.joinpath("tracking_data"))
        tracking_data.make_directories()

        # Creates animal/session subdirectories and initializes session data instances
        session_data_cache: dict[str, DatasetSessionData] = {}
        for session_meta in sessions:
            session_dir = dataset_path.joinpath(session_meta.animal, session_meta.session)

            session_data = DatasetSessionData()
            session_data.resolve_paths(session_directory=session_dir)
            session_data.make_directories()

            cache_key = f"{session_meta.animal}/{session_meta.session}"
            session_data_cache[cache_key] = session_data

        # Generates the DatasetData instance
        instance = cls(
            name=name,
            project=project,
            session_type=session_type,
            acquisition_system=acquisition_system,
            sessions=sessions,
            tracking_data=tracking_data,
            dataset_data_path=dataset_path.joinpath("dataset_data.yaml"),
            session_data_cache=session_data_cache,
        )

        # Saves the configured instance data to disk
        instance.save()

        return instance

    @classmethod
    def load(cls, dataset_path: Path) -> DatasetData:
        """Loads the target dataset's data from the specified dataset_data.yaml file.

        Notes:
            To create a new dataset, use the create() method.

            This method memory-maps the data.feather and metadata.feather files for each session as Polars dataframes.

        Args:
            dataset_path: The path to the directory where to search for the dataset_data.yaml file. Typically, this
                is the path to the root dataset directory.

        Returns:
            An initialized DatasetData instance that stores the loaded dataset's data.

        Raises:
            FileNotFoundError: If multiple or no 'dataset_data.yaml' file instances are found under the input directory.
        """
        # Locates the dataset_data.yaml file
        dataset_data_files = list(dataset_path.rglob("dataset_data.yaml"))
        if len(dataset_data_files) != 1:
            message = (
                f"Unable to load the target dataset's data. Expected a single dataset_data.yaml file to be located "
                f"under the directory tree specified by the input path: {dataset_path}. Instead, encountered "
                f"{len(dataset_data_files)} candidate files. This indicates that the input path does not point to a "
                f"valid dataset data hierarchy."
            )
            console.error(message=message, error=FileNotFoundError)
            raise FileNotFoundError(message)  # Fallback for mypy

        # Loads the dataset's data from the .yaml file
        dataset_data_path = dataset_data_files.pop()
        instance: DatasetData = cls.from_yaml(file_path=dataset_data_path)

        # Resolves the dataset root directory (parent of the YAML file)
        local_root = dataset_data_path.parent

        # Resolves tracking data paths
        instance.tracking_data.resolve_paths(root_directory_path=local_root.joinpath("tracking_data"))
        instance.dataset_data_path = dataset_data_path

        # Resolves session data paths and loads data
        for session_meta in instance.sessions:
            session_dir = local_root.joinpath(session_meta.animal, session_meta.session)

            session_data = DatasetSessionData()
            session_data.resolve_paths(session_directory=session_dir)
            session_data.load_data()

            cache_key = f"{session_meta.animal}/{session_meta.session}"
            instance.session_data_cache[cache_key] = session_data

        return instance

    def save(self) -> None:
        """Caches the instance's data to the dataset's root directory as a 'dataset_data.yaml' file.

        Notes:
            This method releases all memory-mapped dataframes before saving and resets them to None.
        """
        # Releases all memory-mapped dataframes
        for session_data in self.session_data_cache.values():
            session_data.release_data()

        # Generates a copy to avoid modifying the instance
        origin = copy.deepcopy(self)

        # Resets path fields and cache to None before saving
        origin.tracking_data = None  # type: ignore[assignment]
        origin.dataset_data_path = None  # type: ignore[assignment]
        origin.session_data_cache = None  # type: ignore[assignment]

        # Converts StrEnum instances to strings for YAML serialization
        origin.session_type = str(origin.session_type)
        origin.acquisition_system = str(origin.acquisition_system)

        # Converts SessionMetadata tuples to list of dicts for YAML serialization
        origin.sessions = [  # type: ignore[assignment]
            {"session": s.session, "animal": s.animal} for s in origin.sessions
        ]

        # Saves instance data as a .YAML file
        origin.to_yaml(file_path=self.dataset_data_path)

    @property
    def animals(self) -> tuple[str, ...]:
        """Returns a tuple of unique animal identifiers included in the dataset."""
        return tuple(sorted({s.animal for s in self.sessions}))

    @property
    def session_count(self) -> int:
        """Returns the total number of sessions in the dataset."""
        return len(self.sessions)

    def get_sessions_for_animal(self, animal: str) -> tuple[SessionMetadata, ...]:
        """Returns all sessions for the specified animal.

        Args:
            animal: The unique identifier of the animal.

        Returns:
            A tuple of SessionMetadata instances for the specified animal.
        """
        return tuple(s for s in self.sessions if s.animal == animal)

    def get_session_count_for_animal(self, animal: str) -> int:
        """Returns the number of sessions for the specified animal.

        Args:
            animal: The unique identifier of the animal.

        Returns:
            The number of sessions for the specified animal.
        """
        return len(self.get_sessions_for_animal(animal))

    def get_session_data(self, animal: str, session: str) -> DatasetSessionData:
        """Returns the DatasetSessionData instance for the specified session.

        Args:
            animal: The unique identifier of the animal.
            session: The unique identifier of the session.

        Returns:
            The DatasetSessionData instance containing paths and data for the session's assembled data files.

        Raises:
            ValueError: If the specified session is not found in the dataset.
        """
        cache_key = f"{animal}/{session}"
        if cache_key not in self.session_data_cache:
            message = (
                f"Unable to retrieve session data for animal '{animal}', session '{session}'. "
                f"This session is not included in the dataset."
            )
            console.error(message=message, error=ValueError)
            raise ValueError(message)  # Fallback for mypy

        return self.session_data_cache[cache_key]
