"""Contains tests for classes and methods provided by the data_classes module."""

from pathlib import Path

import pytest
import appdirs

from sl_shared_assets.data_classes import (
    SessionTypes,
    RawData,
    ProcessedData,
    TrackingData,
    SessionData,
    ProcessingTracker,
    ProcessingStatus,
)
from sl_shared_assets.configuration import (
    AcquisitionSystems,
    Cue,
    Segment,
    VREnvironment,
    WaterRewardTrial,
    ExperimentState,
    MesoscopeExperimentConfiguration,
    MesoscopeSystemConfiguration,
    set_working_directory,
)


@pytest.fixture
def sample_mesoscope_config() -> MesoscopeSystemConfiguration:
    """Creates a sample MesoscopeSystemConfiguration for testing."""
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
    """Creates a sample MesoscopeExperimentConfiguration for testing."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
        reinforcing_initial_guided_trials=10,
        reinforcing_recovery_failed_threshold=5,
        reinforcing_recovery_guided_trials=3,
    )

    # Cues: A->50, B->75, C->50 = 175 total for Segment_abc
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=2, length_cm=75.0),
        Cue(name="C", code=3, length_cm=50.0),
    ]

    segments = [
        Segment(name="Segment_abc", cue_sequence=["A", "B", "C"], transition_probabilities=None),
    ]

    # Trial references the segment - cue_sequence and trial_length_cm are derived
    trial = WaterRewardTrial(
        segment_name="Segment_abc",
        stimulus_trigger_zone_start_cm=150.0,
        stimulus_trigger_zone_end_cm=175.0,
        stimulus_location_cm=160.0,
        show_stimulus_collision_boundary=False,
    )

    config = MesoscopeExperimentConfiguration(
        cues=cues,
        segments=segments,
        trial_structures={"trial1": trial},
        experiment_states={"state1": state},
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
        ),
        unity_scene_name="TestScene",
        cue_offset_cm=10.0,
    )

    return config


@pytest.fixture
def clean_working_directory(tmp_path, monkeypatch):
    """Sets up a clean temporary working directory for testing."""
    # Patches appdirs to use temporary directory
    app_dir = tmp_path / "app_data"
    app_dir.mkdir()
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    working_dir = tmp_path / "working_directory"
    working_dir.mkdir()

    return working_dir


@pytest.fixture
def sample_session_hierarchy(tmp_path) -> Path:
    """Creates a sample session directory hierarchy for testing."""
    # Creates the session hierarchy: root/project/animal/session/raw_data
    root = tmp_path / "data"
    session_path = root / "test_project" / "test_animal" / "2024-01-15-12-30-45-123456" / "raw_data"
    session_path.mkdir(parents=True)

    return session_path.parent


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


def test_tracking_data_resolve_paths(tmp_path):
    """Verifies that resolve_paths correctly generates all data paths.

    This test ensures all paths are properly resolved from the root directory.
    """
    tracking_data = TrackingData()
    root_path = tmp_path / "tracking_data"

    tracking_data.resolve_paths(root_directory_path=root_path)

    assert tracking_data.tracking_data_path == root_path


def test_tracking_data_make_directories(tmp_path):
    """Verifies that make_directories creates the tracking data directory.

    This test ensures the directory creation method works correctly.
    """
    tracking_data = TrackingData()
    root_path = tmp_path / "tracking_data"

    tracking_data.resolve_paths(root_directory_path=root_path)
    tracking_data.make_directories()

    assert root_path.exists()


# Tests for SessionData dataclass


def test_session_data_post_init_creates_nested_instances():
    """Verifies that __post_init__ creates nested dataclass instances.

    This test ensures RawData, ProcessedData, and TrackingData are initialized.
    """
    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    assert isinstance(session_data.raw_data, RawData)
    assert isinstance(session_data.processed_data, ProcessedData)
    assert isinstance(session_data.tracking_data, TrackingData)


def test_session_data_create_requires_valid_session_type(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() raises error for invalid session types.

    This test ensures only valid session types are accepted.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    with pytest.raises(ValueError):
        SessionData.create(
            project_name="test_project",
            animal_id="test_animal",
            session_type="invalid_session_type",
            python_version="3.11.13",
            sl_experiment_version="3.0.0",
        )


def test_session_data_create_generates_session_directory(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() generates the session directory structure.

    This test ensures all required directories are created.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies session directory exists
    session_path = session_data.raw_data.raw_data_path.parent
    assert session_path.exists()
    assert session_data.raw_data.raw_data_path.exists()
    assert session_data.raw_data.camera_data_path.exists()
    assert session_data.raw_data.behavior_data_path.exists()


def test_session_data_create_saves_session_data_yaml(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() saves session_data.yaml file.

    This test ensures session metadata is persisted.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.RUN_TRAINING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies session_data.yaml exists
    assert session_data.raw_data.session_data_path.exists()

    content = session_data.raw_data.session_data_path.read_text()
    assert "test_project" in content
    assert "test_animal" in content


def test_session_data_create_marks_with_nk_file(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() creates the nk.bin marker file.

    This test ensures the session is marked as not yet initialized.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies nk.bin exists
    assert session_data.raw_data.nk_path.exists()


def test_session_data_load_finds_session_data_yaml(sample_session_hierarchy):
    """Verifies that load() finds and loads session_data.yaml.

    This test ensures sessions can be loaded from disk.
    """
    # Creates session_data.yaml
    session_data_path = sample_session_hierarchy / "raw_data" / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: lick training
acquisition_system: mesoscope
python_version: "3.11.13"
sl_experiment_version: "3.0.0"
raw_data: null
processed_data: null
tracking_data: null
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    assert loaded_session.project_name == "test_project"
    assert loaded_session.animal_id == "test_animal"
    assert loaded_session.session_type == SessionTypes.LICK_TRAINING


def test_session_data_load_raises_error_no_session_data_file(tmp_path):
    """Verifies that load() raises error when session_data.yaml is missing.

    This test ensures proper error handling for missing session files.
    """
    # Creates empty session directory
    session_path = tmp_path / "empty_session" / "raw_data"
    session_path.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=session_path.parent)


def test_session_data_load_raises_error_multiple_session_data_files(tmp_path):
    """Verifies that load() raises error with multiple session_data files.

    This test ensures ambiguous sessions are rejected.
    """
    session_path = tmp_path / "session"
    session_path.mkdir()

    # Creates multiple session data files
    (session_path / "session_data_1.yaml").write_text("test1")
    (session_path / "session_data_2.yaml").write_text("test2")

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=session_path)


def test_session_data_load_resolves_all_paths(sample_session_hierarchy):
    """Verifies that load() resolves all data paths.

    This test ensures raw_data, processed_data, and tracking_data paths are set.
    """
    session_data_path = sample_session_hierarchy / "raw_data" / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: mesoscope experiment
acquisition_system: mesoscope
python_version: "3.11.13"
sl_experiment_version: "3.0.0"
raw_data: null
processed_data: null
tracking_data: null
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    # Verifies paths are resolved
    assert loaded_session.raw_data.raw_data_path == sample_session_hierarchy / "raw_data"
    assert loaded_session.processed_data.processed_data_path == sample_session_hierarchy / "processed_data"
    assert loaded_session.tracking_data.tracking_data_path == sample_session_hierarchy / "tracking_data"


def test_session_data_load_creates_processed_and_tracking_directories(sample_session_hierarchy):
    """Verifies that load() creates processed and tracking directories if missing.

    This test ensures all required directories exist after loading.
    """
    session_data_path = sample_session_hierarchy / "raw_data" / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: lick training
acquisition_system: mesoscope
python_version: "3.11.13"
sl_experiment_version: "3.0.0"
raw_data: null
processed_data: null
tracking_data: null
"""
    session_data_path.write_text(session_data_content)

    # Verifies directories do not exist before load
    assert not (sample_session_hierarchy / "processed_data").exists()
    assert not (sample_session_hierarchy / "tracking_data").exists()

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    # Verifies directories exist after load
    assert loaded_session.processed_data.processed_data_path.exists()
    assert loaded_session.tracking_data.tracking_data_path.exists()


def test_session_data_runtime_initialized_removes_nk_file(sample_session_hierarchy):
    """Verifies that runtime_initialized() removes the nk.bin file.

    This test ensures sessions can be marked as initialized.
    """
    session_data_path = sample_session_hierarchy / "raw_data" / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: run training
acquisition_system: mesoscope
python_version: "3.11.13"
sl_experiment_version: "3.0.0"
raw_data: null
processed_data: null
tracking_data: null
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


def test_session_data_create_raises_error_if_project_does_not_exist(
    clean_working_directory, sample_mesoscope_config, monkeypatch
):
    """Verifies that create() raises FileNotFoundError when the project doesn't exist.

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

    This test ensures experiment configuration files are copied to session directories.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory and experiment configuration
    project_path = clean_working_directory / "test_project"
    project_path.mkdir()
    configuration_path = project_path / "configuration"
    configuration_path.mkdir()

    experiment_config_path = configuration_path / "test_experiment.yaml"
    sample_experiment_config.to_yaml(file_path=experiment_config_path)

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
        experiment_name="test_experiment",
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies experiment configuration was copied
    session_experiment_config = session_data.raw_data.raw_data_path / "experiment_configuration.yaml"
    assert session_experiment_config.exists()

    content = session_experiment_config.read_text()
    assert "TestScene" in content


def test_session_data_create_without_experiment_name_skips_experiment_config(
    clean_working_directory, sample_mesoscope_config, monkeypatch
):
    """Verifies that create() without experiment_name does not copy experiment config.

    This test ensures non-experiment sessions don't require experiment configuration.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        # No experiment_name provided
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies experiment configuration was NOT created
    session_experiment_config = session_data.raw_data.raw_data_path / "experiment_configuration.yaml"
    assert not session_experiment_config.exists()


def test_session_data_create_saves_system_configuration(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that create() saves system configuration to the session.

    This test ensures system configuration is copied for reproducibility.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(appdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Updates config with the actual root directory
    sample_mesoscope_config.filesystem.root_directory = clean_working_directory
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sl_experiment_version="3.0.0",
    )

    # Verifies system configuration file exists
    assert session_data.raw_data.system_configuration_path.exists()

    # Verifies content can be loaded
    loaded_config = MesoscopeSystemConfiguration.from_yaml(file_path=session_data.raw_data.system_configuration_path)
    assert loaded_config.name == sample_mesoscope_config.name
    assert loaded_config.cameras.face_camera_index == sample_mesoscope_config.cameras.face_camera_index


# Tests for ProcessingTracker dataclass


def test_processing_tracker_initialization(tmp_path):
    """Verifies basic initialization of ProcessingTracker.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the tracker initializes with default values.
    """
    tracker_file = tmp_path / "test_tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    assert tracker.file_path == tracker_file
    assert tracker.jobs == {}
    assert tracker.lock_path == str(tracker_file.with_suffix(".yaml.lock"))


def test_processing_tracker_generate_job_id():
    """Verifies that generate_job_id produces consistent hash-based IDs.

    This test ensures the job ID generation is deterministic.
    """
    session_path = Path("/data/project/animal/session")
    job_name = "suite2p_processing"

    # Generate the same ID multiple times
    id1 = ProcessingTracker.generate_job_id(session_path, job_name)
    id2 = ProcessingTracker.generate_job_id(session_path, job_name)

    # Should be consistent
    assert id1 == id2
    # Should be a hexadecimal string
    assert len(id1) == 16
    assert all(c in "0123456789abcdef" for c in id1)


def test_processing_tracker_generate_job_id_unique():
    """Verifies that different jobs produce different IDs.

    This test ensures job IDs are unique for different inputs.
    """
    session_path = Path("/data/project/animal/session")

    id1 = ProcessingTracker.generate_job_id(session_path, "job1")
    id2 = ProcessingTracker.generate_job_id(session_path, "job2")

    assert id1 != id2


def test_processing_tracker_initialize_jobs(tmp_path):
    """Verifies that initialize_jobs creates scheduled job entries.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures jobs are properly initialized.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_ids = [
        ProcessingTracker.generate_job_id(session_path, "job1"),
        ProcessingTracker.generate_job_id(session_path, "job2"),
        ProcessingTracker.generate_job_id(session_path, "job3"),
    ]

    tracker.initialize_jobs(job_ids=job_ids)

    # Reload to verify persistence
    tracker._load_state()
    assert len(tracker.jobs) == 3
    for job_id in job_ids:
        assert job_id in tracker.jobs
        assert tracker.jobs[job_id].status == ProcessingStatus.SCHEDULED
        assert tracker.jobs[job_id].slurm_job_id is None


def test_processing_tracker_initialize_jobs_preserves_existing(tmp_path):
    """Verifies that initialize_jobs doesn't overwrite existing job entries.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures reinitializing doesn't lose progress.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_ids = [
        ProcessingTracker.generate_job_id(session_path, "job1"),
        ProcessingTracker.generate_job_id(session_path, "job2"),
    ]

    # Initialize first time
    tracker.initialize_jobs(job_ids=job_ids)

    # Start one job
    tracker.start_job(job_ids[0])

    # Reinitialize with the same jobs
    tracker.initialize_jobs(job_ids=job_ids)

    # Verify the first job's status is preserved
    tracker._load_state()
    assert tracker.jobs[job_ids[0]].status == ProcessingStatus.RUNNING
    assert tracker.jobs[job_ids[1]].status == ProcessingStatus.SCHEDULED


def test_processing_tracker_start_job(tmp_path, monkeypatch):
    """Verifies that start_job marks a job as running.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for environment modification.

    This test ensures jobs' transition to RUNNING status.
    """
    # Mock SLURM environment
    monkeypatch.setenv("SLURM_JOB_ID", "12345")

    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_id = ProcessingTracker.generate_job_id(session_path, "test_job")

    tracker.initialize_jobs(job_ids=[job_id])
    tracker.start_job(job_id)

    tracker._load_state()
    assert tracker.jobs[job_id].status == ProcessingStatus.RUNNING
    assert tracker.jobs[job_id].slurm_job_id == 12345


def test_processing_tracker_start_job_without_slurm(tmp_path):
    """Verifies that start_job works without a SLURM environment.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the tracker works in non-SLURM environments.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_id = ProcessingTracker.generate_job_id(session_path, "test_job")

    tracker.initialize_jobs(job_ids=[job_id])
    tracker.start_job(job_id)

    tracker._load_state()
    assert tracker.jobs[job_id].status == ProcessingStatus.RUNNING
    assert tracker.jobs[job_id].slurm_job_id is None


def test_processing_tracker_start_job_raises_for_unknown_job(tmp_path):
    """Verifies that start_job raises ValueError for unknown job IDs.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures proper error handling for invalid job IDs.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    unknown_job_id = "nonexistent_job_id"

    with pytest.raises(ValueError) as exc_info:
        tracker.start_job(unknown_job_id)

    assert "not configured to track" in str(exc_info.value)


def test_processing_tracker_complete_job(tmp_path):
    """Verifies that complete_job marks a job as succeeded.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures jobs' transition to SUCCEEDED status.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_id = ProcessingTracker.generate_job_id(session_path, "test_job")

    tracker.initialize_jobs(job_ids=[job_id])
    tracker.start_job(job_id)
    tracker.complete_job(job_id)

    tracker._load_state()
    assert tracker.jobs[job_id].status == ProcessingStatus.SUCCEEDED


def test_processing_tracker_fail_job(tmp_path):
    """Verifies that fail_job marks a job as failed.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures jobs can be marked as FAILED.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_id = ProcessingTracker.generate_job_id(session_path, "test_job")

    tracker.initialize_jobs(job_ids=[job_id])
    tracker.start_job(job_id)
    tracker.fail_job(job_id)

    tracker._load_state()
    assert tracker.jobs[job_id].status == ProcessingStatus.FAILED


def test_processing_tracker_get_job_status(tmp_path):
    """Verifies that get_job_status returns the correct status.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures status queries work correctly.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_id = ProcessingTracker.generate_job_id(session_path, "test_job")

    tracker.initialize_jobs(job_ids=[job_id])

    # Check scheduled status
    assert tracker.get_job_status(job_id) == ProcessingStatus.SCHEDULED

    # Start and check the running status
    tracker.start_job(job_id)
    assert tracker.get_job_status(job_id) == ProcessingStatus.RUNNING

    # Complete and check succeeded status
    tracker.complete_job(job_id)
    assert tracker.get_job_status(job_id) == ProcessingStatus.SUCCEEDED


def test_processing_tracker_reset(tmp_path):
    """Verifies that reset clears all jobs.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the reset method works correctly.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_ids = [
        ProcessingTracker.generate_job_id(session_path, "job1"),
        ProcessingTracker.generate_job_id(session_path, "job2"),
    ]

    tracker.initialize_jobs(job_ids=job_ids)
    tracker.start_job(job_ids[0])

    # Reset
    tracker.reset()

    tracker._load_state()
    assert len(tracker.jobs) == 0


def test_processing_tracker_complete_property(tmp_path):
    """Verifies that the complete property returns True when all jobs succeed.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures pipeline completion detection works.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_ids = [
        ProcessingTracker.generate_job_id(session_path, "job1"),
        ProcessingTracker.generate_job_id(session_path, "job2"),
    ]

    tracker.initialize_jobs(job_ids=job_ids)
    assert not tracker.complete

    # Completes the first job
    tracker.start_job(job_ids[0])
    tracker.complete_job(job_ids[0])
    assert not tracker.complete

    # Completes the second job
    tracker.start_job(job_ids[1])
    tracker.complete_job(job_ids[1])
    assert tracker.complete


def test_processing_tracker_encountered_error_property(tmp_path):
    """Verifies that the encountered_error property returns True when any job fails.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures error detection works.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_ids = [
        ProcessingTracker.generate_job_id(session_path, "job1"),
        ProcessingTracker.generate_job_id(session_path, "job2"),
    ]

    tracker.initialize_jobs(job_ids=job_ids)
    assert not tracker.encountered_error

    # Complete the first job successfully
    tracker.start_job(job_ids[0])
    tracker.complete_job(job_ids[0])
    assert not tracker.encountered_error

    # Fail second job
    tracker.start_job(job_ids[1])
    tracker.fail_job(job_ids[1])
    assert tracker.encountered_error


def test_processing_tracker_concurrent_access(tmp_path):
    """Verifies that file locks prevent race conditions.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures thread-safe operation.
    """
    tracker_file = tmp_path / "tracker.yaml"

    # Simulate two processes
    tracker1 = ProcessingTracker(file_path=tracker_file)
    tracker2 = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_id = ProcessingTracker.generate_job_id(session_path, "test_job")

    # Initialize from the first process
    tracker1.initialize_jobs(job_ids=[job_id])

    # The second process can see the job
    assert tracker2.get_job_status(job_id) == ProcessingStatus.SCHEDULED

    # The first process starts the job
    tracker1.start_job(job_id)

    # The second process sees the update
    assert tracker2.get_job_status(job_id) == ProcessingStatus.RUNNING


def test_processing_tracker_yaml_serialization(tmp_path):
    """Verifies that the tracker state is properly serialized to YAML.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures YAML round-trip works correctly.
    """
    tracker_file = tmp_path / "tracker.yaml"
    tracker = ProcessingTracker(file_path=tracker_file)

    session_path = Path("/data/session")
    job_ids = [
        ProcessingTracker.generate_job_id(session_path, "job1"),
        ProcessingTracker.generate_job_id(session_path, "job2"),
    ]

    tracker.initialize_jobs(job_ids=job_ids)
    tracker.start_job(job_ids[0])

    # Creates a new instance and verify it loads correctly
    tracker2 = ProcessingTracker(file_path=tracker_file)
    tracker2._load_state()

    assert len(tracker2.jobs) == 2
    assert tracker2.jobs[job_ids[0]].status == ProcessingStatus.RUNNING
    assert tracker2.jobs[job_ids[1]].status == ProcessingStatus.SCHEDULED


# Tests for ProcessingStatus enumeration


def test_processing_status_enum_values():
    """Verifies all ProcessingStatus enumeration values.

    This test ensures the enumeration contains all expected status codes.
    """
    assert ProcessingStatus.SCHEDULED == 0
    assert ProcessingStatus.RUNNING == 1
    assert ProcessingStatus.SUCCEEDED == 2
    assert ProcessingStatus.FAILED == 3
