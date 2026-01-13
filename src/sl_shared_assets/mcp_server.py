"""Provides the MCP server for agentic configuration of Sun lab data workflow components.

This module exposes tools that enable AI agents to interactively build complex experiment and system configurations
through a template-then-edit workflow. The server supports both read operations (querying current state) and write
operations (creating and modifying configurations).
"""

from pathlib import Path
from dataclasses import asdict

from mcp.server.fastmcp import FastMCP
from ataraxis_base_utilities import ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from .data_classes import (
    Cue,
    Segment,
    GasPuffTrial,
    VREnvironment,
    WaterRewardTrial,
    AcquisitionSystems,
    ServerConfiguration,
    MesoscopeExperimentState,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory as _set_working_directory,
    get_system_configuration_data,
    get_server_configuration,
    get_google_credentials_path,
    set_google_credentials_path as _set_google_credentials_path,
    create_system_configuration_file,
)

# Initializes the MCP server with JSON response mode for structured output.
mcp = FastMCP(name="sl-shared-assets", json_response=True)


def _get_experiment_config_path(project: str, experiment: str) -> Path:
    """Resolves the path to an experiment configuration file.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.

    Returns:
        The path to the experiment configuration YAML file.
    """
    working_dir = get_working_directory()
    return working_dir.joinpath(project, "configuration", f"{experiment}.yaml")


def _load_experiment_config(project: str, experiment: str) -> MesoscopeExperimentConfiguration:
    """Loads an experiment configuration from disk.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.

    Returns:
        The loaded experiment configuration.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
    """
    config_path = _get_experiment_config_path(project=project, experiment=experiment)
    if not config_path.exists():
        message = f"Experiment configuration file not found: {config_path}"
        raise FileNotFoundError(message)
    return MesoscopeExperimentConfiguration.from_yaml(file_path=config_path)


def _save_experiment_config(project: str, experiment: str, config: MesoscopeExperimentConfiguration) -> None:
    """Saves an experiment configuration to disk.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        config: The experiment configuration to save.
    """
    config_path = _get_experiment_config_path(project=project, experiment=experiment)
    config.to_yaml(file_path=config_path)


# ==============================================================================================================
# Read Operations - Query current configuration state
# ==============================================================================================================


@mcp.tool()
def get_working_directory_tool() -> str:
    """Returns the current Sun lab working directory path.

    Returns:
        The absolute path to the working directory, or an error message if not configured.
    """
    try:
        path = get_working_directory()
        return f"Working directory: {path}"
    except FileNotFoundError as e:
        return f"Error: {e}"


@mcp.tool()
def get_system_configuration_tool() -> str:
    """Returns the current data acquisition system configuration.

    Returns:
        The system configuration as a formatted string, or an error message if not configured.
    """
    try:
        config = get_system_configuration_data()
        return f"System: {config.name} | Root: {config.filesystem.root_directory}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def get_server_configuration_tool() -> str:
    """Returns the current compute server configuration (password masked for security).

    Returns:
        The server configuration summary, or an error message if not configured.
    """
    try:
        config = get_server_configuration()
        return f"Server: {config.host} | User: {config.username} | Storage: {config.storage_root}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def get_google_credentials_tool() -> str:
    """Returns the path to the Google service account credentials file.

    Returns:
        The credentials file path, or an error message if not configured.
    """
    try:
        path = get_google_credentials_path()
        return f"Google credentials: {path}"
    except FileNotFoundError as e:
        return f"Error: {e}"


@mcp.tool()
def read_experiment_configuration_tool(project: str, experiment: str) -> str:
    """Reads and returns an experiment configuration file contents.

    Args:
        project: The name of the project containing the experiment.
        experiment: The name of the experiment configuration to read.

    Returns:
        The experiment configuration summary, or an error message if not found.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)
        cue_count = len(config.cues)
        segment_count = len(config.segments)
        trial_count = len(config.trial_structures)
        state_count = len(config.experiment_states)
        return (
            f"Experiment: {experiment} | Scene: {config.unity_scene_name} | "
            f"Cues: {cue_count} | Segments: {segment_count} | Trials: {trial_count} | States: {state_count}"
        )
    except FileNotFoundError as e:
        return f"Error: {e}"


# ==============================================================================================================
# Setup Operations - Configure working environment
# ==============================================================================================================


@mcp.tool()
def set_working_directory_tool(directory: str) -> str:
    """Sets the Sun lab working directory.

    Args:
        directory: The absolute path to set as the working directory.

    Returns:
        A confirmation message or error description.
    """
    try:
        path = Path(directory)
        _set_working_directory(path=path)
        return f"Working directory set to: {path}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_google_credentials_tool(credentials_path: str) -> str:
    """Sets the path to the Google service account credentials file.

    Args:
        credentials_path: The absolute path to the credentials JSON file.

    Returns:
        A confirmation message or error description.
    """
    try:
        path = Path(credentials_path)
        _set_google_credentials_path(path=path)
        return f"Google credentials path set to: {path}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def create_system_configuration_tool(system: str = "mesoscope") -> str:
    """Creates a data acquisition system configuration file.

    Args:
        system: The acquisition system type. Currently only 'mesoscope' is supported.

    Returns:
        A confirmation message or error description.
    """
    try:
        system_enum = AcquisitionSystems(system)
        create_system_configuration_file(system=system_enum)
        return f"System configuration created for: {system}"
    except (ValueError, FileNotFoundError) as e:
        return f"Error: {e}"


@mcp.tool()
def create_project_tool(project: str) -> str:
    """Creates a new project directory structure.

    Args:
        project: The name of the project to create.

    Returns:
        A confirmation message or error description.
    """
    try:
        system_config = get_system_configuration_data()
        project_path = system_config.filesystem.root_directory.joinpath(project, "configuration")
        ensure_directory_exists(project_path)
        return f"Project '{project}' created at: {project_path.parent}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


# ==============================================================================================================
# Server Configuration - Two-step process for sensitive credentials
# ==============================================================================================================


@mcp.tool()
def create_server_configuration_template_tool(
    username: str,
    host: str = "cbsuwsun.biohpc.cornell.edu",
    storage_root: str = "/local/storage",
    working_root: str = "/local/workdir",
    shared_directory: str = "sun_data",
) -> str:
    """Creates a server configuration template with a placeholder password.

    The user must manually edit the generated file to add their password, then call get_server_configuration_tool
    to validate the configuration.

    Args:
        username: The username for server authentication.
        host: The server hostname or IP address.
        storage_root: The path to the server's slow HDD RAID volume.
        working_root: The path to the server's fast NVME RAID volume.
        shared_directory: The name of the shared directory for Sun lab data.

    Returns:
        The path to the created template file and instructions for the user.
    """
    try:
        output_directory = get_working_directory().joinpath("configuration")
        config_path = output_directory.joinpath("server_configuration.yaml")

        # Creates configuration with placeholder password
        ServerConfiguration(
            username=username,
            password="ENTER_YOUR_PASSWORD_HERE",
            host=host,
            storage_root=storage_root,
            working_root=working_root,
            shared_directory_name=shared_directory,
        ).to_yaml(file_path=config_path)

        return (
            f"Server configuration template created at: {config_path}\n"
            f"ACTION REQUIRED: Edit the file to replace 'ENTER_YOUR_PASSWORD_HERE' with your actual password.\n"
            f"After editing, use get_server_configuration_tool to validate the configuration."
        )
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


# ==============================================================================================================
# Experiment Configuration - Template creation and incremental editing
# ==============================================================================================================


@mcp.tool()
def create_experiment_template_tool(project: str, experiment: str, unity_scene_name: str = "") -> str:
    """Creates a new experiment configuration template with default values.

    This creates a minimal template that can be incrementally built up using the add_* tools.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        unity_scene_name: The Unity scene name for the VR environment.

    Returns:
        A confirmation message with the file path, or an error description.
    """
    try:
        # Verifies project exists
        system_config = get_system_configuration_data()
        project_path = system_config.filesystem.root_directory.joinpath(project)
        if not project_path.exists():
            return f"Error: Project '{project}' does not exist. Create it first with create_project_tool."

        # Creates minimal template with placeholder cue and segment
        config = MesoscopeExperimentConfiguration(
            cues=[Cue(name="Gray", code=0, length_cm=30.0)],
            segments=[Segment(name="Segment_default", cue_sequence=["Gray"])],
            trial_structures={},
            experiment_states={},
            vr_environment=VREnvironment(),
            unity_scene_name=unity_scene_name,
            cue_offset_cm=10.0,
        )

        config_path = _get_experiment_config_path(project=project, experiment=experiment)
        config.to_yaml(file_path=config_path)

        return f"Experiment template created at: {config_path}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def add_cue_tool(project: str, experiment: str, name: str, code: int, length_cm: float) -> str:
    """Adds a visual cue to an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The cue name (e.g., 'A', 'B', 'Gray').
        code: The unique uint8 code (0-255) for MQTT communication.
        length_cm: The cue length in centimeters.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        # Checks for duplicate name or code
        existing_names = {cue.name for cue in config.cues}
        existing_codes = {cue.code for cue in config.cues}

        if name in existing_names:
            return f"Error: Cue with name '{name}' already exists."
        if code in existing_codes:
            return f"Error: Cue with code {code} already exists."

        # Adds new cue
        new_cue = Cue(name=name, code=code, length_cm=length_cm)
        config.cues.append(new_cue)

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Added cue: {name} (code={code}, length={length_cm}cm)"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def remove_cue_tool(project: str, experiment: str, name: str) -> str:
    """Removes a visual cue from an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The name of the cue to remove.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        # Finds and removes cue
        original_count = len(config.cues)
        config.cues = [cue for cue in config.cues if cue.name != name]

        if len(config.cues) == original_count:
            return f"Error: Cue '{name}' not found."

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Removed cue: {name}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def add_segment_tool(project: str, experiment: str, name: str, cue_sequence: list[str]) -> str:
    """Adds a segment (cue sequence) to an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The segment name (Unity prefab name).
        cue_sequence: The ordered list of cue names comprising this segment.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        # Checks for duplicate name
        existing_names = {seg.name for seg in config.segments}
        if name in existing_names:
            return f"Error: Segment with name '{name}' already exists."

        # Validates cue references
        available_cues = {cue.name for cue in config.cues}
        invalid_cues = [c for c in cue_sequence if c not in available_cues]
        if invalid_cues:
            return f"Error: Unknown cues in sequence: {invalid_cues}. Available: {sorted(available_cues)}"

        # Adds new segment
        new_segment = Segment(name=name, cue_sequence=cue_sequence)
        config.segments.append(new_segment)

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Added segment: {name} with cues {cue_sequence}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def remove_segment_tool(project: str, experiment: str, name: str) -> str:
    """Removes a segment from an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The name of the segment to remove.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        # Finds and removes segment
        original_count = len(config.segments)
        config.segments = [seg for seg in config.segments if seg.name != name]

        if len(config.segments) == original_count:
            return f"Error: Segment '{name}' not found."

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Removed segment: {name}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def add_water_reward_trial_tool(
    project: str,
    experiment: str,
    name: str,
    segment_name: str,
    stimulus_trigger_zone_start_cm: float,
    stimulus_trigger_zone_end_cm: float,
    stimulus_location_cm: float,
    reward_size_ul: float = 5.0,
    reward_tone_duration_ms: int = 300,
    show_stimulus_collision_boundary: bool = False,
) -> str:
    """Adds a water reward (reinforcing) trial structure to an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The trial structure name.
        segment_name: The segment this trial is based on.
        stimulus_trigger_zone_start_cm: Start of the trigger zone in cm.
        stimulus_trigger_zone_end_cm: End of the trigger zone in cm.
        stimulus_location_cm: Location of the stimulus boundary in cm.
        reward_size_ul: Water reward volume in microliters.
        reward_tone_duration_ms: Auditory tone duration in milliseconds.
        show_stimulus_collision_boundary: Whether to show the boundary marker.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        # Checks for duplicate name
        if name in config.trial_structures:
            return f"Error: Trial '{name}' already exists."

        # Validates segment reference
        segment_names = {seg.name for seg in config.segments}
        if segment_name not in segment_names:
            return f"Error: Unknown segment '{segment_name}'. Available: {sorted(segment_names)}"

        # Adds new trial
        new_trial = WaterRewardTrial(
            segment_name=segment_name,
            stimulus_trigger_zone_start_cm=stimulus_trigger_zone_start_cm,
            stimulus_trigger_zone_end_cm=stimulus_trigger_zone_end_cm,
            stimulus_location_cm=stimulus_location_cm,
            reward_size_ul=reward_size_ul,
            reward_tone_duration_ms=reward_tone_duration_ms,
            show_stimulus_collision_boundary=show_stimulus_collision_boundary,
        )
        config.trial_structures[name] = new_trial

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Added water reward trial: {name} (segment={segment_name}, reward={reward_size_ul}ul)"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def add_gas_puff_trial_tool(
    project: str,
    experiment: str,
    name: str,
    segment_name: str,
    stimulus_trigger_zone_start_cm: float,
    stimulus_trigger_zone_end_cm: float,
    stimulus_location_cm: float,
    puff_duration_ms: int = 100,
    occupancy_duration_ms: int = 1000,
    show_stimulus_collision_boundary: bool = False,
) -> str:
    """Adds a gas puff (aversive) trial structure to an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The trial structure name.
        segment_name: The segment this trial is based on.
        stimulus_trigger_zone_start_cm: Start of the trigger zone in cm.
        stimulus_trigger_zone_end_cm: End of the trigger zone in cm.
        stimulus_location_cm: Location of the stimulus boundary in cm.
        puff_duration_ms: Gas puff duration in milliseconds.
        occupancy_duration_ms: Required zone occupancy time in milliseconds.
        show_stimulus_collision_boundary: Whether to show the boundary marker.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        # Checks for duplicate name
        if name in config.trial_structures:
            return f"Error: Trial '{name}' already exists."

        # Validates segment reference
        segment_names = {seg.name for seg in config.segments}
        if segment_name not in segment_names:
            return f"Error: Unknown segment '{segment_name}'. Available: {sorted(segment_names)}"

        # Adds new trial
        new_trial = GasPuffTrial(
            segment_name=segment_name,
            stimulus_trigger_zone_start_cm=stimulus_trigger_zone_start_cm,
            stimulus_trigger_zone_end_cm=stimulus_trigger_zone_end_cm,
            stimulus_location_cm=stimulus_location_cm,
            puff_duration_ms=puff_duration_ms,
            occupancy_duration_ms=occupancy_duration_ms,
            show_stimulus_collision_boundary=show_stimulus_collision_boundary,
        )
        config.trial_structures[name] = new_trial

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Added gas puff trial: {name} (segment={segment_name}, puff={puff_duration_ms}ms)"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def remove_trial_tool(project: str, experiment: str, name: str) -> str:
    """Removes a trial structure from an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The name of the trial to remove.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        if name not in config.trial_structures:
            return f"Error: Trial '{name}' not found."

        del config.trial_structures[name]

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Removed trial: {name}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def add_experiment_state_tool(
    project: str,
    experiment: str,
    name: str,
    experiment_state_code: int,
    system_state_code: int,
    state_duration_s: float,
    supports_trials: bool = True,
    reinforcing_initial_guided_trials: int = 0,
    reinforcing_recovery_failed_threshold: int = 0,
    reinforcing_recovery_guided_trials: int = 0,
    aversive_initial_guided_trials: int = 0,
    aversive_recovery_failed_threshold: int = 0,
    aversive_recovery_guided_trials: int = 0,
) -> str:
    """Adds an experiment state (phase) to an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The state name (e.g., 'baseline', 'experiment', 'cooldown').
        experiment_state_code: Unique identifier code for this state.
        system_state_code: Data acquisition system state code.
        state_duration_s: Duration of this state in seconds.
        supports_trials: Whether trials occur during this state.
        reinforcing_initial_guided_trials: Initial guided water reward trials.
        reinforcing_recovery_failed_threshold: Failed trials before recovery mode.
        reinforcing_recovery_guided_trials: Guided trials in recovery mode.
        aversive_initial_guided_trials: Initial guided gas puff trials.
        aversive_recovery_failed_threshold: Failed aversive trials before recovery.
        aversive_recovery_guided_trials: Guided aversive trials in recovery mode.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        # Checks for duplicate name
        if name in config.experiment_states:
            return f"Error: State '{name}' already exists."

        # Adds new state
        new_state = MesoscopeExperimentState(
            experiment_state_code=experiment_state_code,
            system_state_code=system_state_code,
            state_duration_s=state_duration_s,
            supports_trials=supports_trials,
            reinforcing_initial_guided_trials=reinforcing_initial_guided_trials,
            reinforcing_recovery_failed_threshold=reinforcing_recovery_failed_threshold,
            reinforcing_recovery_guided_trials=reinforcing_recovery_guided_trials,
            aversive_initial_guided_trials=aversive_initial_guided_trials,
            aversive_recovery_failed_threshold=aversive_recovery_failed_threshold,
            aversive_recovery_guided_trials=aversive_recovery_guided_trials,
        )
        config.experiment_states[name] = new_state

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Added state: {name} (code={experiment_state_code}, duration={state_duration_s}s)"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def update_experiment_state_tool(
    project: str,
    experiment: str,
    name: str,
    experiment_state_code: int | None = None,
    system_state_code: int | None = None,
    state_duration_s: float | None = None,
    supports_trials: bool | None = None,
    reinforcing_initial_guided_trials: int | None = None,
    reinforcing_recovery_failed_threshold: int | None = None,
    reinforcing_recovery_guided_trials: int | None = None,
    aversive_initial_guided_trials: int | None = None,
    aversive_recovery_failed_threshold: int | None = None,
    aversive_recovery_guided_trials: int | None = None,
) -> str:
    """Updates an existing experiment state with new values.

    Only provided parameters are updated; others remain unchanged.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The name of the state to update.
        experiment_state_code: New experiment state code (optional).
        system_state_code: New system state code (optional).
        state_duration_s: New duration in seconds (optional).
        supports_trials: New trials support flag (optional).
        reinforcing_initial_guided_trials: New initial guided trials (optional).
        reinforcing_recovery_failed_threshold: New failed threshold (optional).
        reinforcing_recovery_guided_trials: New recovery guided trials (optional).
        aversive_initial_guided_trials: New aversive initial trials (optional).
        aversive_recovery_failed_threshold: New aversive threshold (optional).
        aversive_recovery_guided_trials: New aversive recovery trials (optional).

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        if name not in config.experiment_states:
            return f"Error: State '{name}' not found."

        state = config.experiment_states[name]

        # Updates only provided parameters
        if experiment_state_code is not None:
            state.experiment_state_code = experiment_state_code
        if system_state_code is not None:
            state.system_state_code = system_state_code
        if state_duration_s is not None:
            state.state_duration_s = state_duration_s
        if supports_trials is not None:
            state.supports_trials = supports_trials
        if reinforcing_initial_guided_trials is not None:
            state.reinforcing_initial_guided_trials = reinforcing_initial_guided_trials
        if reinforcing_recovery_failed_threshold is not None:
            state.reinforcing_recovery_failed_threshold = reinforcing_recovery_failed_threshold
        if reinforcing_recovery_guided_trials is not None:
            state.reinforcing_recovery_guided_trials = reinforcing_recovery_guided_trials
        if aversive_initial_guided_trials is not None:
            state.aversive_initial_guided_trials = aversive_initial_guided_trials
        if aversive_recovery_failed_threshold is not None:
            state.aversive_recovery_failed_threshold = aversive_recovery_failed_threshold
        if aversive_recovery_guided_trials is not None:
            state.aversive_recovery_guided_trials = aversive_recovery_guided_trials

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Updated state: {name}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def remove_experiment_state_tool(project: str, experiment: str, name: str) -> str:
    """Removes an experiment state from an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        name: The name of the state to remove.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        if name not in config.experiment_states:
            return f"Error: State '{name}' not found."

        del config.experiment_states[name]

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Removed state: {name}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def set_vr_environment_tool(
    project: str,
    experiment: str,
    corridor_spacing_cm: float = 20.0,
    segments_per_corridor: int = 3,
    padding_prefab_name: str = "Padding",
    cm_per_unity_unit: float = 10.0,
) -> str:
    """Configures the VR environment settings for an experiment.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        corridor_spacing_cm: Horizontal spacing between corridor instances.
        segments_per_corridor: Number of visible segments per corridor.
        padding_prefab_name: Unity prefab name for corridor padding.
        cm_per_unity_unit: Centimeters per Unity unit conversion factor.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        config.vr_environment = VREnvironment(
            corridor_spacing_cm=corridor_spacing_cm,
            segments_per_corridor=segments_per_corridor,
            padding_prefab_name=padding_prefab_name,
            cm_per_unity_unit=cm_per_unity_unit,
        )

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"VR environment updated: spacing={corridor_spacing_cm}cm, depth={segments_per_corridor}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def set_experiment_metadata_tool(
    project: str,
    experiment: str,
    unity_scene_name: str | None = None,
    cue_offset_cm: float | None = None,
) -> str:
    """Updates experiment metadata (scene name and cue offset).

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        unity_scene_name: The Unity scene name (optional).
        cue_offset_cm: The cue offset in centimeters (optional).

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        if unity_scene_name is not None:
            config.unity_scene_name = unity_scene_name
        if cue_offset_cm is not None:
            config.cue_offset_cm = cue_offset_cm

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Experiment metadata updated: scene={config.unity_scene_name}, offset={config.cue_offset_cm}cm"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def validate_experiment_configuration_tool(project: str, experiment: str) -> str:
    """Validates an experiment configuration for completeness and correctness.

    Checks that all required components are present and properly configured.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.

    Returns:
        A validation summary with any warnings or errors.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)
        issues: list[str] = []

        # Checks for minimum required components
        if len(config.cues) < 1:
            issues.append("No cues defined")
        if len(config.segments) < 1:
            issues.append("No segments defined")
        if len(config.trial_structures) < 1:
            issues.append("No trial structures defined")
        if len(config.experiment_states) < 1:
            issues.append("No experiment states defined")

        # Checks Unity scene name
        if not config.unity_scene_name:
            issues.append("Unity scene name is empty")

        # Validates segment cue references
        cue_names = {cue.name for cue in config.cues}
        for seg in config.segments:
            for cue_name in seg.cue_sequence:
                if cue_name not in cue_names:
                    issues.append(f"Segment '{seg.name}' references unknown cue '{cue_name}'")

        # Validates trial segment references
        segment_names = {seg.name for seg in config.segments}
        for trial_name, trial in config.trial_structures.items():
            if trial.segment_name not in segment_names:
                issues.append(f"Trial '{trial_name}' references unknown segment '{trial.segment_name}'")

        if issues:
            return f"Validation failed with {len(issues)} issue(s):\n- " + "\n- ".join(issues)

        return (
            f"Validation passed: {len(config.cues)} cues, {len(config.segments)} segments, "
            f"{len(config.trial_structures)} trials, {len(config.experiment_states)} states"
        )
    except FileNotFoundError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Validation error: {e}"


@mcp.tool()
def list_experiment_cues_tool(project: str, experiment: str) -> str:
    """Lists all cues defined in an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.

    Returns:
        A formatted list of cues or an error message.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)
        if not config.cues:
            return "No cues defined"

        cue_list = [f"{cue.name} (code={cue.code}, length={cue.length_cm}cm)" for cue in config.cues]
        return "Cues:\n- " + "\n- ".join(cue_list)
    except FileNotFoundError as e:
        return f"Error: {e}"


@mcp.tool()
def list_experiment_segments_tool(project: str, experiment: str) -> str:
    """Lists all segments defined in an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.

    Returns:
        A formatted list of segments or an error message.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)
        if not config.segments:
            return "No segments defined"

        seg_list = [f"{seg.name}: {' -> '.join(seg.cue_sequence)}" for seg in config.segments]
        return "Segments:\n- " + "\n- ".join(seg_list)
    except FileNotFoundError as e:
        return f"Error: {e}"


@mcp.tool()
def list_experiment_trials_tool(project: str, experiment: str) -> str:
    """Lists all trial structures defined in an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.

    Returns:
        A formatted list of trials or an error message.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)
        if not config.trial_structures:
            return "No trials defined"

        trial_list = []
        for name, trial in config.trial_structures.items():
            trial_type = "Water Reward" if isinstance(trial, WaterRewardTrial) else "Gas Puff"
            trial_list.append(f"{name} ({trial_type}): segment={trial.segment_name}")
        return "Trials:\n- " + "\n- ".join(trial_list)
    except FileNotFoundError as e:
        return f"Error: {e}"


@mcp.tool()
def list_experiment_states_tool(project: str, experiment: str) -> str:
    """Lists all experiment states defined in an experiment configuration.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.

    Returns:
        A formatted list of states or an error message.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)
        if not config.experiment_states:
            return "No states defined"

        state_list = [
            f"{name} (code={state.experiment_state_code}, duration={state.state_duration_s}s, trials={state.supports_trials})"
            for name, state in config.experiment_states.items()
        ]
        return "States:\n- " + "\n- ".join(state_list)
    except FileNotFoundError as e:
        return f"Error: {e}"


def run_server(transport: str = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)
