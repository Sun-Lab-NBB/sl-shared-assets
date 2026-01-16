"""Provides configuration utilities shared across all data acquisition systems.

This module contains the acquisition systems enumeration, server configuration, path utilities, system configuration
management functions, and experiment configuration factory.
"""

from copy import deepcopy
from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass
from collections.abc import Callable

import appdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from .vr_configuration import TriggerType, TaskTemplate
from .mesoscope_configuration import (
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
)
from .experiment_configuration import GasPuffTrial, WaterRewardTrial


class AcquisitionSystems(StrEnum):
    """Defines the data acquisition systems currently used in the Sun lab."""

    MESOSCOPE_VR = "mesoscope"
    """Uses the 2-Photon Random Access Mesoscope (2P-RAM) with Virtual Reality (VR) environments running in Unity game
    engine to conduct experiments."""


# To add a new acquisition system: (1) add the system to AcquisitionSystems enum above, (2) create the system
# configuration module, (3) add entries to _SYSTEM_CONFIG_CLASSES and _EXPERIMENT_CONFIG_FACTORIES below.

SystemConfiguration = MesoscopeSystemConfiguration
"""Type alias for system configuration classes. Extend this union when adding new systems."""

ExperimentConfiguration = MesoscopeExperimentConfiguration
"""Type alias for experiment configuration classes. Extend this union when adding new systems."""

_SYSTEM_CONFIG_CLASSES: dict[str, type[SystemConfiguration]] = {
    AcquisitionSystems.MESOSCOPE_VR: MesoscopeSystemConfiguration,
}
"""Maps acquisition system names to their system configuration classes."""

_CONFIG_FILE_TO_CLASS: dict[str, type[SystemConfiguration]] = {
    f"{system}_system_configuration.yaml": config_class for system, config_class in _SYSTEM_CONFIG_CLASSES.items()
}
"""Maps configuration file names to their configuration classes."""

ExperimentConfigFactory = Callable[
    [TaskTemplate, str, dict[str, WaterRewardTrial | GasPuffTrial], float],
    ExperimentConfiguration,
]
"""Type alias for experiment configuration factory functions."""

_EXPERIMENT_CONFIG_FACTORIES: dict[str, ExperimentConfigFactory] = {}
"""Maps acquisition system names to their experiment configuration factory functions."""


def _create_mesoscope_experiment_config(
    template: TaskTemplate,
    unity_scene_name: str,
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial],
    cue_offset_cm: float,
) -> MesoscopeExperimentConfiguration:
    """Creates a Mesoscope-VR experiment configuration from a TaskTemplate.

    Args:
        template: The TaskTemplate containing the VR structure.
        unity_scene_name: The Unity scene name for the experiment.
        trial_structures: The converted trial structures dictionary.
        cue_offset_cm: The cue offset in centimeters.

    Returns:
        The initialized MesoscopeExperimentConfiguration instance.
    """
    return MesoscopeExperimentConfiguration(
        cues=deepcopy(template.cues),
        segments=deepcopy(template.segments),
        trial_structures=trial_structures,
        experiment_states={},
        vr_environment=deepcopy(template.vr_environment),
        unity_scene_name=unity_scene_name,
        cue_offset_cm=cue_offset_cm,
    )


_EXPERIMENT_CONFIG_FACTORIES[AcquisitionSystems.MESOSCOPE_VR] = _create_mesoscope_experiment_config


@dataclass
class ServerConfiguration(YamlConfig):
    """Defines the access credentials and the filesystem layout of the Sun lab's remote compute server."""

    username: str = ""
    """The username to use for server authentication."""
    password: str = ""
    """The password to use for server authentication."""
    host: str = "cbsuwsun.biohpc.cornell.edu"
    """The hostname or IP address of the server to connect to."""
    storage_root: str = "/local/storage"
    """The path to the server's storage (slow) HDD RAID volume."""
    working_root: str = "/local/workdir"
    """The path to the server's working (fast) NVME RAID volume."""
    shared_directory_name: str = "sun_data"
    """The name of the shared directory that stores Sun lab's project data on both server volumes."""
    shared_storage_root: str = field(init=False, default_factory=lambda: "/local/storage/sun_data")
    """The path to the root Sun lab's shared directory on the storage server's volume."""
    shared_working_root: str = field(init=False, default_factory=lambda: "/local/workdir/sun_data")
    """The path to the root Sun lab's shared directory on the working server's volume."""
    user_data_root: str = field(init=False, default_factory=lambda: "/local/storage/YourNetID")
    """The path to the root user's directory on the storage server's volume."""
    user_working_root: str = field(init=False, default_factory=lambda: "/local/workdir/YourNetID")
    """The path to the root user's directory on the working server's volume."""

    def __post_init__(self) -> None:
        """Resolves all server-side directory paths."""
        # Stores directory paths as strings, as this is required by the paramiko bindings in the Server class from the
        # sl-forgery library.
        self.shared_storage_root = str(Path(self.storage_root).joinpath(self.shared_directory_name))
        self.shared_working_root = str(Path(self.working_root).joinpath(self.shared_directory_name))
        self.user_data_root = str(Path(self.storage_root).joinpath(f"{self.username}"))
        self.user_working_root = str(Path(self.working_root).joinpath(f"{self.username}"))


def set_working_directory(path: Path) -> None:
    """Sets the specified directory as the Sun lab's working directory for the local machine (PC).

    Notes:
        This function caches the path to the working directory in the user's data directory.

        If the input path does not point to an existing directory, the function creates the requested directory.

    Args:
        path: The path to the directory to set as the local Sun lab's working directory.
    """
    # Resolves the path to the static .txt file used to store the path to the system configuration file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("working_directory_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Ensures that the input path's directory exists
    ensure_directory_exists(path)

    # Also ensures that the working directory contains the 'configuration' subdirectory.
    ensure_directory_exists(path.joinpath("configuration"))

    # Replaces the contents of the working_directory_path.txt file with the provided path
    with path_file.open("w") as f:
        f.write(str(path))

    console.echo(message=f"Sun lab's working directory set to: {path}.", level=LogLevel.SUCCESS)


def get_working_directory() -> Path:
    """Resolves and returns the path to the local Sun lab's working directory.

    Returns:
        The path to the local working directory.

    Raises:
        FileNotFoundError: If the local working directory has not been configured for the host-machine.
    """
    # Uses appdirs to locate the user data directory and resolve the path to the configuration file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("working_directory_path.txt")

    # If the cache file or the Sun lab's data directory does not exist, aborts with an error
    if not path_file.exists():
        message = (
            "Unable to resolve the path to the local Sun lab's working directory, as it has not been set. "
            "Set the local working directory by using the 'sl-configure directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Loads the path to the local working directory
    with path_file.open() as f:
        working_directory = Path(f.read().strip())

    # If the configuration file does not exist, also aborts with an error
    if not working_directory.exists():
        message = (
            "Unable to resolve the path to the local Sun lab's working directory, as the currently configured "
            "directory does not exist at the expected path. Set a new working directory by using the 'sl-configure "
            "directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Returns the path to the working directory
    return working_directory


def set_google_credentials_path(path: Path) -> None:
    """Configures the local machine (PC) to use the provided Google Sheets service account credentials .JSON file for
    all future interactions with the Google's API.

    Notes:
        This function caches the path to the Google Sheets credentials file in the user's data directory.

    Args:
        path: The path to the .JSON file containing the Google Sheets service account credentials.

    Raises:
        FileNotFoundError: If the specified .JSON file does not exist at the provided path.
    """
    # Verifies that the specified credentials file exists
    if not path.exists():
        message = (
            f"Unable to set the Google Sheets credentials path. The specified file ({path}) does not exist. "
            f"Ensure the .JSON credentials file exists at the specified path before calling this function."
        )
        console.error(message=message, error=FileNotFoundError)

    # Verifies that the file has a .json extension
    if path.suffix.lower() != ".json":
        message = (
            f"Unable to set the Google Sheets credentials path. The specified file ({path}) does not have a .json "
            f"extension. Provide the path to the Google Sheets service account credentials .JSON file."
        )
        console.error(message=message, error=ValueError)

    # Resolves the path to the static .txt file used to store the path to the Google Sheets credentials file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("google_credentials_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Writes the absolute path to the credentials file
    with path_file.open("w") as f:
        f.write(str(path.resolve()))


def get_google_credentials_path() -> Path:
    """Resolves and returns the path to the Google service account credentials .JSON file.

    Returns:
        The path to the Google service account credentials .JSON file.

    Raises:
        FileNotFoundError: If the Google service account credentials path has not been configured for the host-machine,
            or if the previously configured credentials file no longer exists at the expected path.
    """
    # Uses appdirs to locate the user data directory and resolve the path to the credentials' path cache file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("google_credentials_path.txt")

    # If the cache file does not exist, aborts with an error
    if not path_file.exists():
        message = (
            "Unable to resolve the path to the Google account credentials file, as it has not been set. "
            "Set the Google service account credentials path by using the 'sl-configure google' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Once the location of the path storage file is resolved, reads the file path from the file
    with path_file.open() as f:
        credentials_path = Path(f.read().strip())

    # If the credentials' file does not exist at the cached path, aborts with an error
    if not credentials_path.exists():
        message = (
            f"Unable to resolve the path to the Google account credentials file, as the previously configured "
            f"credentials file does not exist at the expected path ({credentials_path}). Set a new credentials path "
            f"by using the 'sl-configure google' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Returns the path to the credentials' file
    return credentials_path


def set_task_templates_directory(path: Path) -> None:
    """Configures the local machine (PC) to use the specified directory as the path to the sl-unity-tasks project's
    Configurations (Template) directory.

    Notes:
        This function caches the path to the task templates directory in the user's data directory.

    Args:
        path: The path to the sl-unity-tasks project's Configurations (Template) directory.

    Raises:
        FileNotFoundError: If the specified directory does not exist at the provided path.
    """
    # Verifies that the specified directory exists
    if not path.exists():
        message = (
            f"Unable to set the task templates directory path. The specified directory ({path}) does not exist. "
            f"Ensure the directory exists at the specified path before calling this function."
        )
        console.error(message=message, error=FileNotFoundError)

    # Verifies that the path points to a directory
    if not path.is_dir():
        message = (
            f"Unable to set the task templates directory path. The specified path ({path}) does not point to a "
            f"directory. Provide the path to the sl-unity-tasks project's Configurations (Template) directory."
        )
        console.error(message=message, error=ValueError)

    # Resolves the path to the static .txt file used to store the path to the task templates directory
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("task_templates_directory_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Writes the absolute path to the task templates directory
    with path_file.open("w") as f:
        f.write(str(path.resolve()))

    console.echo(message=f"Task templates directory path set to: {path.resolve()}.", level=LogLevel.SUCCESS)


def get_task_templates_directory() -> Path:
    """Resolves and returns the path to the sl-unity-tasks project's Configurations (Template) directory.

    Returns:
        The path to the task templates directory.

    Raises:
        FileNotFoundError: If the task templates directory path has not been configured for the host-machine, or if
            the previously configured directory no longer exists at the expected path.
    """
    # Uses appdirs to locate the user data directory and resolve the path to the task templates directory cache file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("task_templates_directory_path.txt")

    # If the cache file does not exist, aborts with an error
    if not path_file.exists():
        message = (
            "Unable to resolve the path to the task templates directory, as it has not been set. "
            "Set the task templates directory path by using the 'sl-configure templates' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Once the location of the path storage file is resolved, reads the directory path from the file
    with path_file.open() as f:
        templates_directory = Path(f.read().strip())

    # If the templates directory does not exist at the cached path, aborts with an error
    if not templates_directory.exists():
        message = (
            f"Unable to resolve the path to the task templates directory, as the previously configured "
            f"directory does not exist at the expected path ({templates_directory}). Set a new directory path "
            f"by using the 'sl-configure templates' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Returns the path to the task templates directory
    return templates_directory


def create_system_configuration_file(system: AcquisitionSystems | str) -> None:
    """Creates the .YAML configuration file for the requested Sun lab's data acquisition system and configures the local
    machine (PC) to use this file for all future acquisition-system-related calls.

    Notes:
        This function creates the configuration file inside the local Sun lab's working directory.

    Args:
        system: The name (type) of the data acquisition system for which to create the configuration file.

    Raises:
        ValueError: If the input acquisition system name (type) is not recognized.
    """
    system_str = str(system)
    if system_str not in _SYSTEM_CONFIG_CLASSES:
        supported_systems = list(_SYSTEM_CONFIG_CLASSES.keys())
        message = (
            f"Unable to generate the system configuration file for the acquisition system '{system}'. The specified "
            f"acquisition system is not supported (not recognized). Currently, only the following acquisition systems "
            f"are supported: {', '.join(supported_systems)}."
        )
        console.error(message=message, error=ValueError)

    directory = get_working_directory()
    directory = directory.joinpath("configuration")

    # Removes any existing system configuration files to ensure only one system configuration exists on each machine.
    existing_configs = tuple(directory.glob("*_system_configuration.yaml"))
    for config_file in existing_configs:
        console.echo(f"Removing the existing configuration file {config_file.name}...")
        config_file.unlink()

    config_class = _SYSTEM_CONFIG_CLASSES[system_str]
    configuration = config_class()
    configuration_path = directory.joinpath(f"{system}_system_configuration.yaml")
    configuration.save(path=configuration_path)

    message = (
        f"{system} data acquisition system configuration file: Saved to {configuration_path}. Edit the default "
        f"parameters inside the configuration file to finish configuring the system."
    )
    console.echo(message=message, level=LogLevel.SUCCESS)
    input("Enter anything to continue...")


def get_system_configuration_data() -> SystemConfiguration:
    """Resolves the path to the local data acquisition system configuration file and loads the configuration data as
    a SystemConfiguration instance.

    Returns:
        The initialized SystemConfiguration class instance that stores the loaded configuration parameters.

    Raises:
        FileNotFoundError: If the local machine does not have a valid data acquisition system configuration file.
        ValueError: If the configuration file is not recognized.
    """
    directory = get_working_directory()
    directory = directory.joinpath("configuration")

    config_files = tuple(directory.glob("*_system_configuration.yaml"))

    if len(config_files) != 1:
        file_names = [f.name for f in config_files]
        message = (
            f"Expected a single data acquisition system configuration file to be found inside the local Sun lab's "
            f"working directory ({directory}), but found {len(config_files)} files ({', '.join(file_names)}). Call the "
            f"'sl-configure system' CLI command to reconfigure the host-machine to only contain a single data "
            f"acquisition system configuration file."
        )
        console.error(message=message, error=FileNotFoundError)
        raise FileNotFoundError(message)  # pragma: no cover

    configuration_file = config_files[0]
    file_name = configuration_file.name

    if file_name not in _CONFIG_FILE_TO_CLASS:
        message = (
            f"The data acquisition system configuration file '{file_name}' stored in the local Sun lab's working "
            f"directory is not recognized. Call the 'sl-configure system' CLI command to reconfigure the host-machine "
            f"to use a supported configuration file."
        )
        console.error(message=message, error=ValueError)
        raise ValueError(message)  # pragma: no cover

    configuration_class = _CONFIG_FILE_TO_CLASS[file_name]
    return configuration_class.from_yaml(file_path=configuration_file)


def create_server_configuration_file(
    username: str,
    password: str,
    host: str = "cbsuwsun.biohpc.cornell.edu",
    storage_root: str = "/local/workdir",
    working_root: str = "/local/storage",
    shared_directory_name: str = "sun_data",
) -> None:
    """Creates the .YAML configuration file for the Sun lab compute server and configures the local machine (PC) to use
    this file for all future server-related calls.

    Notes:
        This function creates the configuration file inside the shared Sun lab's working directory on the local machine.

    Args:
        username: The username to use for server authentication.
        password: The password to use for server authentication.
        host: The hostname or IP address of the server to connect to.
        storage_root: The path to the server's storage (slow) HDD RAID volume.
        working_root: The path to the server's working (fast) NVME RAID volume.
        shared_directory_name: The name of the shared directory that stores Sun lab's project data on both server
            volumes.
    """
    output_directory = get_working_directory().joinpath("configuration")
    ServerConfiguration(
        username=username,
        password=password,
        host=host,
        storage_root=storage_root,
        working_root=working_root,
        shared_directory_name=shared_directory_name,
    ).to_yaml(file_path=output_directory.joinpath("server_configuration.yaml"))
    console.echo(message="Server configuration file: Created.", level=LogLevel.SUCCESS)


def get_server_configuration() -> ServerConfiguration:
    """Resolves and returns the Sun lab compute server's configuration data as a ServerConfiguration instance.

    Returns:
        The loaded and validated server configuration data, stored in a ServerConfiguration instance.

    Raises:
        FileNotFoundError: If the configuration file does not exist in the local Sun lab's working directory.
        ValueError: If the configuration file exists, but is not properly configured.
    """
    # Gets the path to the local working directory.
    working_directory = get_working_directory().joinpath("configuration")

    # Resolves the path to the server configuration file.
    config_path = working_directory.joinpath("server_configuration.yaml")

    # Ensures that the configuration file exists.
    if not config_path.exists():
        message = (
            f"Unable to locate the 'server_configuration.yaml' file in the Sun lab's working directory "
            f"{config_path}. Call the 'sl-configure server' CLI command to create the server configuration file."
        )
        console.error(message=message, error=FileNotFoundError)
        raise FileNotFoundError(message)  # Fallback to appease mypy, should not be reachable

    # Loads the configuration file.
    configuration = ServerConfiguration.from_yaml(file_path=config_path)

    # Validates that the configuration is properly set up.
    if configuration.username == "" or configuration.password == "":
        message = (
            "The 'server_configuration.yaml' file appears to be unconfigured or contains placeholder access "
            "credentials. Call the 'sl-configure server' CLI command to reconfigure the server access credentials."
        )
        console.error(message=message, error=ValueError)
        raise ValueError(message)  # Fallback to appease mypy, should not be reachable

    # Returns the loaded configuration data to the caller.
    message = f"Server configuration: Resolved. Using the {configuration.username} account."
    console.echo(message=message, level=LogLevel.SUCCESS)
    return configuration


def create_experiment_configuration(
    template: TaskTemplate,
    system: AcquisitionSystems | str,
    unity_scene_name: str,
    default_reward_size_ul: float = 5.0,
    default_reward_tone_duration_ms: int = 300,
    default_puff_duration_ms: int = 100,
    default_occupancy_duration_ms: int = 1000,
) -> ExperimentConfiguration:
    """Creates an experiment configuration for the specified acquisition system from a TaskTemplate.

    Dispatches to the appropriate system-specific generator based on the system parameter. Converts base TrialStructure
    instances from the template into WaterRewardTrial or GasPuffTrial instances based on each trial's trigger_type
    field.

    Args:
        template: The TaskTemplate containing the VR structure (cues, segments, trial zones) to convert.
        system: The data acquisition system for which to create the configuration.
        unity_scene_name: The Unity scene name for the experiment. Must match the template's scene file name.
        default_reward_size_ul: Water reward volume in microliters for lick-type trials.
        default_reward_tone_duration_ms: Reward tone duration in milliseconds for lick-type trials.
        default_puff_duration_ms: Gas puff duration in milliseconds for occupancy-type trials.
        default_occupancy_duration_ms: Occupancy threshold duration in milliseconds for occupancy-type trials.

    Returns:
        The experiment configuration for the specified acquisition system.

    Notes:
        Trials with trigger_type 'lick' are converted to WaterRewardTrial (GuidanceZone in Unity). Trials with
        trigger_type 'occupancy' are converted to GasPuffTrial (OccupancyZone in Unity).
    """
    system_str = str(system)
    if system_str not in _EXPERIMENT_CONFIG_FACTORIES:
        supported_systems = list(_EXPERIMENT_CONFIG_FACTORIES.keys())
        message = (
            f"Unable to create the experiment configuration for the acquisition system '{system}'. The specified "
            f"acquisition system is not supported. Currently, only the following acquisition systems are supported: "
            f"{', '.join(supported_systems)}."
        )
        console.error(message=message, error=ValueError)

    # Converts base TrialStructure instances to experiment-specific trial types based on trigger_type.
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial] = {}
    for trial_name, base_trial in template.trial_structures.items():
        if base_trial.trigger_type == TriggerType.LICK:
            trial_structures[trial_name] = WaterRewardTrial(
                segment_name=base_trial.segment_name,
                stimulus_trigger_zone_start_cm=base_trial.stimulus_trigger_zone_start_cm,
                stimulus_trigger_zone_end_cm=base_trial.stimulus_trigger_zone_end_cm,
                stimulus_location_cm=base_trial.stimulus_location_cm,
                show_stimulus_collision_boundary=base_trial.show_stimulus_collision_boundary,
                trigger_type=base_trial.trigger_type,
                reward_size_ul=default_reward_size_ul,
                reward_tone_duration_ms=default_reward_tone_duration_ms,
            )
        elif base_trial.trigger_type == TriggerType.OCCUPANCY:
            trial_structures[trial_name] = GasPuffTrial(
                segment_name=base_trial.segment_name,
                stimulus_trigger_zone_start_cm=base_trial.stimulus_trigger_zone_start_cm,
                stimulus_trigger_zone_end_cm=base_trial.stimulus_trigger_zone_end_cm,
                stimulus_location_cm=base_trial.stimulus_location_cm,
                show_stimulus_collision_boundary=base_trial.show_stimulus_collision_boundary,
                trigger_type=base_trial.trigger_type,
                puff_duration_ms=default_puff_duration_ms,
                occupancy_duration_ms=default_occupancy_duration_ms,
            )

    factory = _EXPERIMENT_CONFIG_FACTORIES[system_str]
    return factory(
        template,
        unity_scene_name,
        trial_structures,
        template.cue_offset_cm,
    )
