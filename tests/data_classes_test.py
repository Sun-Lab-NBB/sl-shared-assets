from pathlib import Path

import pytest
import appdirs

from sl_shared_assets import (
    AcquisitionSystems,
    MesoscopeExperimentState,
    MesoscopeExperimentTrial,
    MesoscopeExperimentConfiguration,
    MesoscopeFileSystem,
    MesoscopeCameras,
    MesoscopeMicroControllers,
    MesoscopeExternalAssets,
    MesoscopeSystemConfiguration,
    MesoscopeGoogleSheets,
    SessionTypes,
    RawData,
    ProcessedData,
    TrackingData,
    SessionData,
    SessionLock,
    get_working_directory,
    get_system_configuration_data,
    ProcessingTracker,
    TrackerFiles,
    ProcessingStatus,
    ProcessingPipelines,
    get_google_credentials_path,
    get_server_configuration,
    ServerConfiguration,
)

from sl_shared_assets.data_classes.configuration_data import (
    set_working_directory,
    create_system_configuration_file,
    set_google_credentials_path,
    create_server_configuration_file,
)


@pytest.fixture
def sample_mesoscope_config() -> MesoscopeSystemConfiguration:
    """Creates a sample MesoscopeSystemConfiguration for testing.

    Returns:
        A configured MesoscopeSystemConfiguration instance.
    """
    config = MesoscopeSystemConfiguration()
    config.filesystem.root_directory = Path("/data/projects")
    config.filesystem.server_directory = Path("/mnt/server/projects")
    config.filesystem.nas_directory = Path("/mnt/nas/backup")
    config.filesystem.mesoscope_directory = Path("/mnt/mesoscope/data")
    config.sheets.surgery_sheet_id = "abc123"
    config.sheets.water_log_sheet_id = "xyz789"
    return config


@pytest.fixture
def sample_experiment_config() -> MesoscopeExperimentConfiguration:
    """Creates a sample MesoscopeExperimentConfiguration for testing.

    Returns:
        A configured MesoscopeExperimentConfiguration instance.
    """
    state = MesoscopeExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        initial_guided_trials=10,
        recovery_failed_trial_threshold=5,
        recovery_guided_trials=3,
    )

    trial = MesoscopeExperimentTrial(
        cue_sequence=[1, 2, 3],
        trial_length_cm=200.0,
        trial_reward_size_ul=5.0,
        reward_zone_start_cm=180.0,
        reward_zone_end_cm=200.0,
        guidance_trigger_location_cm=190.0,
    )

    config = MesoscopeExperimentConfiguration(
        cue_map={1: 50.0, 2: 75.0, 3: 50.0},
        cue_offset_cm=10.0,
        unity_scene_name="TestScene",
        experiment_states={"state1": state},
        trial_structures={"trial1": trial},
    )

    return config


@pytest.fixture
def clean_working_directory(tmp_path, monkeypatch):
    """Sets up a clean temporary working directory for testing.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    Returns:
        Path to the temporary working directory.
    """
    # Patches appdirs to use temporary directory
    app_dir = tmp_path / "app_data"
    app_dir.mkdir()
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    working_dir = tmp_path / "working_directory"
    working_dir.mkdir()

    return working_dir


@pytest.fixture
def sample_session_hierarchy(tmp_path) -> Path:
    """Creates a sample session directory hierarchy for testing.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Returns:
        Path to the root session directory.
    """
    # Creates the session hierarchy: root/project/animal/session/raw_data
    root = tmp_path / "data"
    session_path = root / "test_project" / "test_animal" / "2024-01-15-12-30-45-123456" / "raw_data"
    session_path.mkdir(parents=True)

    return session_path.parent


# Tests for AcquisitionSystems enumeration


def test_acquisition_systems_mesoscope_vr():
    """Verifies the MESOSCOPE_VR acquisition system enumeration value.

    This test ensures the enumeration contains the expected string value.
    """
    assert AcquisitionSystems.MESOSCOPE_VR == "mesoscope"
    assert str(AcquisitionSystems.MESOSCOPE_VR) == "mesoscope"


def test_acquisition_systems_is_string_enum():
    """Verifies that AcquisitionSystems inherits from StrEnum.

    This test ensures the enumeration members behave as strings.
    """
    assert isinstance(AcquisitionSystems.MESOSCOPE_VR, str)


# Tests for SessionTypes enumeration


def test_session_types_values():
    """Verifies all SessionTypes enumeration values.

    This test ensures the enumeration contains all expected session types.
    """
    assert SessionTypes.LICK_TRAINING == "lick training"
    assert SessionTypes.RUN_TRAINING == "run training"
    assert SessionTypes.MESOSCOPE_EXPERIMENT == "mesoscope experiment"
    assert SessionTypes.WINDOW_CHECKING == "window checking"


def test_session_types_is_string_enum():
    """Verifies that SessionTypes inherits from StrEnum.

    This test ensures the enumeration members behave as strings.
    """
    assert isinstance(SessionTypes.LICK_TRAINING, str)
    assert isinstance(SessionTypes.RUN_TRAINING, str)
    assert isinstance(SessionTypes.MESOSCOPE_EXPERIMENT, str)
    assert isinstance(SessionTypes.WINDOW_CHECKING, str)


# Tests for RawData dataclass


def test_raw_data_default_initialization():
    """Verifies default initialization of RawData.

    This test ensures all path fields have default Path() values.
    """
    raw_data = RawData()

    assert raw_data.raw_data_path == Path()
    assert raw_data.camera_data_path == Path()
    assert raw_data.mesoscope_data_path == Path()
    assert raw_data.behavior_data_path == Path()
    assert raw_data.zaber_positions_path == Path()
    assert raw_data.session_descriptor_path == Path()


def test_raw_data_resolve_paths(tmp_path):
    """Verifies that resolve_paths correctly generates all data paths.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures all paths are properly resolved from the root directory.
    """
    raw_data = RawData()
    root_path = tmp_path / "raw_data"

    raw_data.resolve_paths(root_directory_path=root_path)

    assert raw_data.raw_data_path == root_path
    assert raw_data.camera_data_path == root_path / "camera_data"
    assert raw_data.mesoscope_data_path == root_path / "mesoscope_data"
    assert raw_data.behavior_data_path == root_path / "behavior_data"
    assert raw_data.zaber_positions_path == root_path / "zaber_positions.yaml"
    assert raw_data.session_descriptor_path == root_path / "session_descriptor.yaml"
    assert raw_data.session_data_path == root_path / "session_data.yaml"
    assert raw_data.nk_path == root_path / "nk.bin"


def test_raw_data_make_directories(tmp_path):
    """Verifies that make_directories creates all required subdirectories.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the directory creation method works correctly.
    """
    raw_data = RawData()
    root_path = tmp_path / "raw_data"

    raw_data.resolve_paths(root_directory_path=root_path)
    raw_data.make_directories()

    assert root_path.exists()
    assert (root_path / "camera_data").exists()
    assert (root_path / "mesoscope_data").exists()
    assert (root_path / "behavior_data").exists()


# Tests for ProcessedData dataclass


def test_processed_data_default_initialization():
    """Verifies default initialization of ProcessedData.

    This test ensures all path fields have default Path() values.
    """
    processed_data = ProcessedData()

    assert processed_data.processed_data_path == Path()
    assert processed_data.camera_data_path == Path()
    assert processed_data.mesoscope_data_path == Path()
    assert processed_data.behavior_data_path == Path()


def test_processed_data_resolve_paths(tmp_path):
    """Verifies that resolve_paths correctly generates all data paths.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures all paths are properly resolved from the root directory.
    """
    processed_data = ProcessedData()
    root_path = tmp_path / "processed_data"

    processed_data.resolve_paths(root_directory_path=root_path)

    assert processed_data.processed_data_path == root_path
    assert processed_data.camera_data_path == root_path / "camera_data"
    assert processed_data.mesoscope_data_path == root_path / "mesoscope_data"
    assert processed_data.behavior_data_path == root_path / "behavior_data"


def test_processed_data_make_directories(tmp_path):
    """Verifies that make_directories creates all required subdirectories.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the directory creation method works correctly.
    """
    processed_data = ProcessedData()
    root_path = tmp_path / "processed_data"

    processed_data.resolve_paths(root_directory_path=root_path)
    processed_data.make_directories()

    assert root_path.exists()
    assert (root_path / "camera_data").exists()
    assert (root_path / "behavior_data").exists()


# Tests for TrackingData dataclass


def test_tracking_data_default_initialization():
    """Verifies default initialization of TrackingData.

    This test ensures all path fields have default Path() values.
    """
    tracking_data = TrackingData()

    assert tracking_data.tracking_data_path == Path()
    assert tracking_data.session_lock_path == Path()


def test_tracking_data_resolve_paths(tmp_path):
    """Verifies that resolve_paths correctly generates all data paths.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures all paths are properly resolved from the root directory.
    """
    tracking_data = TrackingData()
    root_path = tmp_path / "tracking_data"

    tracking_data.resolve_paths(root_directory_path=root_path)

    assert tracking_data.tracking_data_path == root_path
    assert tracking_data.session_lock_path == root_path / "session_lock.yaml"


def test_tracking_data_make_directories(tmp_path):
    """Verifies that make_directories creates the tracking directory.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the directory creation method works correctly.
    """
    tracking_data = TrackingData()
    root_path = tmp_path / "tracking_data"

    tracking_data.resolve_paths(root_directory_path=root_path)
    tracking_data.make_directories()

    assert root_path.exists()


# Tests for SessionData dataclass


def test_session_data_post_init_creates_nested_instances():
    """Verifies that __post_init__ ensures nested dataclass instances exist.

    This test ensures proper initialization of nested RawData, ProcessedData, and TrackingData.
    """
    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
    )

    assert isinstance(session_data.raw_data, RawData)
    assert isinstance(session_data.processed_data, ProcessedData)
    assert isinstance(session_data.tracking_data, TrackingData)


def test_session_data_create_requires_valid_session_type(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() raises ValueError for invalid session types.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures only valid SessionTypes are accepted.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory BEFORE creating directories
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    project_dir = clean_working_directory / "test_project"
    project_dir.mkdir(parents=True)

    with pytest.raises(ValueError):
        SessionData.create(
            project_name="test_project",
            animal_id="test_animal",
            session_type="invalid_session_type",
            python_version="3.11.13",
            sl_experiment_version="3.0.0",
        )


def test_session_data_create_generates_session_directory(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() generates the complete session directory structure.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures all session directories are created correctly.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory BEFORE creating directories
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    project_dir = clean_working_directory / "test_project"
    project_dir.mkdir(parents=True)

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies directory structure
    assert session_data.raw_data.raw_data_path.exists()
    assert session_data.raw_data.camera_data_path.exists()
    assert session_data.raw_data.mesoscope_data_path.exists()
    assert session_data.raw_data.behavior_data_path.exists()


def test_session_data_create_saves_session_data_yaml(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() saves the session_data.yaml file.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the session metadata file is created.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory BEFORE creating directories
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    project_dir = clean_working_directory / "test_project"
    project_dir.mkdir(parents=True)

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    assert session_data.raw_data.session_data_path.exists()
    content = session_data.raw_data.session_data_path.read_text()
    assert "project_name: test_project" in content
    assert "animal_id: test_animal" in content


def test_session_data_create_marks_with_nk_file(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() marks new sessions with the nk.bin file.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures new sessions are properly marked for initialization tracking.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory BEFORE creating directories
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    project_dir = clean_working_directory / "test_project"
    project_dir.mkdir(parents=True)

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.RUN_TRAINING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    assert session_data.raw_data.nk_path.exists()


def test_session_data_load_finds_session_data_yaml(sample_session_hierarchy):
    """Verifies that load() successfully finds and loads session_data.yaml.

    Args:
        sample_session_hierarchy: Fixture providing a sample session directory structure.

    This test ensures the load method can locate the session data file.
    """
    # Creates a session_data.yaml file
    raw_data_path = sample_session_hierarchy / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)

    session_data_path = raw_data_path / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: lick training
acquisition_system: mesoscope
experiment_name: null
python_version: 3.11.13
sl_experiment_version: 3.0.0
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    assert loaded_session.project_name == "test_project"
    assert loaded_session.animal_id == "test_animal"
    assert loaded_session.session_type == "lick training"


def test_session_data_load_raises_error_no_session_data_file(tmp_path):
    """Verifies that load() raises FileNotFoundError when no session_data.yaml exists.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures proper error handling for missing session data files.
    """
    empty_dir = tmp_path / "empty_session"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=empty_dir)


def test_session_data_load_raises_error_multiple_session_data_files(tmp_path):
    """Verifies that load() raises FileNotFoundError when multiple session_data.yaml files exist.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures proper error handling for ambiguous session hierarchies.
    """
    session_dir = tmp_path / "ambiguous_session"
    session_dir.mkdir()

    # Creates multiple session_data.yaml files
    (session_dir / "session_data.yaml").write_text("content1")
    subdir = session_dir / "subdir"
    subdir.mkdir()
    (subdir / "session_data.yaml").write_text("content2")

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=session_dir)


def test_session_data_load_resolves_all_paths(sample_session_hierarchy):
    """Verifies that load() resolves all RawData, ProcessedData, and TrackingData paths.

    Args:
        sample_session_hierarchy: Fixture providing a sample session directory structure.

    This test ensures all session data paths are properly initialized after loading.
    """
    raw_data_path = sample_session_hierarchy / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)

    session_data_path = raw_data_path / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: mesoscope experiment
acquisition_system: mesoscope
experiment_name: test_experiment
python_version: 3.11.13
sl_experiment_version: 3.0.0
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    # Verifies RawData paths
    assert loaded_session.raw_data.raw_data_path.name == "raw_data"
    assert loaded_session.raw_data.camera_data_path.name == "camera_data"

    # Verifies ProcessedData paths
    assert loaded_session.processed_data.processed_data_path.name == "processed_data"

    # Verifies TrackingData paths
    assert loaded_session.tracking_data.tracking_data_path.name == "tracking_data"


def test_session_data_load_creates_processed_and_tracking_directories(sample_session_hierarchy):
    """Verifies that load() creates processed_data and tracking_data directories.

    Args:
        sample_session_hierarchy: Fixture providing a sample session directory structure.

    This test ensures missing processing directories are created during load() runtime.
    """
    raw_data_path = sample_session_hierarchy / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)

    session_data_path = raw_data_path / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: window checking
acquisition_system: mesoscope
experiment_name: null
python_version: 3.11.13
sl_experiment_version: 3.0.0
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    assert loaded_session.processed_data.processed_data_path.exists()
    assert loaded_session.tracking_data.tracking_data_path.exists()


def test_session_data_runtime_initialized_removes_nk_file(sample_session_hierarchy):
    """Verifies that runtime_initialized() removes the nk.bin marker file.

    Args:
        sample_session_hierarchy: Fixture providing a sample session directory structure.

    This test ensures the initialization marker is properly removed.
    """
    raw_data_path = sample_session_hierarchy / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)

    session_data_path = raw_data_path / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: lick training
acquisition_system: mesoscope
experiment_name: null
python_version: 3.11.13
sl_experiment_version: 3.0.0
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    # Creates the nk.bin file
    loaded_session.raw_data.nk_path.touch()
    assert loaded_session.raw_data.nk_path.exists()

    # Calls runtime_initialized
    loaded_session.runtime_initialized()

    assert not loaded_session.raw_data.nk_path.exists()


def test_session_data_save_converts_enums_to_strings(sample_session_hierarchy):
    """Verifies that save() converts SessionTypes and AcquisitionSystems to strings.

    Args:
        sample_session_hierarchy: Fixture providing a sample session directory structure.

    This test ensures enum values are properly serialized in YAML.
    """
    raw_data_path = sample_session_hierarchy / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)

    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    session_data.raw_data.resolve_paths(root_directory_path=raw_data_path)
    session_data.save()

    content = session_data.raw_data.session_data_path.read_text()
    assert "session_type: mesoscope experiment" in content
    assert "acquisition_system: mesoscope" in content


def test_session_data_save_does_not_include_path_objects(sample_session_hierarchy):
    """Verifies that save() excludes path objects from the saved YAML.

    Args:
        sample_session_hierarchy: Fixture providing a sample session directory structure.

    This test ensures only metadata is saved, not path instances.
    """
    raw_data_path = sample_session_hierarchy / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)

    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.RUN_TRAINING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    session_data.raw_data.resolve_paths(root_directory_path=raw_data_path)
    session_data.save()

    content = session_data.raw_data.session_data_path.read_text()
    assert "raw_data: null" in content
    assert "processed_data: null" in content
    assert "tracking_data: null" in content


# Tests for SessionLock dataclass


def test_session_lock_initialization(tmp_path):
    """Verifies basic initialization of SessionLock.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the lock file path is properly initialized.
    """
    lock_file = tmp_path / "session_lock.yaml"
    session_lock = SessionLock(file_path=lock_file)

    assert session_lock.file_path == lock_file
    assert session_lock._manager_id == -1
    assert session_lock.lock_path == str(lock_file.with_suffix(".yaml.lock"))


def test_session_lock_acquire_creates_lock_file(tmp_path):
    """Verifies that acquire() creates the lock file with the correct manager ID.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the lock acquisition mechanism works correctly.
    """
    lock_file = tmp_path / "session_lock.yaml"
    session_lock = SessionLock(file_path=lock_file)

    manager_id = 12345
    session_lock.acquire(manager_id=manager_id)

    assert lock_file.exists()
    content = lock_file.read_text()
    assert f"_manager_id: {manager_id}" in content


def test_session_lock_acquire_raises_error_if_locked_by_another_manager(tmp_path):
    """Verifies that acquire() raises PermissionError when locked by another manager.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures exclusive lock ownership is enforced.
    Note: This test creates separate SessionLock instances to simulate different processes.
    """
    lock_file = tmp_path / "session_lock.yaml"

    # The first manager acquires lock (simulates the first process)
    session_lock_1 = SessionLock(file_path=lock_file)
    session_lock_1.acquire(manager_id=100)

    # The second manager attempts to acquire lock (simulates the second process)
    session_lock_2 = SessionLock(file_path=lock_file)
    with pytest.raises(PermissionError):
        session_lock_2.acquire(manager_id=200)


def test_session_lock_acquire_allows_reacquisition_by_same_manager(tmp_path):
    """Verifies that acquire() allows the same manager to reacquire the lock.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures that calling the lock acquisition method multiple times does not do anything for the owner.
    Note: This test creates separate SessionLock instances to simulate the same process reacquiring the lock after
    reloading state.
    """
    lock_file = tmp_path / "session_lock.yaml"

    # First acquisition
    session_lock_1 = SessionLock(file_path=lock_file)
    manager_id = 12345
    session_lock_1.acquire(manager_id=manager_id)

    # The same manager reacquires lock (simulates the same process reloading state)
    session_lock_2 = SessionLock(file_path=lock_file)
    session_lock_2.acquire(manager_id=manager_id)  # Should not raise error

    # Verifies the lock is still held by the same manager
    session_lock_2._load_state()
    assert session_lock_2._manager_id == manager_id


def test_session_lock_release_removes_lock_ownership(tmp_path):
    """Verifies that release() removes lock ownership.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the lock release mechanism works correctly.
    """
    lock_file = tmp_path / "session_lock.yaml"
    session_lock = SessionLock(file_path=lock_file)

    manager_id = 12345
    session_lock.acquire(manager_id=manager_id)
    session_lock.release(manager_id=manager_id)

    # Reloads state to verify
    session_lock._load_state()
    assert session_lock._manager_id == -1


def test_session_lock_release_raises_error_if_not_owner(tmp_path):
    """Verifies that release() raises PermissionError when called by a non-owner.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures only the lock owner can release the lock.
    Note: This test creates separate SessionLock instances to simulate different processes.
    """
    lock_file = tmp_path / "session_lock.yaml"

    # First manager acquires a lock
    session_lock_1 = SessionLock(file_path=lock_file)
    session_lock_1.acquire(manager_id=100)

    # Different manager attempts to release a lock
    session_lock_2 = SessionLock(file_path=lock_file)
    with pytest.raises(PermissionError):
        session_lock_2.release(manager_id=200)


def test_session_lock_force_release_clears_any_lock(tmp_path):
    """Verifies that force_release() clears the lock regardless of ownership.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the emergency lock release mechanism works correctly.
    """
    lock_file = tmp_path / "session_lock.yaml"

    # Manager acquires lock
    session_lock_1 = SessionLock(file_path=lock_file)
    session_lock_1.acquire(manager_id=12345)

    # Force release from any process (simulated by different instance)
    session_lock_2 = SessionLock(file_path=lock_file)
    session_lock_2.force_release()

    # Reloads state to verify
    session_lock_2._load_state()
    assert session_lock_2._manager_id == -1


def test_session_lock_check_owner_passes_for_correct_owner(tmp_path):
    """Verifies that check_owner() passes when called by the lock owner.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures ownership verification works correctly for valid owners.
    Note: This test creates separate SessionLock instances to simulate a process
    checking its ownership after reloading state.
    """
    lock_file = tmp_path / "session_lock.yaml"

    # Manager acquires lock
    session_lock_1 = SessionLock(file_path=lock_file)
    manager_id = 12345
    session_lock_1.acquire(manager_id=manager_id)

    # The same manager checks ownership (simulated by different instance loading state)
    session_lock_2 = SessionLock(file_path=lock_file)
    session_lock_2.check_owner(manager_id=manager_id)  # Should not raise error


def test_session_lock_check_owner_raises_error_for_wrong_owner(tmp_path):
    """Verifies that check_owner() raises ValueError when called by a non-owner.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures ownership verification rejects non-owners.
    Note: This test creates separate SessionLock instances to simulate different processes.
    """
    lock_file = tmp_path / "session_lock.yaml"

    # First manager acquires a lock
    session_lock_1 = SessionLock(file_path=lock_file)
    session_lock_1.acquire(manager_id=100)

    # Different manager checks ownership
    session_lock_2 = SessionLock(file_path=lock_file)
    with pytest.raises(ValueError):
        session_lock_2.check_owner(manager_id=200)


# Tests for MesoscopeExperimentState dataclass


def test_mesoscope_experiment_state_initialization():
    """Verifies basic initialization of MesoscopeExperimentState.

    This test ensures all fields are properly assigned during initialization.
    """
    state = MesoscopeExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        initial_guided_trials=10,
        recovery_failed_trial_threshold=5,
        recovery_guided_trials=3,
    )

    assert state.experiment_state_code == 1
    assert state.system_state_code == 0
    assert state.state_duration_s == 600.0
    assert state.initial_guided_trials == 10
    assert state.recovery_failed_trial_threshold == 5
    assert state.recovery_guided_trials == 3


def test_mesoscope_experiment_state_types():
    """Verifies the data types of MesoscopeExperimentState fields.

    This test ensures each field has the expected type.
    """
    state = MesoscopeExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        initial_guided_trials=10,
        recovery_failed_trial_threshold=5,
        recovery_guided_trials=3,
    )

    assert isinstance(state.experiment_state_code, int)
    assert isinstance(state.system_state_code, int)
    assert isinstance(state.state_duration_s, float)
    assert isinstance(state.initial_guided_trials, int)
    assert isinstance(state.recovery_failed_trial_threshold, int)
    assert isinstance(state.recovery_guided_trials, int)


# Tests for MesoscopeExperimentTrial dataclass


def test_mesoscope_experiment_trial_initialization():
    """Verifies basic initialization of MesoscopeExperimentTrial.

    This test ensures all fields are properly assigned during initialization.
    """
    trial = MesoscopeExperimentTrial(
        cue_sequence=[1, 2, 3, 4],
        trial_length_cm=200.0,
        trial_reward_size_ul=5.0,
        reward_zone_start_cm=180.0,
        reward_zone_end_cm=200.0,
        guidance_trigger_location_cm=190.0,
    )

    assert trial.cue_sequence == [1, 2, 3, 4]
    assert trial.trial_length_cm == 200.0
    assert trial.trial_reward_size_ul == 5.0
    assert trial.reward_zone_start_cm == 180.0
    assert trial.reward_zone_end_cm == 200.0
    assert trial.guidance_trigger_location_cm == 190.0


def test_mesoscope_experiment_trial_types():
    """Verifies the data types of MesoscopeExperimentTrial fields.

    This test ensures each field has the expected type.
    """
    trial = MesoscopeExperimentTrial(
        cue_sequence=[1, 2, 3],
        trial_length_cm=200.0,
        trial_reward_size_ul=5.0,
        reward_zone_start_cm=180.0,
        reward_zone_end_cm=200.0,
        guidance_trigger_location_cm=190.0,
    )

    assert isinstance(trial.cue_sequence, list)
    assert all(isinstance(cue, int) for cue in trial.cue_sequence)
    assert isinstance(trial.trial_length_cm, float)
    assert isinstance(trial.trial_reward_size_ul, float)
    assert isinstance(trial.reward_zone_start_cm, float)
    assert isinstance(trial.reward_zone_end_cm, float)
    assert isinstance(trial.guidance_trigger_location_cm, float)


# Tests for MesoscopeFileSystem dataclass


def test_mesoscope_filesystem_default_initialization():
    """Verifies default initialization of MesoscopeFileSystem.

    This test ensures all fields have default Path() values.
    """
    filesystem = MesoscopeFileSystem()

    assert filesystem.root_directory == Path()
    assert filesystem.server_directory == Path()
    assert filesystem.nas_directory == Path()
    assert filesystem.mesoscope_directory == Path()


def test_mesoscope_filesystem_custom_initialization():
    """Verifies custom initialization of MesoscopeFileSystem.

    This test ensures all fields accept custom Path values.
    """
    filesystem = MesoscopeFileSystem(
        root_directory=Path("/data/root"),
        server_directory=Path("/mnt/server"),
        nas_directory=Path("/mnt/nas"),
        mesoscope_directory=Path("/mnt/mesoscope"),
    )

    assert filesystem.root_directory == Path("/data/root")
    assert filesystem.server_directory == Path("/mnt/server")
    assert filesystem.nas_directory == Path("/mnt/nas")
    assert filesystem.mesoscope_directory == Path("/mnt/mesoscope")


# Tests for MesoscopeGoogleSheets dataclass


def test_mesoscope_google_sheets_default_initialization():
    """Verifies default initialization of MesoscopeGoogleSheets.

    This test ensures all fields have appropriate default values.
    """
    sheets = MesoscopeGoogleSheets()

    assert sheets.surgery_sheet_id == ""
    assert sheets.water_log_sheet_id == ""


def test_mesoscope_google_sheets_custom_initialization():
    """Verifies custom initialization of MesoscopeGoogleSheets.

    This test ensures all fields accept custom values.
    """
    sheets = MesoscopeGoogleSheets(
        surgery_sheet_id="abc123xyz",
        water_log_sheet_id="def456uvw",
    )

    assert sheets.surgery_sheet_id == "abc123xyz"
    assert sheets.water_log_sheet_id == "def456uvw"


# Tests for MesoscopeCameras dataclass


def test_mesoscope_cameras_default_initialization():
    """Verifies default initialization of MesoscopeCameras.

    This test ensures all fields have appropriate default values.
    """
    cameras = MesoscopeCameras()

    assert cameras.face_camera_index == 0
    assert cameras.body_camera_index == 1
    assert cameras.face_camera_quantization == 15
    assert cameras.face_camera_preset == 5
    assert cameras.body_camera_quantization == 15
    assert cameras.body_camera_preset == 5


def test_mesoscope_cameras_custom_initialization():
    """Verifies custom initialization of MesoscopeCameras.

    This test ensures all fields accept custom values.
    """
    cameras = MesoscopeCameras(
        face_camera_index=2,
        body_camera_index=3,
        face_camera_quantization=18,
        face_camera_preset=7,
        body_camera_quantization=20,
        body_camera_preset=8,
    )

    assert cameras.face_camera_index == 2
    assert cameras.body_camera_index == 3
    assert cameras.face_camera_quantization == 18
    assert cameras.face_camera_preset == 7
    assert cameras.body_camera_quantization == 20
    assert cameras.body_camera_preset == 8


# Tests for MesoscopeMicroControllers dataclass


def test_mesoscope_microcontrollers_default_initialization():
    """Verifies default initialization of MesoscopeMicroControllers.

    This test ensures all fields have appropriate default values.
    """
    mcu = MesoscopeMicroControllers()

    assert mcu.actor_port == "/dev/ttyACM0"
    assert mcu.sensor_port == "/dev/ttyACM1"
    assert mcu.encoder_port == "/dev/ttyACM2"
    assert mcu.wheel_diameter_cm == 15.0333
    assert mcu.lick_threshold_adc == 600
    assert len(mcu.valve_calibration_data) == 4


def test_mesoscope_microcontrollers_valve_calibration_tuple():
    """Verifies valve_calibration_data is stored as a tuple of tuples.

    This test ensures the valve calibration data has the correct structure.
    """
    mcu = MesoscopeMicroControllers()

    assert isinstance(mcu.valve_calibration_data, tuple)
    assert all(isinstance(item, tuple) for item in mcu.valve_calibration_data)
    assert all(len(item) == 2 for item in mcu.valve_calibration_data)
    assert all(
        isinstance(item[0], (int, float)) and isinstance(item[1], (int, float)) for item in mcu.valve_calibration_data
    )


def test_mesoscope_microcontrollers_custom_valve_calibration():
    """Verifies custom valve_calibration_data initialization.

    This test ensures custom calibration data can be provided during initialization.
    """
    custom_calibration = ((10000, 0.5), (20000, 1.5), (30000, 3.0))
    mcu = MesoscopeMicroControllers(valve_calibration_data=custom_calibration)

    assert mcu.valve_calibration_data == custom_calibration
    assert len(mcu.valve_calibration_data) == 3


# Tests for MesoscopeExternalAssets dataclass


def test_mesoscope_external_assets_default_initialization():
    """Verifies default initialization of MesoscopeExternalAssets.

    This test ensures all fields have appropriate default values.
    """
    assets = MesoscopeExternalAssets()

    assert assets.headbar_port == "/dev/ttyUSB0"
    assert assets.lickport_port == "/dev/ttyUSB1"
    assert assets.wheel_port == "/dev/ttyUSB2"
    assert assets.unity_ip == "127.0.0.1"
    assert assets.unity_port == 1883


def test_mesoscope_external_assets_custom_initialization():
    """Verifies custom initialization of MesoscopeExternalAssets.

    This test ensures all fields accept custom values.
    """
    assets = MesoscopeExternalAssets(
        headbar_port="/dev/ttyUSB3",
        lickport_port="/dev/ttyUSB4",
        wheel_port="/dev/ttyUSB5",
        unity_ip="192.168.1.100",
        unity_port=1884,
    )

    assert assets.headbar_port == "/dev/ttyUSB3"
    assert assets.lickport_port == "/dev/ttyUSB4"
    assert assets.wheel_port == "/dev/ttyUSB5"
    assert assets.unity_ip == "192.168.1.100"
    assert assets.unity_port == 1884


# Tests for MesoscopeSystemConfiguration dataclass


def test_mesoscope_system_configuration_default_initialization():
    """Verifies default initialization of MesoscopeSystemConfiguration.

    This test ensures the class initializes with default nested dataclasses.
    """
    config = MesoscopeSystemConfiguration()

    assert config.name == str(AcquisitionSystems.MESOSCOPE_VR)
    assert isinstance(config.filesystem, MesoscopeFileSystem)
    assert isinstance(config.sheets, MesoscopeGoogleSheets)
    assert isinstance(config.cameras, MesoscopeCameras)
    assert isinstance(config.microcontrollers, MesoscopeMicroControllers)
    assert isinstance(config.assets, MesoscopeExternalAssets)


def test_mesoscope_system_configuration_post_init_path_conversion():
    """Verifies that __post_init__ converts string paths to Path objects.

    This test ensures path fields are properly converted during initialization.
    """
    config = MesoscopeSystemConfiguration()
    # noinspection PyTypeChecker
    config.filesystem.root_directory = "/data/projects"
    # noinspection PyTypeChecker
    config.filesystem.server_directory = "/mnt/server"

    # Simulates re-initialization (would happen during YAML loading)
    config.__post_init__()

    assert isinstance(config.filesystem.root_directory, Path)
    assert isinstance(config.filesystem.server_directory, Path)


def test_mesoscope_system_configuration_post_init_valve_calibration_dict():
    """Verifies that __post_init__ converts valve_calibration_data dict to tuple.

    This test ensures valve calibration data is converted from dict to tuple format.
    """
    config = MesoscopeSystemConfiguration()
    config.microcontrollers.valve_calibration_data = {
        10000: 0.5,
        20000: 1.5,
        30000: 3.0,
    }

    config.__post_init__()

    assert isinstance(config.microcontrollers.valve_calibration_data, tuple)
    assert len(config.microcontrollers.valve_calibration_data) == 3
    assert (10000, 0.5) in config.microcontrollers.valve_calibration_data


def test_mesoscope_system_configuration_post_init_invalid_valve_calibration():
    """Verifies that __post_init__ raises TypeError for invalid valve calibration data.

    This test ensures improper calibration data structure is detected and rejected.
    """
    config = MesoscopeSystemConfiguration()
    # noinspection PyTypeChecker
    config.microcontrollers.valve_calibration_data = ((10000, "invalid"), (20000, 1.5))

    with pytest.raises(TypeError):
        config.__post_init__()


def test_mesoscope_system_configuration_save_yaml(tmp_path, sample_mesoscope_config):
    """Verifies that save() correctly writes configuration to YAML file.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        sample_mesoscope_config: Fixture providing a sample configuration.

    This test ensures configuration data is properly saved as YAML.
    """
    yaml_path = tmp_path / "test_config.yaml"
    sample_mesoscope_config.save(path=yaml_path)

    assert yaml_path.exists()
    assert yaml_path.stat().st_size > 0

    # Verifies file contains YAML content
    content = yaml_path.read_text()
    assert "name:" in content
    assert "filesystem:" in content
    assert "mesoscope" in content


def test_mesoscope_system_configuration_save_converts_paths(tmp_path, sample_mesoscope_config):
    """Verifies that save() converts Path objects to strings in YAML.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        sample_mesoscope_config: Fixture providing a sample configuration.

    This test ensures Path objects are serialized as strings in the YAML file.
    """
    yaml_path = tmp_path / "test_config.yaml"
    sample_mesoscope_config.save(path=yaml_path)

    content = yaml_path.read_text()

    # Verifies paths are stored as strings (not Path objects)
    assert "/data/projects" in content
    assert "/mnt/server/projects" in content
    assert "Path(" not in content


def test_mesoscope_system_configuration_save_converts_valve_calibration(tmp_path, sample_mesoscope_config):
    """Verifies that save() converts valve calibration tuple to dict in YAML.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        sample_mesoscope_config: Fixture providing a sample configuration.

    This test ensures valve calibration data is serialized as a dictionary.
    """
    yaml_path = tmp_path / "test_config.yaml"
    sample_mesoscope_config.save(path=yaml_path)

    content = yaml_path.read_text()

    # Verifies valve calibration is stored as key-value pairs
    assert "15000:" in content or "15000.0:" in content
    assert "valve_calibration_data:" in content


def test_mesoscope_system_configuration_save_does_not_modify_original(tmp_path, sample_mesoscope_config):
    """Verifies that save() does not modify the original configuration instance.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        sample_mesoscope_config: Fixture providing a sample configuration.

    This test ensures the original instance remains unchanged after saving.
    """
    original_root = sample_mesoscope_config.filesystem.root_directory
    original_valve_data = sample_mesoscope_config.microcontrollers.valve_calibration_data

    yaml_path = tmp_path / "test_config.yaml"
    sample_mesoscope_config.save(path=yaml_path)

    # Verifies original data is unchanged
    assert isinstance(sample_mesoscope_config.filesystem.root_directory, Path)
    assert sample_mesoscope_config.filesystem.root_directory == original_root
    assert isinstance(sample_mesoscope_config.microcontrollers.valve_calibration_data, tuple)
    assert sample_mesoscope_config.microcontrollers.valve_calibration_data == original_valve_data


def test_mesoscope_system_configuration_yaml_round_trip(tmp_path, sample_mesoscope_config):
    """Verifies that configuration can be saved and loaded without data loss.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        sample_mesoscope_config: Fixture providing a sample configuration.

    This test ensures YAML serialization/deserialization preserves all data.
    """
    yaml_path = tmp_path / "test_config.yaml"

    # Saves configuration
    sample_mesoscope_config.save(path=yaml_path)

    # Loads configuration
    loaded_config = MesoscopeSystemConfiguration.from_yaml(file_path=yaml_path)

    # Verifies data integrity
    assert loaded_config.name == sample_mesoscope_config.name
    assert loaded_config.filesystem.root_directory == sample_mesoscope_config.filesystem.root_directory
    assert loaded_config.sheets.surgery_sheet_id == sample_mesoscope_config.sheets.surgery_sheet_id
    assert loaded_config.cameras.face_camera_index == sample_mesoscope_config.cameras.face_camera_index
    assert (
        loaded_config.microcontrollers.valve_calibration_data
        == sample_mesoscope_config.microcontrollers.valve_calibration_data
    )


# Tests for MesoscopeExperimentConfiguration


def test_mesoscope_experiment_configuration_initialization(sample_experiment_config):
    """Verifies basic initialization of MesoscopeExperimentConfiguration.

    Args:
        sample_experiment_config: Fixture providing a sample experiment configuration.

    This test ensures all fields are properly assigned during initialization.
    """
    assert sample_experiment_config.cue_map == {1: 50.0, 2: 75.0, 3: 50.0}
    assert sample_experiment_config.cue_offset_cm == 10.0
    assert sample_experiment_config.unity_scene_name == "TestScene"
    assert "state1" in sample_experiment_config.experiment_states
    assert "trial1" in sample_experiment_config.trial_structures


def test_mesoscope_experiment_configuration_nested_structures(sample_experiment_config):
    """Verifies nested dataclass structures in MesoscopeExperimentConfiguration.

    Args:
        sample_experiment_config: Fixture providing a sample experiment configuration.

    This test ensures nested experiment states and trials are properly initialized.
    """
    state = sample_experiment_config.experiment_states["state1"]
    assert isinstance(state, MesoscopeExperimentState)
    assert state.experiment_state_code == 1

    trial = sample_experiment_config.trial_structures["trial1"]
    assert isinstance(trial, MesoscopeExperimentTrial)
    assert trial.cue_sequence == [1, 2, 3]


def test_mesoscope_experiment_configuration_yaml_serialization(tmp_path, sample_experiment_config):
    """Verifies that MesoscopeExperimentConfiguration can be saved as YAML.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        sample_experiment_config: Fixture providing a sample experiment configuration.

    This test ensures the experiment configuration is properly serialized to YAML.
    """
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    assert yaml_path.exists()
    content = yaml_path.read_text()

    assert "cue_map:" in content
    assert "unity_scene_name:" in content
    assert "TestScene" in content


def test_mesoscope_experiment_configuration_yaml_deserialization(tmp_path, sample_experiment_config):
    """Verifies that MesoscopeExperimentConfiguration can be loaded from YAML.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        sample_experiment_config: Fixture providing a sample experiment configuration.

    This test ensures the experiment configuration is properly deserialized from YAML.
    """
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    loaded_config = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    assert loaded_config.cue_map == sample_experiment_config.cue_map
    assert loaded_config.unity_scene_name == sample_experiment_config.unity_scene_name
    assert loaded_config.cue_offset_cm == sample_experiment_config.cue_offset_cm


# Tests for set_working_directory function


def test_set_working_directory_creates_directory(clean_working_directory, monkeypatch):
    """Verifies that set_working_directory creates the directory if it does not exist.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function creates missing directories.
    """
    new_dir = clean_working_directory.parent / "new_working_dir"
    assert not new_dir.exists()

    # Patches appdirs to use our test directory
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(new_dir)

    assert new_dir.exists()


def test_set_working_directory_writes_path_file(clean_working_directory, monkeypatch):
    """Verifies that set_working_directory writes the path to the cache file.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the working directory path is cached correctly.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    path_file = app_dir / "working_directory_path.txt"
    assert path_file.exists()
    assert path_file.read_text() == str(clean_working_directory)


def test_set_working_directory_creates_app_directory(tmp_path, monkeypatch):
    """Verifies that set_working_directory creates the app data directory.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the application data directory is created if missing.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    working_dir = tmp_path / "working"
    working_dir.mkdir()

    assert not app_dir.exists()
    set_working_directory(working_dir)
    assert app_dir.exists()


def test_set_working_directory_overwrites_existing(clean_working_directory, monkeypatch):
    """Verifies that set_working_directory overwrites an existing cached path.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function can update an existing working directory path.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    # Sets first directory
    first_dir = clean_working_directory / "first"
    first_dir.mkdir()
    set_working_directory(first_dir)

    # Sets a second directory
    second_dir = clean_working_directory / "second"
    second_dir.mkdir()
    set_working_directory(second_dir)

    path_file = app_dir / "working_directory_path.txt"
    assert path_file.read_text() == str(second_dir)


# Tests for get_working_directory function


def test_get_working_directory_returns_cached_path(clean_working_directory, monkeypatch):
    """Verifies that get_working_directory returns the cached directory path.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function retrieves the correct cached path.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)
    retrieved_dir = get_working_directory()

    assert retrieved_dir == clean_working_directory


def test_get_working_directory_raises_error_if_not_set(tmp_path, monkeypatch):
    """Verifies that get_working_directory raises FileNotFoundError if not configured.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function raises an appropriate error when unconfigured.
    """
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    with pytest.raises(FileNotFoundError):
        get_working_directory()


def test_get_working_directory_raises_error_if_directory_missing(clean_working_directory, monkeypatch):
    """Verifies that get_working_directory raises error if cached directory does not exist.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function detects when the cached path no longer exists.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Deletes the working directory
    import shutil

    shutil.rmtree(clean_working_directory)

    with pytest.raises(FileNotFoundError):
        get_working_directory()


# Tests for set_google_credentials_path function


def test_set_google_credentials_path_creates_cache_file(tmp_path, monkeypatch):
    """Verifies that set_google_credentials_path creates the credentials' cache file.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the credentials' path is properly cached.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)

    cache_file = app_dir / "google_credentials_path.txt"
    assert cache_file.exists()
    assert cache_file.read_text() == str(credentials_file.resolve())


def test_set_google_credentials_path_raises_error_file_not_exists(tmp_path, monkeypatch):
    """Verifies that set_google_credentials_path raises error for non-existent files.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function validates file existence.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    non_existent_file = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        set_google_credentials_path(non_existent_file)


def test_set_google_credentials_path_raises_error_wrong_extension(tmp_path, monkeypatch):
    """Verifies that set_google_credentials_path raises error for non-JSON files.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function validates the file extension.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    wrong_extension = tmp_path / "credentials.txt"
    wrong_extension.write_text("not json")

    with pytest.raises(ValueError):
        set_google_credentials_path(wrong_extension)


# Tests for get_google_credentials_path function


def test_get_google_credentials_path_returns_cached_path(tmp_path, monkeypatch):
    """Verifies that get_google_credentials_path returns the cached credentials path.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function retrieves the correct cached credentials path.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)
    retrieved_path = get_google_credentials_path()

    assert retrieved_path == credentials_file.resolve()


def test_get_google_credentials_path_raises_error_if_not_set(tmp_path, monkeypatch):
    """Verifies that get_google_credentials_path raises an error if not configured.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function raises an error when the credentials' path is not set.
    """
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    with pytest.raises(FileNotFoundError):
        get_google_credentials_path()


def test_get_google_credentials_path_raises_error_if_file_missing(tmp_path, monkeypatch):
    """Verifies that get_google_credentials_path raises an error if the cached file no longer exists.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function detects when the cached credentials file is missing.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)

    # Deletes the credentials' file
    credentials_file.unlink()

    with pytest.raises(FileNotFoundError):
        get_google_credentials_path()


# Tests for the create_system_configuration_file function


def test_create_system_configuration_file_mesoscope_vr(clean_working_directory, monkeypatch):
    """Verifies that create_system_configuration_file creates a Mesoscope-VR config file.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function creates the correct configuration file.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))
    monkeypatch.setattr("builtins.input", lambda _: "")  # Mocks user input

    set_working_directory(clean_working_directory)
    create_system_configuration_file(AcquisitionSystems.MESOSCOPE_VR)

    config_file = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    assert config_file.exists()


def test_create_system_configuration_file_removes_existing(clean_working_directory, monkeypatch):
    """Verifies that create_system_configuration_file removes existing config files.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures only one configuration file exists after creation.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))
    monkeypatch.setattr("builtins.input", lambda _: "")

    set_working_directory(clean_working_directory)

    # Creates an existing config file
    existing_config = clean_working_directory / "configuration" / "old_system_configuration.yaml"
    existing_config.write_text("old config")

    create_system_configuration_file(AcquisitionSystems.MESOSCOPE_VR)

    # Verifies old config is removed
    assert not existing_config.exists()

    # Verifies new config exists
    new_config = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    assert new_config.exists()


def test_create_system_configuration_file_invalid_system(clean_working_directory, monkeypatch):
    """Verifies that create_system_configuration_file raises ValueError for invalid systems.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function rejects unsupported acquisition systems.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    with pytest.raises(ValueError):
        create_system_configuration_file("invalid-system")


def test_create_system_configuration_file_creates_valid_yaml(clean_working_directory, monkeypatch):
    """Verifies that create_system_configuration_file creates valid YAML content.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the created configuration file has a valid YAML structure.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))
    monkeypatch.setattr("builtins.input", lambda _: "")

    set_working_directory(clean_working_directory)
    create_system_configuration_file(AcquisitionSystems.MESOSCOPE_VR)

    config_file = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    content = config_file.read_text()

    # Verifies basic YAML structure
    assert "name:" in content
    assert "filesystem:" in content
    assert "cameras:" in content
    assert "microcontrollers:" in content


# Tests for get_system_configuration_data function


def test_get_system_configuration_data_loads_mesoscope_config(
    clean_working_directory, sample_mesoscope_config, monkeypatch
):
    """Verifies that get_system_configuration_data loads MesoscopeSystemConfiguration.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function correctly loads configuration data.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Saves configuration
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Loads configuration
    loaded_config = get_system_configuration_data()

    assert isinstance(loaded_config, MesoscopeSystemConfiguration)
    assert loaded_config.name == sample_mesoscope_config.name


def test_get_system_configuration_data_raises_error_no_config(clean_working_directory, monkeypatch):
    """Verifies that get_system_configuration_data raises an error when no config exists.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function raises an error when no configuration file is found.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    with pytest.raises(FileNotFoundError):
        get_system_configuration_data()


def test_get_system_configuration_data_raises_error_multiple_configs(clean_working_directory, monkeypatch):
    """Verifies that get_system_configuration_data raises error with multiple configs.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function rejects directories with multiple configuration files.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates multiple config files
    (clean_working_directory / "config1_configuration.yaml").write_text("config1")
    (clean_working_directory / "config2_configuration.yaml").write_text("config2")

    with pytest.raises(FileNotFoundError):
        get_system_configuration_data()


def test_get_system_configuration_data_raises_error_unsupported_config(clean_working_directory, monkeypatch):
    """Verifies that get_system_configuration_data raises error for unsupported config names.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the function rejects unrecognized configuration file names.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates unsupported config file
    (clean_working_directory / "configuration" / "unsupported_system_configuration.yaml").write_text("config")

    with pytest.raises(ValueError):
        get_system_configuration_data()


def test_get_system_configuration_data_path_types(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that get_system_configuration_data returns Path objects (not strings).

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures path fields are properly converted to Path objects after loading.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    loaded_config = get_system_configuration_data()

    # Verifies all path fields are Path objects
    assert isinstance(loaded_config.filesystem.root_directory, Path)
    assert isinstance(loaded_config.filesystem.server_directory, Path)
    assert isinstance(loaded_config.filesystem.nas_directory, Path)


def test_get_system_configuration_data_valve_calibration_tuple(
    clean_working_directory, sample_mesoscope_config, monkeypatch
):
    """Verifies that get_system_configuration_data returns valve_calibration_data as a tuple.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures valve calibration data is converted to tuple format after loading.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    loaded_config = get_system_configuration_data()

    # Verifies valve calibration is a tuple
    assert isinstance(loaded_config.microcontrollers.valve_calibration_data, tuple)
    assert all(isinstance(item, tuple) for item in loaded_config.microcontrollers.valve_calibration_data)


# Add this test after the existing SessionData.create tests


def test_session_data_create_raises_error_if_project_does_not_exist(
    clean_working_directory, sample_mesoscope_config, monkeypatch
):
    """Verifies that create() raises FileNotFoundError when the project doesn't exist.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures sessions cannot be created for non-existent projects.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Does NOT create the project directory

    with pytest.raises(FileNotFoundError) as exc_info:
        SessionData.create(
            project_name="nonexistent_project",
            animal_id="test_animal",
            session_type=SessionTypes.LICK_TRAINING,
            python_version="3.11.13",
            sl_experiment_version="3.0.0",
        )

    # Verifies the error message mentioning the project and CLI command
    assert "nonexistent_project" in str(exc_info.value)
    assert "sl-project create" in str(exc_info.value)


def test_session_data_create_copies_experiment_configuration(
    clean_working_directory, sample_mesoscope_config, sample_experiment_config, monkeypatch
):
    """Verifies that create() copies experiment configuration when experiment_name is provided.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        sample_experiment_config: Fixture providing a sample experiment configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures experiment configuration files are copied to session directories.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project and configuration directories
    project_dir = clean_working_directory / "test_project"
    config_dir = project_dir / "configuration"
    config_dir.mkdir(parents=True)

    # Creates experiment configuration file
    experiment_name = "test_experiment"
    experiment_config_path = config_dir / f"{experiment_name}.yaml"
    sample_experiment_config.to_yaml(file_path=experiment_config_path)

    # Creates session with experiment name
    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
        experiment_name=experiment_name,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies experiment configuration was copied to the session directory
    assert session_data.raw_data.experiment_configuration_path.exists()

    # Verifies content matches original
    loaded_config = MesoscopeExperimentConfiguration.from_yaml(
        file_path=session_data.raw_data.experiment_configuration_path
    )
    assert loaded_config.unity_scene_name == sample_experiment_config.unity_scene_name
    assert loaded_config.cue_map == sample_experiment_config.cue_map


def test_session_data_create_without_experiment_name_skips_experiment_config(
    clean_working_directory, sample_mesoscope_config, monkeypatch
):
    """Verifies that create() does not copy experiment config when experiment_name is None.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures experiment configuration is only copied for experiment sessions.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    project_dir = clean_working_directory / "test_project"
    project_dir.mkdir(parents=True)

    # Creates a session WITHOUT an experiment name
    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        experiment_name=None,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies an experiment configuration path exists but the file does not
    assert (
        session_data.raw_data.experiment_configuration_path
        == session_data.raw_data.raw_data_path / "experiment_configuration.yaml"
    )
    assert not session_data.raw_data.experiment_configuration_path.exists()


def test_session_data_create_saves_system_configuration(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() saves the system configuration to the session directory.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        sample_mesoscope_config: Fixture providing a sample configuration.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the system configuration snapshot is saved with each session.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    project_dir = clean_working_directory / "test_project"
    project_dir.mkdir(parents=True)

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.WINDOW_CHECKING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies system configuration file exists
    assert session_data.raw_data.system_configuration_path.exists()

    # Verifies content can be loaded
    loaded_config = MesoscopeSystemConfiguration.from_yaml(file_path=session_data.raw_data.system_configuration_path)
    assert loaded_config.name == sample_mesoscope_config.name
    assert loaded_config.cameras.face_camera_index == sample_mesoscope_config.cameras.face_camera_index


# Tests for ServerConfiguration dataclass


def test_server_configuration_default_initialization():
    """Verifies default initialization of ServerConfiguration.

    This test ensures the class initializes with expected default values.
    """
    config = ServerConfiguration()

    assert config.username == ""
    assert config.password == ""
    assert config.host == "cbsuwsun.biohpc.cornell.edu"
    assert config.storage_root == "/local/storage"
    assert config.working_root == "/local/workdir"
    assert config.shared_directory_name == "sun_data"


def test_server_configuration_post_init_resolves_paths():
    """Verifies that __post_init__ correctly resolves derived paths.

    This test ensures all paths are properly constructed.
    """
    config = ServerConfiguration(
        username="testuser",
        storage_root="/mnt/storage",
        working_root="/mnt/work",
        shared_directory_name="shared",
    )

    assert config.shared_storage_root == "/mnt/storage/shared"
    assert config.shared_working_root == "/mnt/work/shared"
    assert config.user_data_root == "/mnt/storage/testuser"
    assert config.user_working_root == "/mnt/work/testuser"


def test_server_configuration_custom_initialization():
    """Verifies custom initialization of ServerConfiguration.

    This test ensures all fields accept custom values.
    """
    config = ServerConfiguration(
        username="myuser",
        password="mypass",
        host="example.com",
        storage_root="/data",
        working_root="/work",
        shared_directory_name="lab_data",
    )

    assert config.username == "myuser"
    assert config.password == "mypass"
    assert config.host == "example.com"
    assert config.storage_root == "/data"
    assert config.working_root == "/work"
    assert config.shared_directory_name == "lab_data"


def test_server_configuration_yaml_round_trip(tmp_path):
    """Verifies that ServerConfiguration survives YAML serialization.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures YAML round-trip preserves all data.
    """
    yaml_path = tmp_path / "server_config.yaml"

    original = ServerConfiguration(
        username="testuser",
        password="testpass",
        host="server.example.com",
    )

    original.to_yaml(file_path=yaml_path)
    loaded = ServerConfiguration.from_yaml(file_path=yaml_path)

    assert loaded.username == original.username
    assert loaded.password == original.password
    assert loaded.host == original.host
    assert loaded.shared_storage_root == original.shared_storage_root


# Tests for the create_server_configuration_file function


def test_create_server_configuration_file_user(clean_working_directory, monkeypatch):
    """Verifies that create_server_configuration_file creates user config.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the user server configuration is created correctly.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    create_server_configuration_file(
        username="testuser",
        password="testpass",
        service=False,
    )

    config_file = clean_working_directory / "configuration" / "user_server_configuration.yaml"
    assert config_file.exists()

    # Verify content
    loaded = ServerConfiguration.from_yaml(file_path=config_file)
    assert loaded.username == "testuser"
    assert loaded.password == "testpass"


def test_create_server_configuration_file_service(clean_working_directory, monkeypatch):
    """Verifies that create_server_configuration_file creates service config.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures service server configuration is created correctly.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    create_server_configuration_file(
        username="service_account",
        password="service_pass",
        service=True,
    )

    config_file = clean_working_directory / "configuration" / "service_server_configuration.yaml"
    assert config_file.exists()

    # Verify content
    loaded = ServerConfiguration.from_yaml(file_path=config_file)
    assert loaded.username == "service_account"
    assert loaded.password == "service_pass"


def test_create_server_configuration_file_custom_parameters(clean_working_directory, monkeypatch):
    """Verifies that create_server_configuration_file accepts custom parameters.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures custom server parameters are preserved.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    create_server_configuration_file(
        username="myuser",
        password="mypass",
        host="custom.server.com",
        storage_root="/custom/storage",
        working_root="/custom/work",
        shared_directory_name="custom_shared",
        service=False,
    )

    config_file = clean_working_directory / "configuration" / "user_server_configuration.yaml"
    loaded = ServerConfiguration.from_yaml(file_path=config_file)

    assert loaded.host == "custom.server.com"
    assert loaded.storage_root == "/custom/storage"
    assert loaded.working_root == "/custom/work"
    assert loaded.shared_directory_name == "custom_shared"


# Tests for the get_server_configuration function


def test_get_server_configuration_user(clean_working_directory, monkeypatch):
    """Verifies that get_server_configuration loads user config.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures user configuration can be retrieved.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Create user config
    create_server_configuration_file(
        username="testuser",
        password="testpass",
        service=False,
    )

    # Load it
    config = get_server_configuration(service=False)

    assert config.username == "testuser"
    assert config.password == "testpass"


def test_get_server_configuration_service(clean_working_directory, monkeypatch):
    """Verifies that get_server_configuration loads service config.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures service configuration can be retrieved.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Create service config
    create_server_configuration_file(
        username="service",
        password="service_pass",
        service=True,
    )

    # Load it
    config = get_server_configuration(service=True)

    assert config.username == "service"
    assert config.password == "service_pass"


def test_get_server_configuration_raises_error_if_missing(clean_working_directory, monkeypatch):
    """Verifies that get_server_configuration raises error when config missing.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures proper error handling for missing configurations.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Don't create any config files

    with pytest.raises(FileNotFoundError) as exc_info:
        get_server_configuration(service=False)

    assert "user_server_configuration.yaml" in str(exc_info.value)


def test_get_server_configuration_raises_error_if_unconfigured(clean_working_directory, monkeypatch):
    """Verifies that get_server_configuration raises an error for placeholder credentials.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures unconfigured files are detected.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Create config with empty credentials (unconfigured)
    config_file = clean_working_directory / "configuration" / "user_server_configuration.yaml"
    ServerConfiguration().to_yaml(file_path=config_file)

    with pytest.raises(ValueError) as exc_info:
        get_server_configuration(service=False)

    assert "unconfigured" in str(exc_info.value).lower()


def test_get_server_configuration_distinguishes_user_and_service(clean_working_directory, monkeypatch):
    """Verifies that get_server_configuration correctly distinguishes user vs. service.

    Args:
        clean_working_directory: Fixture providing a temporary working directory.
        monkeypatch: Pytest fixture for modifying environment variables.

    This test ensures the correct config is loaded based on the service flag.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Create both configs with different usernames
    create_server_configuration_file(
        username="regular_user",
        password="user_pass",
        service=False,
    )

    create_server_configuration_file(
        username="service_user",
        password="service_pass",
        service=True,
    )

    # Verify the correct config is loaded
    user_config = get_server_configuration(service=False)
    service_config = get_server_configuration(service=True)

    assert user_config.username == "regular_user"
    assert service_config.username == "service_user"


# Tests for ProcessingTracker dataclass


def test_processing_tracker_initialization(tmp_path):
    """Verifies basic initialization of ProcessingTracker.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the tracker initializes with default values.
    """
    tracker_file = tmp_path / TrackerFiles.MANIFEST
    tracker = ProcessingTracker(file_path=tracker_file)

    assert tracker.file_path == tracker_file
    assert tracker._complete is False
    assert tracker._encountered_error is False
    assert tracker._running is False
    assert tracker._manager_id == -1
    assert tracker._job_count == 1
    assert tracker._completed_jobs == 0
    assert tracker.lock_path == str(tracker_file.with_suffix(".yaml.lock"))


def test_processing_tracker_post_init_validates_filename(tmp_path):
    """Verifies that __post_init__ validates the tracker filename.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures only supported tracker filenames are accepted.
    """
    invalid_tracker = tmp_path / "invalid_tracker.yaml"

    with pytest.raises(ValueError) as exc_info:
        ProcessingTracker(file_path=invalid_tracker)

    assert "Unsupported processing tracker file" in str(exc_info.value)
    assert "invalid_tracker.yaml" in str(exc_info.value)


def test_processing_tracker_post_init_accepts_valid_filenames(tmp_path):
    """Verifies that __post_init__ accepts all TrackerFiles enum values.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures all official tracker filenames are supported.
    """
    for tracker_file_name in TrackerFiles:
        tracker_path = tmp_path / tracker_file_name
        tracker = ProcessingTracker(file_path=tracker_path)
        assert tracker.file_path == tracker_path


def test_processing_tracker_load_state_creates_file_if_missing(tmp_path):
    """Verifies that _load_state() creates the tracker file if it doesn't exist.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the tracker auto-creates its state file.
    """
    tracker_file = tmp_path / TrackerFiles.MANIFEST
    tracker = ProcessingTracker(file_path=tracker_file)

    # Initially the file should not exist
    assert not tracker_file.exists()

    # Calling _load_state should create it
    tracker._load_state()

    assert tracker_file.exists()


def test_processing_tracker_load_state_reads_existing_file(tmp_path):
    """Verifies that _load_state() correctly reads from the existing file.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the tracker loads state from the disk correctly.
    """
    tracker_file = tmp_path / TrackerFiles.CHECKSUM

    # Create the first tracker and set some state
    tracker1 = ProcessingTracker(file_path=tracker_file)
    tracker1._running = True
    tracker1._manager_id = 12345
    tracker1._job_count = 5
    tracker1._completed_jobs = 3
    tracker1._save_state()

    # Create second tracker and load state
    tracker2 = ProcessingTracker(file_path=tracker_file)
    tracker2._load_state()

    assert tracker2._running is True
    assert tracker2._manager_id == 12345
    assert tracker2._job_count == 5
    assert tracker2._completed_jobs == 3


def test_processing_tracker_save_state_preserves_file_and_lock_paths(tmp_path):
    """Verifies that _save_state() doesn't modify file_path and lock_path.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the refactored _save_state() correctly preserves paths.
    """
    tracker_file = tmp_path / TrackerFiles.TRANSFER
    tracker = ProcessingTracker(file_path=tracker_file)

    original_file_path = tracker.file_path
    original_lock_path = tracker.lock_path

    tracker._save_state()

    # Verify paths are unchanged
    assert tracker.file_path == original_file_path
    assert tracker.lock_path == original_lock_path
    assert isinstance(tracker.file_path, Path)
    assert isinstance(tracker.lock_path, str)


def test_processing_tracker_start_locks_pipeline(tmp_path):
    """Verifies that start() correctly locks the pipeline.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures start() sets the running state and manager ID.
    """
    tracker_file = tmp_path / TrackerFiles.BEHAVIOR
    tracker = ProcessingTracker(file_path=tracker_file)

    manager_id = 99999
    job_count = 10

    tracker.start(manager_id=manager_id, job_count=job_count)

    # Reload state to verify persistence
    tracker._load_state()

    assert tracker._running is True
    assert tracker._manager_id == manager_id
    assert tracker._job_count == job_count
    assert tracker._completed_jobs == 0
    assert tracker._complete is False
    assert tracker._encountered_error is False


def test_processing_tracker_start_prevents_different_manager(tmp_path):
    """Verifies that start() prevents different manager from acquiring lock.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures exclusive lock ownership.
    """
    tracker_file = tmp_path / TrackerFiles.SUITE2P

    # First manager starts pipeline
    tracker1 = ProcessingTracker(file_path=tracker_file)
    tracker1.start(manager_id=100, job_count=5)

    # The second manager attempts to start the pipeline
    tracker2 = ProcessingTracker(file_path=tracker_file)

    with pytest.raises(PermissionError) as exc_info:
        tracker2.start(manager_id=200, job_count=3)

    assert "Unable to start the processing pipeline" in str(exc_info.value)
    assert "manager process with id 100" in str(exc_info.value)


def test_processing_tracker_start_allows_same_manager_reacquisition(tmp_path):
    """Verifies that start() allows the same manager to reacquire lock with no adverse side effects.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    tracker_file = tmp_path / TrackerFiles.VIDEO
    tracker = ProcessingTracker(file_path=tracker_file)

    manager_id = 12345

    # First start
    tracker.start(manager_id=manager_id, job_count=5)

    # Second start (should not raise error or modify state)
    tracker.start(manager_id=manager_id, job_count=10)  # Note: job_count shouldn't change

    tracker._load_state()
    assert tracker._running is True
    assert tracker._manager_id == manager_id
    assert tracker._job_count == 5  # Original job count preserved


def test_processing_tracker_stop_increments_completed_jobs(tmp_path):
    """Verifies that stop() increments the completed job counter.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures job progress is tracked correctly.
    """
    tracker_file = tmp_path / TrackerFiles.MULTIDAY
    tracker = ProcessingTracker(file_path=tracker_file)

    manager_id = 55555
    tracker.start(manager_id=manager_id, job_count=3)

    # Stop first job
    tracker.stop(manager_id=manager_id)
    tracker._load_state()
    assert tracker._completed_jobs == 1
    assert tracker._running is True  # Still running

    # Stop the second job
    tracker.stop(manager_id=manager_id)
    tracker._load_state()
    assert tracker._completed_jobs == 2
    assert tracker._running is True  # Still running


def test_processing_tracker_stop_completes_pipeline_when_all_jobs_done(tmp_path):
    """Verifies that stop() marks the pipeline complete when all jobs finish.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the pipeline completes after all jobs are done.
    """
    tracker_file = tmp_path / TrackerFiles.FORGING
    tracker = ProcessingTracker(file_path=tracker_file)

    manager_id = 77777
    job_count = 2
    tracker.start(manager_id=manager_id, job_count=job_count)

    # Complete the first job
    tracker.stop(manager_id=manager_id)
    tracker._load_state()
    assert tracker._running is True

    # Complete the second (final) job
    tracker.stop(manager_id=manager_id)
    tracker._load_state()

    assert tracker._running is False
    assert tracker._complete is True
    assert tracker._encountered_error is False
    assert tracker._manager_id == -1


def test_processing_tracker_stop_prevents_wrong_manager(tmp_path):
    """Verifies that stop() prevents non-owner from reporting completion.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures only the owning manager can stop the pipeline.
    """
    tracker_file = tmp_path / TrackerFiles.MANIFEST

    # Manager 1 starts the pipeline
    tracker1 = ProcessingTracker(file_path=tracker_file)
    tracker1.start(manager_id=100, job_count=5)

    # Manager 2 attempts to stop the pipeline
    tracker2 = ProcessingTracker(file_path=tracker_file)

    with pytest.raises(PermissionError) as exc_info:
        tracker2.stop(manager_id=200)

    assert "Unable to report that the processing pipeline has completed" in str(exc_info.value)


def test_processing_tracker_stop_ignores_if_not_running(tmp_path):
    """Verifies that stop() safely ignores calls when the pipeline not running.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures stop() is safe to call on non-running pipelines.
    """
    tracker_file = tmp_path / TrackerFiles.CHECKSUM
    tracker = ProcessingTracker(file_path=tracker_file)

    # Don't start the pipeline
    tracker.stop(manager_id=12345)  # Should not raise error

    tracker._load_state()
    assert tracker._completed_jobs == 0


def test_processing_tracker_error_marks_pipeline_failed(tmp_path):
    """Verifies that error() correctly marks the pipeline as failed.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the error state is properly recorded.
    """
    tracker_file = tmp_path / TrackerFiles.TRANSFER
    tracker = ProcessingTracker(file_path=tracker_file)

    manager_id = 88888
    tracker.start(manager_id=manager_id, job_count=5)

    # Report error
    tracker.error(manager_id=manager_id)

    tracker._load_state()
    assert tracker._running is False
    assert tracker._encountered_error is True
    assert tracker._complete is False
    assert tracker._manager_id == -1


def test_processing_tracker_error_prevents_wrong_manager(tmp_path):
    """Verifies that error() prevents non-owner from reporting errors.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures only the owning manager can report errors.
    """
    tracker_file = tmp_path / TrackerFiles.BEHAVIOR

    # Manager 1 starts the pipeline
    tracker1 = ProcessingTracker(file_path=tracker_file)
    tracker1.start(manager_id=100, job_count=5)

    # Manager 2 attempts to report an error
    tracker2 = ProcessingTracker(file_path=tracker_file)

    with pytest.raises(PermissionError) as exc_info:
        tracker2.error(manager_id=200)

    assert "Unable to report that the processing pipeline has encountered an error" in str(exc_info.value)


def test_processing_tracker_error_ignores_if_not_running(tmp_path):
    """Verifies that error() safely ignores calls when the pipeline not running.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures error() is safe to call on non-running pipelines.
    """
    tracker_file = tmp_path / TrackerFiles.SUITE2P
    tracker = ProcessingTracker(file_path=tracker_file)

    # Don't start the pipeline
    tracker.error(manager_id=12345)  # Should not raise error

    tracker._load_state()
    assert tracker._encountered_error is False


def test_processing_tracker_abort_resets_all_state(tmp_path):
    """Verifies that abort() resets tracker to default state.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures abort() provides emergency recovery.
    """
    tracker_file = tmp_path / TrackerFiles.VIDEO
    tracker = ProcessingTracker(file_path=tracker_file)

    # Starts the pipeline and do some work
    tracker.start(manager_id=12345, job_count=10)
    tracker.stop(manager_id=12345)
    tracker.stop(manager_id=12345)

    # Abort from any process
    tracker2 = ProcessingTracker(file_path=tracker_file)
    tracker2.abort()

    # Verify complete reset
    tracker2._load_state()
    assert tracker2._running is False
    assert tracker2._manager_id == -1
    assert tracker2._completed_jobs == 0
    assert tracker2._job_count == 1
    assert tracker2._complete is False
    assert tracker2._encountered_error is False


def test_processing_tracker_abort_allows_any_process(tmp_path):
    """Verifies that abort() can be called by any process.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures abort() provides emergency override capability.
    """
    tracker_file = tmp_path / TrackerFiles.MULTIDAY

    # Manager 1 locks the pipeline
    tracker1 = ProcessingTracker(file_path=tracker_file)
    tracker1.start(manager_id=100, job_count=5)

    # Manager 2 aborts (should succeed)
    tracker2 = ProcessingTracker(file_path=tracker_file)
    tracker2.abort()  # Should not raise error

    tracker2._load_state()
    assert tracker2._running is False
    assert tracker2._manager_id == -1


def test_processing_tracker_complete_property(tmp_path):
    """Verifies that the complete property correctly reports completion status.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the completion property accessor works correctly.
    """
    tracker_file = tmp_path / TrackerFiles.FORGING
    tracker = ProcessingTracker(file_path=tracker_file)

    # Initially not complete
    assert tracker.complete is False

    # Start and complete the pipeline
    manager_id = 11111
    tracker.start(manager_id=manager_id, job_count=1)
    assert tracker.complete is False

    tracker.stop(manager_id=manager_id)
    assert tracker.complete is True


def test_processing_tracker_encountered_error_property(tmp_path):
    """Verifies that encountered_error property correctly reports error status.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the error property accessor works correctly.
    """
    tracker_file = tmp_path / TrackerFiles.MANIFEST
    tracker = ProcessingTracker(file_path=tracker_file)

    # Initially no error
    assert tracker.encountered_error is False

    # Start pipeline
    manager_id = 22222
    tracker.start(manager_id=manager_id, job_count=5)
    assert tracker.encountered_error is False

    # Report error
    tracker.error(manager_id=manager_id)
    assert tracker.encountered_error is True


def test_processing_tracker_running_property(tmp_path):
    """Verifies that the running property correctly reports running status.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the running property accessor works correctly.
    """
    tracker_file = tmp_path / TrackerFiles.CHECKSUM
    tracker = ProcessingTracker(file_path=tracker_file)

    # Initially not running
    assert tracker.running is False

    # Start pipeline
    manager_id = 33333
    tracker.start(manager_id=manager_id, job_count=3)
    assert tracker.running is True

    # Complete pipeline
    for _ in range(3):
        tracker.stop(manager_id=manager_id)

    assert tracker.running is False


def test_processing_tracker_properties_reload_state(tmp_path):
    """Verifies that properties reload state from the disk on each access.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures properties always return current state from disk.
    """
    tracker_file = tmp_path / TrackerFiles.TRANSFER

    # Create two tracker instances pointing to the same file
    tracker1 = ProcessingTracker(file_path=tracker_file)
    tracker2 = ProcessingTracker(file_path=tracker_file)

    # Start the pipeline using tracker1
    tracker1.start(manager_id=44444, job_count=2)

    # Verify tracker2 sees the change via property access
    assert tracker2.running is True
    assert tracker2.complete is False

    # Complete via tracker1
    tracker1.stop(manager_id=44444)
    tracker1.stop(manager_id=44444)

    # Verify tracker2 sees completion
    assert tracker2.running is False
    assert tracker2.complete is True


def test_processing_tracker_concurrent_access_via_locks(tmp_path):
    """Verifies that file locks prevent race conditions in concurrent access.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the locking mechanism works for process safety.
    Note: This is a basic test; true concurrency testing would require multiprocessing.
    """
    tracker_file = tmp_path / TrackerFiles.BEHAVIOR

    # Simulate two processes accessing the same tracker
    tracker1 = ProcessingTracker(file_path=tracker_file)
    tracker2 = ProcessingTracker(file_path=tracker_file)

    # Both try to start with different manager IDs
    tracker1.start(manager_id=100, job_count=5)

    # Second should fail
    with pytest.raises(PermissionError):
        tracker2.start(manager_id=200, job_count=3)

    # Only first manager can modify state
    tracker1.stop(manager_id=100)

    with pytest.raises(PermissionError):
        tracker2.stop(manager_id=200)


def test_processing_tracker_yaml_round_trip(tmp_path):
    """Verifies that tracker state survives YAML serialization round trip.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures YAML serialization preserves all state correctly.
    """
    tracker_file = tmp_path / TrackerFiles.SUITE2P
    tracker = ProcessingTracker(file_path=tracker_file)

    # Set the complex state
    tracker.start(manager_id=99999, job_count=7)
    tracker.stop(manager_id=99999)
    tracker.stop(manager_id=99999)

    # Create new instance and verify state loaded correctly
    tracker2 = ProcessingTracker(file_path=tracker_file)
    tracker2._load_state()

    assert tracker2._running is True
    assert tracker2._manager_id == 99999
    assert tracker2._job_count == 7
    assert tracker2._completed_jobs == 2
    assert tracker2._complete is False
    assert tracker2._encountered_error is False


def test_processing_tracker_job_count_validation(tmp_path):
    """Verifies behavior when job_count is 0 or negative.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test documents edge case behavior for invalid job counts.
    Note: Current implementation doesn't validate job_count, but should it?
    """
    tracker_file = tmp_path / TrackerFiles.VIDEO
    tracker = ProcessingTracker(file_path=tracker_file)

    # Start with job_count of 0
    tracker.start(manager_id=11111, job_count=0)

    # Verify it completes immediately on the first stop
    tracker.stop(manager_id=11111)

    tracker._load_state()
    assert tracker._complete is True


def test_processing_tracker_state_transitions(tmp_path):
    """Verifies correct state transitions through the pipeline lifecycle.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test validates the full state machine behavior.
    """
    tracker_file = tmp_path / TrackerFiles.MULTIDAY
    tracker = ProcessingTracker(file_path=tracker_file)

    # Initial state
    assert not tracker.running
    assert not tracker.complete
    assert not tracker.encountered_error

    # Start: running
    manager_id = 55555
    tracker.start(manager_id=manager_id, job_count=2)
    assert tracker.running
    assert not tracker.complete
    assert not tracker.encountered_error

    # In progress: still running
    tracker.stop(manager_id=manager_id)
    assert tracker.running
    assert not tracker.complete
    assert not tracker.encountered_error

    # Complete: not running, complete
    tracker.stop(manager_id=manager_id)
    assert not tracker.running
    assert tracker.complete
    assert not tracker.encountered_error


def test_processing_tracker_error_state_transitions(tmp_path):
    """Verifies correct state transitions when the error occurs.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test validates error handling state machine behavior.
    """
    tracker_file = tmp_path / TrackerFiles.FORGING
    tracker = ProcessingTracker(file_path=tracker_file)

    # Start pipeline
    manager_id = 66666
    tracker.start(manager_id=manager_id, job_count=5)
    assert tracker.running

    # Do some work
    tracker.stop(manager_id=manager_id)
    tracker.stop(manager_id=manager_id)
    assert tracker.running

    # Encounter error
    tracker.error(manager_id=manager_id)
    assert not tracker.running
    assert not tracker.complete
    assert tracker.encountered_error


# Tests for ProcessingPipelines and ProcessingStatus enumerations


def test_processing_pipelines_enum_values():
    """Verifies all ProcessingPipelines enumeration values.

    This test ensures the enumeration contains all expected pipeline types.
    """
    assert ProcessingPipelines.MANIFEST == "manifest generation"
    assert ProcessingPipelines.CHECKSUM == "checksum resolution"
    assert ProcessingPipelines.TRANSFER == "data transfer"
    assert ProcessingPipelines.BEHAVIOR == "behavior processing"
    assert ProcessingPipelines.SUITE2P == "single-day suite2p processing"
    assert ProcessingPipelines.VIDEO == "video processing"
    assert ProcessingPipelines.MULTIDAY == "multi-day suite2p processing"
    assert ProcessingPipelines.FORGING == "dataset forging"


def test_processing_status_enum_values():
    """Verifies all ProcessingStatus enumeration values.

    This test ensures the enumeration contains all expected status codes.
    """
    assert ProcessingStatus.RUNNING == 0
    assert ProcessingStatus.SUCCEEDED == 1
    assert ProcessingStatus.FAILED == 2
    assert ProcessingStatus.ABORTED == 3


def test_tracker_files_enum_values():
    """Verifies all TrackerFiles enumeration values.

    This test ensures the enumeration contains all expected tracker filenames.
    """
    assert TrackerFiles.MANIFEST == "manifest_generation_tracker.yaml"
    assert TrackerFiles.CHECKSUM == "checksum_resolution_tracker.yaml"
    assert TrackerFiles.TRANSFER == "data_transfer_tracker.yaml"
    assert TrackerFiles.BEHAVIOR == "behavior_processing_tracker.yaml"
    assert TrackerFiles.SUITE2P == "suite2p_processing_tracker.yaml"
    assert TrackerFiles.VIDEO == "video_processing_tracker.yaml"
    assert TrackerFiles.MULTIDAY == "multiday_processing_tracker.yaml"
    assert TrackerFiles.FORGING == "dataset_forging_tracker.yaml"
