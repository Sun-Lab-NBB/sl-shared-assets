"""Provides the MCP server for agentic configuration of Sun lab data workflow components.

This module exposes tools that enable AI agents to interactively build complex experiment and system configurations
through a template-then-edit workflow. The server supports both read operations (querying current state) and write
operations (creating and modifying configurations).
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP
from ataraxis_base_utilities import ensure_directory_exists

from .data_classes import (
    GasPuffTrial,
    TaskTemplate,
    WaterRewardTrial,
    AcquisitionSystems,
    ServerConfiguration,
    MesoscopeExperimentState,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory as _set_working_directory,
    get_server_configuration,
    get_google_credentials_path,
    set_google_credentials_path as _set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory as _set_task_templates_directory,
    get_system_configuration_data,
    create_experiment_from_template,
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
def get_task_templates_directory_tool() -> str:
    """Returns the path to the sl-unity-tasks project's Configurations (Template) directory.

    Returns:
        The task templates directory path, or an error message if not configured.
    """
    try:
        path = get_task_templates_directory()
        return f"Task templates directory: {path}"
    except FileNotFoundError as e:
        return f"Error: {e}"


@mcp.tool()
def list_available_templates_tool() -> str:
    """Lists all available task templates in the configured templates directory.

    Returns:
        A formatted list of available template names, or an error message if not configured.
    """
    try:
        templates_dir = get_task_templates_directory()
        templates = sorted([f.stem for f in templates_dir.glob("*.yaml")])
        if not templates:
            return f"No templates found in {templates_dir}"
        return "Available templates:\n- " + "\n- ".join(templates)
    except FileNotFoundError as e:
        return f"Error: {e}"


@mcp.tool()
def get_template_info_tool(template_name: str) -> str:
    """Returns detailed information about a specific task template.

    Args:
        template_name: The name of the template (without .yaml extension).

    Returns:
        A summary of the template contents including cues, segments, and trial structures.
    """
    try:
        templates_dir = get_task_templates_directory()
        template_path = templates_dir.joinpath(f"{template_name}.yaml")
        if not template_path.exists():
            available = sorted([f.stem for f in templates_dir.glob("*.yaml")])
            return f"Error: Template '{template_name}' not found. Available: {', '.join(available)}"

        template = TaskTemplate.from_yaml(file_path=template_path)

        cue_summary = ", ".join([f"{c.name}(code={c.code})" for c in template.cues])
        segment_summary = ", ".join([s.name for s in template.segments])
        trial_summary = []
        for name, trial in template.trial_structures.items():
            trial_summary.append(f"{name} ({trial.trigger_type}): segment={trial.segment_name}")

        return (
            f"Template: {template_name}\n"
            f"Cue offset: {template.cue_offset_cm}cm\n"
            f"Cues: {cue_summary}\n"
            f"Segments: {segment_summary}\n"
            f"Trial structures:\n  - " + "\n  - ".join(trial_summary)
        )
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error loading template: {e}"


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
def set_task_templates_directory_tool(directory: str) -> str:
    """Sets the path to the sl-unity-tasks project's Configurations (Template) directory.

    Args:
        directory: The absolute path to the task templates directory.

    Returns:
        A confirmation message or error description.
    """
    try:
        path = Path(directory)
        _set_task_templates_directory(path=path)
        return f"Task templates directory set to: {path}"
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
def create_experiment_from_template_tool(
    project: str,
    experiment: str,
    template_name: str,
    default_reward_size_ul: float = 5.0,
    default_reward_tone_duration_ms: int = 300,
    default_puff_duration_ms: int = 100,
    default_occupancy_duration_ms: int = 1000,
) -> str:
    """Creates a new experiment configuration from a task template.

    The template provides all VR structure (cues, segments, trial zones). Only experiment-specific parameters
    like reward sizes, puff durations, and experiment states can be customized after creation.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        template_name: The name of the task template to use (without .yaml extension).
        default_reward_size_ul: Default water reward volume in microliters for lick-type trials.
        default_reward_tone_duration_ms: Default reward tone duration in milliseconds for lick-type trials.
        default_puff_duration_ms: Default gas puff duration in milliseconds for occupancy-type trials.
        default_occupancy_duration_ms: Default occupancy threshold duration in milliseconds.

    Returns:
        A confirmation message with the file path, or an error description.
    """
    try:
        # Verifies project exists.
        system_config = get_system_configuration_data()
        project_path = system_config.filesystem.root_directory.joinpath(project)
        if not project_path.exists():
            return f"Error: Project '{project}' does not exist. Create it first with create_project_tool."

        # Loads the task template.
        templates_dir = get_task_templates_directory()
        template_path = templates_dir.joinpath(f"{template_name}.yaml")
        if not template_path.exists():
            available = sorted([f.stem for f in templates_dir.glob("*.yaml")])
            return f"Error: Template '{template_name}' not found. Available: {', '.join(available)}"

        task_template = TaskTemplate.from_yaml(file_path=template_path)

        # Creates experiment configuration from template.
        config = create_experiment_from_template(
            template=task_template,
            unity_scene_name=template_name,
            default_reward_size_ul=default_reward_size_ul,
            default_reward_tone_duration_ms=default_reward_tone_duration_ms,
            default_puff_duration_ms=default_puff_duration_ms,
            default_occupancy_duration_ms=default_occupancy_duration_ms,
        )

        config_path = _get_experiment_config_path(project=project, experiment=experiment)
        config.to_yaml(file_path=config_path)

        trial_count = len(config.trial_structures)
        water_count = sum(1 for t in config.trial_structures.values() if isinstance(t, WaterRewardTrial))
        puff_count = sum(1 for t in config.trial_structures.values() if isinstance(t, GasPuffTrial))

        return (
            f"Experiment created from template '{template_name}' at: {config_path}\n"
            f"Trials: {trial_count} ({water_count} water reward, {puff_count} gas puff)\n"
            f"Next: Use add_experiment_state_tool to add experiment states."
        )
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def update_water_reward_trial_tool(
    project: str,
    experiment: str,
    trial_name: str,
    reward_size_ul: float | None = None,
    reward_tone_duration_ms: int | None = None,
) -> str:
    """Updates the parameters of a water reward trial.

    Only provided parameters are updated; others remain unchanged.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        trial_name: The name of the trial to update.
        reward_size_ul: New water reward volume in microliters (optional).
        reward_tone_duration_ms: New reward tone duration in milliseconds (optional).

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        if trial_name not in config.trial_structures:
            return f"Error: Trial '{trial_name}' not found."

        trial = config.trial_structures[trial_name]
        if not isinstance(trial, WaterRewardTrial):
            return f"Error: Trial '{trial_name}' is not a water reward trial."

        if reward_size_ul is not None:
            trial.reward_size_ul = reward_size_ul
        if reward_tone_duration_ms is not None:
            trial.reward_tone_duration_ms = reward_tone_duration_ms

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return f"Updated trial '{trial_name}': reward={trial.reward_size_ul}ul, tone={trial.reward_tone_duration_ms}ms"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"


@mcp.tool()
def update_gas_puff_trial_tool(
    project: str,
    experiment: str,
    trial_name: str,
    puff_duration_ms: int | None = None,
    occupancy_duration_ms: int | None = None,
) -> str:
    """Updates the parameters of a gas puff trial.

    Only provided parameters are updated; others remain unchanged.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        trial_name: The name of the trial to update.
        puff_duration_ms: New gas puff duration in milliseconds (optional).
        occupancy_duration_ms: New occupancy threshold duration in milliseconds (optional).

    Returns:
        A confirmation message or error description.
    """
    try:
        config = _load_experiment_config(project=project, experiment=experiment)

        if trial_name not in config.trial_structures:
            return f"Error: Trial '{trial_name}' not found."

        trial = config.trial_structures[trial_name]
        if not isinstance(trial, GasPuffTrial):
            return f"Error: Trial '{trial_name}' is not a gas puff trial."

        if puff_duration_ms is not None:
            trial.puff_duration_ms = puff_duration_ms
        if occupancy_duration_ms is not None:
            trial.occupancy_duration_ms = occupancy_duration_ms

        _save_experiment_config(project=project, experiment=experiment, config=config)
        return (
            f"Updated trial '{trial_name}': puff={trial.puff_duration_ms}ms, occupancy={trial.occupancy_duration_ms}ms"
        )
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
            f"{name} (code={state.experiment_state_code}, duration={state.state_duration_s}s, "
            f"trials={state.supports_trials})"
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
