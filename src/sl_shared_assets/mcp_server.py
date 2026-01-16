"""Provides the MCP server for agentic configuration of Sun lab data workflow components.

This module exposes tools that enable AI agents to interactively build complex experiment and system configurations
through a template-then-edit workflow. The server supports both read operations (querying current state) and write
operations (creating and modifying configurations).
"""

import json
from typing import Literal
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from ataraxis_base_utilities import ensure_directory_exists

from .configuration import (
    GasPuffTrial,
    TaskTemplate,
    WaterRewardTrial,
    AcquisitionSystems,
    ServerConfiguration,
    MesoscopeExperimentState,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory as _set_working_directory,
    get_server_configuration,
    get_google_credentials_path,
    set_google_credentials_path as _set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory as _set_task_templates_directory,
    get_system_configuration_data,
    create_experiment_configuration,
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


def _get_system_config_path() -> Path:
    """Resolves the path to the system configuration file.

    Returns:
        The path to the system configuration YAML file.

    Raises:
        FileNotFoundError: If no system configuration file exists.
    """
    working_dir = get_working_directory()
    config_dir = working_dir.joinpath("configuration")
    config_files = list(config_dir.glob("*_system_configuration.yaml"))
    if len(config_files) != 1:
        message = f"Expected exactly one system configuration file, found {len(config_files)}"
        raise FileNotFoundError(message)
    return config_files[0]


def _save_system_config(config: MesoscopeSystemConfiguration) -> None:
    """Saves a system configuration to disk.

    Args:
        config: The system configuration to save.
    """
    config_path = _get_system_config_path()
    config.save(path=config_path)


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
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        return f"Working directory: {path}"


@mcp.tool()
def get_system_configuration_tool() -> str:
    """Returns the current data acquisition system configuration.

    Returns:
        The system configuration as a formatted string, or an error message if not configured.
    """
    try:
        config = get_system_configuration_data()
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"System: {config.name} | Root: {config.filesystem.root_directory}"


@mcp.tool()
def get_server_configuration_tool() -> str:
    """Returns the current compute server configuration (password masked for security).

    Returns:
        The server configuration summary, or an error message if not configured.
    """
    try:
        config = get_server_configuration()
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Server: {config.host} | User: {config.username} | Storage: {config.storage_root}"


@mcp.tool()
def get_google_credentials_tool() -> str:
    """Returns the path to the Google service account credentials file.

    Returns:
        The credentials file path, or an error message if not configured.
    """
    try:
        path = get_google_credentials_path()
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        return f"Google credentials: {path}"


@mcp.tool()
def get_task_templates_directory_tool() -> str:
    """Returns the path to the sl-unity-tasks project's Configurations (Template) directory.

    Returns:
        The task templates directory path, or an error message if not configured.
    """
    try:
        path = get_task_templates_directory()
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        return f"Task templates directory: {path}"


@mcp.tool()
def list_available_templates_tool() -> str:
    """Lists all available task templates in the configured templates directory.

    Returns:
        A formatted list of available template names, or an error message if not configured.
    """
    try:
        templates_dir = get_task_templates_directory()
        templates = sorted([f.stem for f in templates_dir.glob("*.yaml")])
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        if not templates:
            return f"No templates found in {templates_dir}"
        return "Available templates:\n- " + "\n- ".join(templates)


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
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error loading template: {e}"
    else:
        return (
            f"Template: {template_name}\n"
            f"Cue offset: {template.cue_offset_cm}cm\n"
            f"Cues: {cue_summary}\n"
            f"Segments: {segment_summary}\n"
            f"Trial structures:\n  - " + "\n  - ".join(trial_summary)
        )


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
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        return (
            f"Experiment: {experiment} | Scene: {config.unity_scene_name} | "
            f"Cues: {cue_count} | Segments: {segment_count} | Trials: {trial_count} | States: {state_count}"
        )


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
    except Exception as e:
        return f"Error: {e}"
    else:
        return f"Working directory set to: {path}"


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
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Google credentials path set to: {path}"


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
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Task templates directory set to: {path}"


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
    except (ValueError, FileNotFoundError) as e:
        return f"Error: {e}"
    else:
        return f"System configuration created for: {system}"


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
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Project '{project}' created at: {project_path.parent}"


# ==============================================================================================================
# System Configuration - Query and update acquisition system settings
# ==============================================================================================================


@mcp.tool()
def list_system_configuration_sections_tool() -> str:
    """Lists all configurable sections of the system configuration.

    Returns:
        A formatted list of configuration sections and their descriptions.
    """
    sections = [
        "filesystem - Directory paths for data storage (root, server, NAS, mesoscope)",
        "sheets - Google Sheets identifiers (surgery, water log)",
        "cameras - Video camera settings (indices, quantization, presets)",
        "microcontrollers - Hardware calibration (ports, sensors, encoders, valves)",
        "assets - External hardware (Zaber motors, MQTT broker)",
    ]
    return "System configuration sections:\n- " + "\n- ".join(sections)


@mcp.tool()
def get_filesystem_configuration_tool() -> str:
    """Returns the filesystem configuration section of the system configuration.

    Returns:
        The filesystem configuration details, or an error message if not configured.
    """
    try:
        config = get_system_configuration_data()
        fs = config.filesystem
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return (
            f"Filesystem Configuration:\n"
            f"  root_directory: {fs.root_directory}\n"
            f"  server_directory: {fs.server_directory}\n"
            f"  nas_directory: {fs.nas_directory}\n"
            f"  mesoscope_directory: {fs.mesoscope_directory}"
        )


@mcp.tool()
def get_sheets_configuration_tool() -> str:
    """Returns the Google Sheets configuration section of the system configuration.

    Returns:
        The Google Sheets configuration details, or an error message if not configured.
    """
    try:
        config = get_system_configuration_data()
        sheets = config.sheets
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return (
            f"Google Sheets Configuration:\n"
            f"  surgery_sheet_id: {sheets.surgery_sheet_id or '(not set)'}\n"
            f"  water_log_sheet_id: {sheets.water_log_sheet_id or '(not set)'}"
        )


@mcp.tool()
def get_cameras_configuration_tool() -> str:
    """Returns the cameras configuration section of the system configuration.

    Returns:
        The cameras configuration details, or an error message if not configured.
    """
    try:
        config = get_system_configuration_data()
        cam = config.cameras
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return (
            f"Cameras Configuration:\n"
            f"  face_camera_index: {cam.face_camera_index}\n"
            f"  body_camera_index: {cam.body_camera_index}\n"
            f"  face_camera_quantization: {cam.face_camera_quantization}\n"
            f"  face_camera_preset: {cam.face_camera_preset}\n"
            f"  body_camera_quantization: {cam.body_camera_quantization}\n"
            f"  body_camera_preset: {cam.body_camera_preset}"
        )


@mcp.tool()
def get_microcontrollers_configuration_tool() -> str:
    """Returns the microcontrollers configuration section of the system configuration.

    Returns:
        The microcontrollers configuration details, or an error message if not configured.
    """
    try:
        config = get_system_configuration_data()
        mc = config.microcontrollers
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return (
            f"Microcontrollers Configuration:\n"
            f"  Ports:\n"
            f"    actor_port: {mc.actor_port}\n"
            f"    sensor_port: {mc.sensor_port}\n"
            f"    encoder_port: {mc.encoder_port}\n"
            f"  Timing:\n"
            f"    keepalive_interval_ms: {mc.keepalive_interval_ms}\n"
            f"    sensor_polling_delay_ms: {mc.sensor_polling_delay_ms}\n"
            f"  Wheel:\n"
            f"    wheel_diameter_cm: {mc.wheel_diameter_cm}\n"
            f"    wheel_encoder_ppr: {mc.wheel_encoder_ppr}\n"
            f"  Brake:\n"
            f"    minimum_brake_strength_g_cm: {mc.minimum_brake_strength_g_cm}\n"
            f"    maximum_brake_strength_g_cm: {mc.maximum_brake_strength_g_cm}\n"
            f"  Lick Sensor:\n"
            f"    lick_threshold_adc: {mc.lick_threshold_adc}\n"
            f"    lick_signal_threshold_adc: {mc.lick_signal_threshold_adc}\n"
            f"    lick_delta_threshold_adc: {mc.lick_delta_threshold_adc}\n"
            f"    lick_averaging_pool_size: {mc.lick_averaging_pool_size}\n"
            f"  Torque Sensor:\n"
            f"    torque_baseline_voltage_adc: {mc.torque_baseline_voltage_adc}\n"
            f"    torque_maximum_voltage_adc: {mc.torque_maximum_voltage_adc}\n"
            f"    torque_sensor_capacity_g_cm: {mc.torque_sensor_capacity_g_cm}\n"
            f"  Valve Calibration: {dict(mc.valve_calibration_data)}"
        )


@mcp.tool()
def get_external_assets_configuration_tool() -> str:
    """Returns the external assets configuration section of the system configuration.

    Returns:
        The external assets configuration details, or an error message if not configured.
    """
    try:
        config = get_system_configuration_data()
        assets = config.assets
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return (
            f"External Assets Configuration:\n"
            f"  Zaber Motors:\n"
            f"    headbar_port: {assets.headbar_port}\n"
            f"    lickport_port: {assets.lickport_port}\n"
            f"    wheel_port: {assets.wheel_port}\n"
            f"  MQTT Broker:\n"
            f"    unity_ip: {assets.unity_ip}\n"
            f"    unity_port: {assets.unity_port}"
        )


@mcp.tool()
def update_filesystem_configuration_tool(
    root_directory: str | None = None,
    server_directory: str | None = None,
    nas_directory: str | None = None,
    mesoscope_directory: str | None = None,
) -> str:
    """Updates the filesystem configuration section.

    Only provided parameters are updated; others remain unchanged.

    Args:
        root_directory: Path to the main data acquisition PC storage directory.
        server_directory: Path to the mounted remote compute server directory.
        nas_directory: Path to the mounted NAS backup storage directory.
        mesoscope_directory: Path to the mounted mesoscope data aggregation directory.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()

        if root_directory is not None:
            config.filesystem.root_directory = Path(root_directory)
        if server_directory is not None:
            config.filesystem.server_directory = Path(server_directory)
        if nas_directory is not None:
            config.filesystem.nas_directory = Path(nas_directory)
        if mesoscope_directory is not None:
            config.filesystem.mesoscope_directory = Path(mesoscope_directory)

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Filesystem configuration updated successfully."


@mcp.tool()
def update_sheets_configuration_tool(
    surgery_sheet_id: str | None = None,
    water_log_sheet_id: str | None = None,
) -> str:
    """Updates the Google Sheets configuration section.

    Only provided parameters are updated; others remain unchanged.

    Args:
        surgery_sheet_id: The Google Sheet ID for surgery records.
        water_log_sheet_id: The Google Sheet ID for water restriction logs.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()

        if surgery_sheet_id is not None:
            config.sheets.surgery_sheet_id = surgery_sheet_id
        if water_log_sheet_id is not None:
            config.sheets.water_log_sheet_id = water_log_sheet_id

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Google Sheets configuration updated successfully."


@mcp.tool()
def update_cameras_configuration_tool(
    face_camera_index: int | None = None,
    body_camera_index: int | None = None,
    face_camera_quantization: int | None = None,
    face_camera_preset: int | None = None,
    body_camera_quantization: int | None = None,
    body_camera_preset: int | None = None,
) -> str:
    """Updates the cameras configuration section.

    Only provided parameters are updated; others remain unchanged.

    Args:
        face_camera_index: Index of the face camera in the Harvester camera list.
        body_camera_index: Index of the body camera in the Harvester camera list.
        face_camera_quantization: Quantization parameter for face camera encoding.
        face_camera_preset: Encoding speed preset for face camera (0-9).
        body_camera_quantization: Quantization parameter for body camera encoding.
        body_camera_preset: Encoding speed preset for body camera (0-9).

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()

        if face_camera_index is not None:
            config.cameras.face_camera_index = face_camera_index
        if body_camera_index is not None:
            config.cameras.body_camera_index = body_camera_index
        if face_camera_quantization is not None:
            config.cameras.face_camera_quantization = face_camera_quantization
        if face_camera_preset is not None:
            config.cameras.face_camera_preset = face_camera_preset
        if body_camera_quantization is not None:
            config.cameras.body_camera_quantization = body_camera_quantization
        if body_camera_preset is not None:
            config.cameras.body_camera_preset = body_camera_preset

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Cameras configuration updated successfully."


@mcp.tool()
def update_microcontroller_ports_tool(
    actor_port: str | None = None,
    sensor_port: str | None = None,
    encoder_port: str | None = None,
) -> str:
    """Updates the microcontroller USB port assignments.

    Only provided parameters are updated; others remain unchanged.

    Args:
        actor_port: USB port for the Actor microcontroller (e.g., '/dev/ttyACM0').
        sensor_port: USB port for the Sensor microcontroller (e.g., '/dev/ttyACM1').
        encoder_port: USB port for the Encoder microcontroller (e.g., '/dev/ttyACM2').

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()

        if actor_port is not None:
            config.microcontrollers.actor_port = actor_port
        if sensor_port is not None:
            config.microcontrollers.sensor_port = sensor_port
        if encoder_port is not None:
            config.microcontrollers.encoder_port = encoder_port

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Microcontroller ports updated successfully."


@mcp.tool()
def update_wheel_configuration_tool(
    *,
    wheel_diameter_cm: float | None = None,
    wheel_encoder_ppr: int | None = None,
    wheel_encoder_report_cw: bool | None = None,
    wheel_encoder_report_ccw: bool | None = None,
    wheel_encoder_delta_threshold_pulse: int | None = None,
    wheel_encoder_polling_delay_us: int | None = None,
) -> str:
    """Updates the running wheel and encoder configuration.

    Only provided parameters are updated; others remain unchanged.

    Args:
        wheel_diameter_cm: Diameter of the running wheel in centimeters.
        wheel_encoder_ppr: Encoder resolution in pulses per revolution.
        wheel_encoder_report_cw: Whether to report clockwise rotation.
        wheel_encoder_report_ccw: Whether to report counter-clockwise rotation.
        wheel_encoder_delta_threshold_pulse: Minimum pulse change to report.
        wheel_encoder_polling_delay_us: Delay between encoder readings in microseconds.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()
        mc = config.microcontrollers

        if wheel_diameter_cm is not None:
            mc.wheel_diameter_cm = wheel_diameter_cm
        if wheel_encoder_ppr is not None:
            mc.wheel_encoder_ppr = wheel_encoder_ppr
        if wheel_encoder_report_cw is not None:
            mc.wheel_encoder_report_cw = wheel_encoder_report_cw
        if wheel_encoder_report_ccw is not None:
            mc.wheel_encoder_report_ccw = wheel_encoder_report_ccw
        if wheel_encoder_delta_threshold_pulse is not None:
            mc.wheel_encoder_delta_threshold_pulse = wheel_encoder_delta_threshold_pulse
        if wheel_encoder_polling_delay_us is not None:
            mc.wheel_encoder_polling_delay_us = wheel_encoder_polling_delay_us

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Wheel configuration updated successfully."


@mcp.tool()
def update_brake_configuration_tool(
    minimum_brake_strength_g_cm: float | None = None,
    maximum_brake_strength_g_cm: float | None = None,
) -> str:
    """Updates the running wheel brake configuration.

    Only provided parameters are updated; others remain unchanged.

    Args:
        minimum_brake_strength_g_cm: Minimum brake torque in gram-centimeters.
        maximum_brake_strength_g_cm: Maximum brake torque in gram-centimeters.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()
        mc = config.microcontrollers

        if minimum_brake_strength_g_cm is not None:
            mc.minimum_brake_strength_g_cm = minimum_brake_strength_g_cm
        if maximum_brake_strength_g_cm is not None:
            mc.maximum_brake_strength_g_cm = maximum_brake_strength_g_cm

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Brake configuration updated successfully."


@mcp.tool()
def update_lick_sensor_configuration_tool(
    lick_threshold_adc: int | None = None,
    lick_signal_threshold_adc: int | None = None,
    lick_delta_threshold_adc: int | None = None,
    lick_averaging_pool_size: int | None = None,
) -> str:
    """Updates the lick sensor calibration parameters.

    Only provided parameters are updated; others remain unchanged.

    Args:
        lick_threshold_adc: ADC threshold for detecting tongue contact (0-4095).
        lick_signal_threshold_adc: Minimum ADC value reported as non-zero (0-4095).
        lick_delta_threshold_adc: Minimum ADC change to report (0-4095).
        lick_averaging_pool_size: Number of readings to average.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()
        mc = config.microcontrollers

        if lick_threshold_adc is not None:
            mc.lick_threshold_adc = lick_threshold_adc
        if lick_signal_threshold_adc is not None:
            mc.lick_signal_threshold_adc = lick_signal_threshold_adc
        if lick_delta_threshold_adc is not None:
            mc.lick_delta_threshold_adc = lick_delta_threshold_adc
        if lick_averaging_pool_size is not None:
            mc.lick_averaging_pool_size = lick_averaging_pool_size

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Lick sensor configuration updated successfully."


@mcp.tool()
def update_torque_sensor_configuration_tool(
    *,
    torque_baseline_voltage_adc: int | None = None,
    torque_maximum_voltage_adc: int | None = None,
    torque_sensor_capacity_g_cm: float | None = None,
    torque_report_cw: bool | None = None,
    torque_report_ccw: bool | None = None,
    torque_signal_threshold_adc: int | None = None,
    torque_delta_threshold_adc: int | None = None,
    torque_averaging_pool_size: int | None = None,
) -> str:
    """Updates the torque sensor calibration parameters.

    Only provided parameters are updated; others remain unchanged.

    Args:
        torque_baseline_voltage_adc: ADC value corresponding to zero torque (0-4095).
        torque_maximum_voltage_adc: ADC value at maximum detectable torque (0-4095).
        torque_sensor_capacity_g_cm: Maximum torque capacity in gram-centimeters.
        torque_report_cw: Whether to report clockwise torque.
        torque_report_ccw: Whether to report counter-clockwise torque.
        torque_signal_threshold_adc: Minimum ADC value reported as non-zero (0-4095).
        torque_delta_threshold_adc: Minimum ADC change to report (0-4095).
        torque_averaging_pool_size: Number of readings to average.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()
        mc = config.microcontrollers

        if torque_baseline_voltage_adc is not None:
            mc.torque_baseline_voltage_adc = torque_baseline_voltage_adc
        if torque_maximum_voltage_adc is not None:
            mc.torque_maximum_voltage_adc = torque_maximum_voltage_adc
        if torque_sensor_capacity_g_cm is not None:
            mc.torque_sensor_capacity_g_cm = torque_sensor_capacity_g_cm
        if torque_report_cw is not None:
            mc.torque_report_cw = torque_report_cw
        if torque_report_ccw is not None:
            mc.torque_report_ccw = torque_report_ccw
        if torque_signal_threshold_adc is not None:
            mc.torque_signal_threshold_adc = torque_signal_threshold_adc
        if torque_delta_threshold_adc is not None:
            mc.torque_delta_threshold_adc = torque_delta_threshold_adc
        if torque_averaging_pool_size is not None:
            mc.torque_averaging_pool_size = torque_averaging_pool_size

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Torque sensor configuration updated successfully."


@mcp.tool()
def update_valve_calibration_tool(
    calibration_points: str,
) -> str:
    """Updates the water valve calibration data.

    The calibration maps valve open times (microseconds) to water volumes (microliters).

    Args:
        calibration_points: JSON string of calibration data as a list of [time_us, volume_ul] pairs.
            Example: '[[15000, 1.1], [30000, 3.0], [45000, 6.25], [60000, 10.9]]'

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()

        # Parses the JSON string into calibration data.
        data = json.loads(calibration_points)
        if not isinstance(data, list) or not all(isinstance(point, list) and len(point) == 2 for point in data):  # noqa: PLR2004
            return "Error: calibration_points must be a JSON list of [time_us, volume_ul] pairs."

        # Converts to tuple of tuples.
        calibration_tuple = tuple((float(point[0]), float(point[1])) for point in data)
        config.microcontrollers.valve_calibration_data = calibration_tuple

        _save_system_config(config=config)
        point_count = len(calibration_tuple)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON format - {e}"
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Valve calibration updated with {point_count} points."


@mcp.tool()
def update_timing_configuration_tool(
    keepalive_interval_ms: int | None = None,
    sensor_polling_delay_ms: int | None = None,
    screen_trigger_pulse_duration_ms: int | None = None,
    cm_per_unity_unit: float | None = None,
) -> str:
    """Updates the microcontroller timing and VR scale parameters.

    Only provided parameters are updated; others remain unchanged.

    Args:
        keepalive_interval_ms: Keepalive message interval in milliseconds.
        sensor_polling_delay_ms: Delay between sensor readings in milliseconds.
        screen_trigger_pulse_duration_ms: VR screen toggle pulse duration in milliseconds.
        cm_per_unity_unit: Real-world centimeters per Unity distance unit.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()
        mc = config.microcontrollers

        if keepalive_interval_ms is not None:
            mc.keepalive_interval_ms = keepalive_interval_ms
        if sensor_polling_delay_ms is not None:
            mc.sensor_polling_delay_ms = sensor_polling_delay_ms
        if screen_trigger_pulse_duration_ms is not None:
            mc.screen_trigger_pulse_duration_ms = screen_trigger_pulse_duration_ms
        if cm_per_unity_unit is not None:
            mc.cm_per_unity_unit = cm_per_unity_unit

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "Timing configuration updated successfully."


@mcp.tool()
def update_external_assets_configuration_tool(
    headbar_port: str | None = None,
    lickport_port: str | None = None,
    wheel_port: str | None = None,
    unity_ip: str | None = None,
    unity_port: int | None = None,
) -> str:
    """Updates the external assets configuration section.

    Only provided parameters are updated; others remain unchanged.

    Args:
        headbar_port: USB port for the HeadBar Zaber motor (e.g., '/dev/ttyUSB0').
        lickport_port: USB port for the LickPort Zaber motor (e.g., '/dev/ttyUSB1').
        wheel_port: USB port for the Wheel Zaber motor (e.g., '/dev/ttyUSB2').
        unity_ip: IP address of the MQTT broker for Unity communication.
        unity_port: Port number of the MQTT broker for Unity communication.

    Returns:
        A confirmation message or error description.
    """
    try:
        config = get_system_configuration_data()

        if headbar_port is not None:
            config.assets.headbar_port = headbar_port
        if lickport_port is not None:
            config.assets.lickport_port = lickport_port
        if wheel_port is not None:
            config.assets.wheel_port = wheel_port
        if unity_ip is not None:
            config.assets.unity_ip = unity_ip
        if unity_port is not None:
            config.assets.unity_port = unity_port

        _save_system_config(config=config)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return "External assets configuration updated successfully."


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
            password="ENTER_YOUR_PASSWORD_HERE",  # noqa: S106
            host=host,
            storage_root=storage_root,
            working_root=working_root,
            shared_directory_name=shared_directory,
        ).to_yaml(file_path=config_path)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return (
            f"Server configuration template created at: {config_path}\n"
            f"ACTION REQUIRED: Edit the file to replace 'ENTER_YOUR_PASSWORD_HERE' with your actual password.\n"
            f"After editing, use get_server_configuration_tool to validate the configuration."
        )


# ==============================================================================================================
# Experiment Configuration - Template creation and incremental editing
# ==============================================================================================================


@mcp.tool()
def create_experiment_from_template_tool(
    project: str,
    experiment: str,
    template_name: str,
    acquisition_system: str,
    default_reward_size_ul: float = 5.0,
    default_reward_tone_duration_ms: int = 300,
    default_puff_duration_ms: int = 100,
    default_occupancy_duration_ms: int = 1000,
) -> str:
    """Creates a new experiment configuration from a task template for the specified acquisition system.

    The template provides all VR structure (cues, segments, trial zones). Only experiment-specific parameters
    like reward sizes, puff durations, and experiment states can be customized after creation.

    Args:
        project: The name of the project.
        experiment: The name of the experiment.
        template_name: The name of the task template to use (without .yaml extension).
        acquisition_system: The data acquisition system for which to create the configuration (e.g., 'mesoscope').
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

        # Creates experiment configuration from template for the specified acquisition system.
        config = create_experiment_configuration(
            template=task_template,
            system=acquisition_system,
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
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return (
            f"Experiment created for '{acquisition_system}' system from template '{template_name}' at: {config_path}\n"
            f"Trials: {trial_count} ({water_count} water reward, {puff_count} gas puff)\n"
            f"Next: Use add_experiment_state_tool to add experiment states."
        )


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
        result_reward = trial.reward_size_ul
        result_tone = trial.reward_tone_duration_ms
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Updated trial '{trial_name}': reward={result_reward}ul, tone={result_tone}ms"


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
        result_puff = trial.puff_duration_ms
        result_occupancy = trial.occupancy_duration_ms
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Updated trial '{trial_name}': puff={result_puff}ms, occupancy={result_occupancy}ms"


@mcp.tool()
def add_experiment_state_tool(
    project: str,
    experiment: str,
    name: str,
    experiment_state_code: int,
    system_state_code: int,
    state_duration_s: float,
    *,
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
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Added state: {name} (code={experiment_state_code}, duration={state_duration_s}s)"


@mcp.tool()
def update_experiment_state_tool(
    project: str,
    experiment: str,
    name: str,
    *,
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
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Updated state: {name}"


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
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Removed state: {name}"


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
        issues.extend(
            f"Segment '{seg.name}' references unknown cue '{cue_name}'"
            for seg in config.segments
            for cue_name in seg.cue_sequence
            if cue_name not in cue_names
        )

        # Validates trial segment references
        segment_names = {seg.name for seg in config.segments}
        issues.extend(
            f"Trial '{trial_name}' references unknown segment '{trial.segment_name}'"
            for trial_name, trial in config.trial_structures.items()
            if trial.segment_name not in segment_names
        )

        # Captures result data for else block
        cue_count = len(config.cues)
        segment_count = len(config.segments)
        trial_count = len(config.trial_structures)
        state_count = len(config.experiment_states)
    except FileNotFoundError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Validation error: {e}"
    else:
        if issues:
            return f"Validation failed with {len(issues)} issue(s):\n- " + "\n- ".join(issues)
        return (
            f"Validation passed: {cue_count} cues, {segment_count} segments, {trial_count} trials, {state_count} states"
        )


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
        cue_list = [f"{cue.name} (code={cue.code}, length={cue.length_cm}cm)" for cue in config.cues]
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        if not cue_list:
            return "No cues defined"
        return "Cues:\n- " + "\n- ".join(cue_list)


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
        seg_list = [f"{seg.name}: {' -> '.join(seg.cue_sequence)}" for seg in config.segments]
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        if not seg_list:
            return "No segments defined"
        return "Segments:\n- " + "\n- ".join(seg_list)


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
        trial_list = []
        for name, trial in config.trial_structures.items():
            trial_type = "Water Reward" if isinstance(trial, WaterRewardTrial) else "Gas Puff"
            trial_list.append(f"{name} ({trial_type}): segment={trial.segment_name}")
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        if not trial_list:
            return "No trials defined"
        return "Trials:\n- " + "\n- ".join(trial_list)


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
        state_list = [
            f"{name} (code={state.experiment_state_code}, duration={state.state_duration_s}s, "
            f"trials={state.supports_trials})"
            for name, state in config.experiment_states.items()
        ]
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        if not state_list:
            return "No states defined"
        return "States:\n- " + "\n- ".join(state_list)


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)
