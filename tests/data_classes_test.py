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
    get_working_directory,
    get_system_configuration_data,
)

from sl_shared_assets.data_classes.configuration_data import set_working_directory, create_system_configuration_file


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
    config.sheets.google_credentials_path = Path("/home/user/.credentials/service_account.json")
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


# Tests for AcquisitionSystems enumeration


@pytest.mark.xdist_group(name="group3")
def test_acquisition_systems_mesoscope_vr():
    """Verifies the MESOSCOPE_VR acquisition system enumeration value.

    This test ensures the enumeration contains the expected string value.
    """
    assert AcquisitionSystems.MESOSCOPE_VR == "mesoscope-vr"
    assert str(AcquisitionSystems.MESOSCOPE_VR) == "mesoscope-vr"


@pytest.mark.xdist_group(name="group3")
def test_acquisition_systems_is_string_enum():
    """Verifies that AcquisitionSystems inherits from StrEnum.

    This test ensures the enumeration members behave as strings.
    """
    assert isinstance(AcquisitionSystems.MESOSCOPE_VR, str)


# Tests for MesoscopeExperimentState dataclass


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
def test_mesoscope_filesystem_default_initialization():
    """Verifies default initialization of MesoscopeFileSystem.

    This test ensures all fields have default Path() values.
    """
    filesystem = MesoscopeFileSystem()

    assert filesystem.root_directory == Path()
    assert filesystem.server_directory == Path()
    assert filesystem.nas_directory == Path()
    assert filesystem.mesoscope_directory == Path()


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
def test_mesoscope_google_sheets_default_initialization():
    """Verifies default initialization of MesoscopeGoogleSheets.

    This test ensures all fields have appropriate default values.
    """
    sheets = MesoscopeGoogleSheets()

    assert sheets.google_credentials_path == Path()
    assert sheets.surgery_sheet_id == ""
    assert sheets.water_log_sheet_id == ""


@pytest.mark.xdist_group(name="group3")
def test_mesoscope_google_sheets_custom_initialization():
    """Verifies custom initialization of MesoscopeGoogleSheets.

    This test ensures all fields accept custom values.
    """
    sheets = MesoscopeGoogleSheets(
        google_credentials_path=Path("/home/user/.creds/service.json"),
        surgery_sheet_id="abc123xyz",
        water_log_sheet_id="def456uvw",
    )

    assert sheets.google_credentials_path == Path("/home/user/.creds/service.json")
    assert sheets.surgery_sheet_id == "abc123xyz"
    assert sheets.water_log_sheet_id == "def456uvw"


# Tests for MesoscopeCameras dataclass


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
def test_mesoscope_microcontrollers_default_initialization():
    """Verifies default initialization of MesoscopeMicroControllers.

    This test ensures all fields have appropriate default values.
    """
    mcu = MesoscopeMicroControllers()

    assert mcu.actor_port == "/dev/ttyACM0"
    assert mcu.sensor_port == "/dev/ttyACM1"
    assert mcu.encoder_port == "/dev/ttyACM2"
    assert mcu.debug is False
    assert mcu.wheel_diameter_cm == 15.0333
    assert mcu.lick_threshold_adc == 600
    assert len(mcu.valve_calibration_data) == 4


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
def test_mesoscope_microcontrollers_custom_valve_calibration():
    """Verifies custom valve_calibration_data initialization.

    This test ensures custom calibration data can be provided during initialization.
    """
    custom_calibration = ((10000, 0.5), (20000, 1.5), (30000, 3.0))
    mcu = MesoscopeMicroControllers(valve_calibration_data=custom_calibration)

    assert mcu.valve_calibration_data == custom_calibration
    assert len(mcu.valve_calibration_data) == 3


# Tests for MesoscopeExternalAssets dataclass


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
def test_mesoscope_system_configuration_post_init_invalid_valve_calibration():
    """Verifies that __post_init__ raises TypeError for invalid valve calibration data.

    This test ensures improper calibration data structure is detected and rejected.
    """
    config = MesoscopeSystemConfiguration()
    # noinspection PyTypeChecker
    config.microcontrollers.valve_calibration_data = ((10000, "invalid"), (20000, 1.5))

    with pytest.raises(TypeError):
        config.__post_init__()


@pytest.mark.xdist_group(name="group3")
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
    assert "mesoscope-vr" in content


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


# Tests for the create_system_configuration_file function


@pytest.mark.xdist_group(name="group3")
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

    config_file = clean_working_directory / "mesoscope-vr_configuration.yaml"
    assert config_file.exists()


@pytest.mark.xdist_group(name="group3")
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
    existing_config = clean_working_directory / "old_configuration.yaml"
    existing_config.write_text("old config")

    create_system_configuration_file(AcquisitionSystems.MESOSCOPE_VR)

    # Verifies old config is removed
    assert not existing_config.exists()

    # Verifies new config exists
    new_config = clean_working_directory / "mesoscope-vr_configuration.yaml"
    assert new_config.exists()


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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

    config_file = clean_working_directory / "mesoscope-vr_configuration.yaml"
    content = config_file.read_text()

    # Verifies basic YAML structure
    assert "name:" in content
    assert "filesystem:" in content
    assert "cameras:" in content
    assert "microcontrollers:" in content


# Tests for get_system_configuration_data function


@pytest.mark.xdist_group(name="group3")
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
    config_path = clean_working_directory / "mesoscope-vr_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Loads configuration
    loaded_config = get_system_configuration_data()

    assert isinstance(loaded_config, MesoscopeSystemConfiguration)
    assert loaded_config.name == sample_mesoscope_config.name


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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


@pytest.mark.xdist_group(name="group3")
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
    (clean_working_directory / "unsupported_configuration.yaml").write_text("config")

    with pytest.raises(ValueError):
        get_system_configuration_data()


@pytest.mark.xdist_group(name="group3")
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

    config_path = clean_working_directory / "mesoscope-vr_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    loaded_config = get_system_configuration_data()

    # Verifies all path fields are Path objects
    assert isinstance(loaded_config.filesystem.root_directory, Path)
    assert isinstance(loaded_config.filesystem.server_directory, Path)
    assert isinstance(loaded_config.filesystem.nas_directory, Path)
    assert isinstance(loaded_config.sheets.google_credentials_path, Path)


@pytest.mark.xdist_group(name="group3")
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

    config_path = clean_working_directory / "mesoscope-vr_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    loaded_config = get_system_configuration_data()

    # Verifies valve calibration is a tuple
    assert isinstance(loaded_config.microcontrollers.valve_calibration_data, tuple)
    assert all(isinstance(item, tuple) for item in loaded_config.microcontrollers.valve_calibration_data)
