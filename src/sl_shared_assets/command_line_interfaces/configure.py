"""This module provides the Command-Line Interface (CLI) for configuring major components of the Sun lab data
workflow.
"""

from pathlib import Path  # pragma: no cover

import click  # pragma: no cover
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists  # pragma: no cover

from ..data_classes import (
    Cue,
    Segment,
    GasPuffTrial,
    VREnvironment,
    WaterRewardTrial,
    AcquisitionSystems,
    MesoscopeExperimentState,
    MesoscopeExperimentConfiguration,
    set_working_directory,
    set_google_credentials_path,
    get_system_configuration_data,
    create_server_configuration_file,
    create_system_configuration_file,
)  # pragma: no cover

# Ensures that displayed CLICK help messages are formatted according to the lab standard.
CONTEXT_SETTINGS = {"max_content_width": 120}  # pragma: no cover


@click.group("configure", context_settings=CONTEXT_SETTINGS)
def configure() -> None:  # pragma: no cover
    """This Command-Line Interface allows configuring major components of the Sun lab data workflow."""


@configure.command("directory")
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to cache Sun lab configuration and local runtime data.",
)
def configure_directory(directory: Path) -> None:  # pragma: no cover
    """Sets the input directory as the local Sun lab's working directory."""
    # Creates the directory if it does not exist
    ensure_directory_exists(directory)

    # Sets the directory as the local working directory
    set_working_directory(path=directory)


@configure.command("server")
@click.option(
    "-u",
    "--username",
    type=str,
    required=True,
    help="The username to use for server authentication.",
)
@click.option(
    "-p",
    "--password",
    type=str,
    required=True,
    help="The password to use for server authentication.",
)
@click.option(
    "-h",
    "--host",
    type=str,
    required=True,
    show_default=True,
    default="cbsuwsun.biohpc.cornell.edu",
    help="The host name or IP address of the server.",
)
@click.option(
    "-sr",
    "--storage-root",
    type=str,
    required=True,
    show_default=True,
    default="/local/storage",
    help="The absolute path to to the server's slow HDD RAID volume.",
)
@click.option(
    "-wr",
    "--working-root",
    type=str,
    required=True,
    show_default=True,
    default="/local/workdir",
    help="The absolute path to to the server's fast NVME RAID volume.",
)
@click.option(
    "-sd",
    "--shared-directory",
    type=str,
    required=True,
    show_default=True,
    default="sun_data",
    help="The name of the shared directory used to store all Sun lab's projects on both server's volumes.",
)
def generate_server_configuration_file(
    username: str,
    password: str,
    host: str,
    storage_root: str,
    working_root: str,
    shared_directory: str,
) -> None:  # pragma: no cover
    """Creates the remote compute server configuration file."""
    # Generates the server configuration file.
    create_server_configuration_file(
        username=username,
        password=password,
        host=host,
        storage_root=storage_root,
        working_root=working_root,
        shared_directory_name=shared_directory,
    )


@configure.command("system")
@click.option(
    "-s",
    "--system",
    type=click.Choice(AcquisitionSystems, case_sensitive=False),
    show_default=True,
    required=True,
    default=AcquisitionSystems.MESOSCOPE_VR,
    help="The type (name) of the data acquisition system for which to create the configuration file.",
)
def generate_system_configuration_file(system: AcquisitionSystems) -> None:  # pragma: no cover
    """Creates the specified data acquisition system's configuration file."""
    create_system_configuration_file(system=system)


@configure.command("google")
@click.option(
    "-c",
    "--credentials",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="The absolute path to the Google service account credentials .JSON file.",
)
def configure_google_credentials(credentials: Path) -> None:  # pragma: no cover
    """Sets the path to the Google service account credentials file."""
    # Sets the Google Sheets credentials path
    set_google_credentials_path(path=credentials)

    console.echo(
        message=f"Google Sheets credentials path set to: {credentials.resolve()}.",
        level=LogLevel.SUCCESS,
    )


@configure.command("project")
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project to be created.",
)
def configure_project(project: str) -> None:  # pragma: no cover
    """Configures the local data acquisition system to acquire data for the specified project."""
    # Queries the local data acquisition system configuration.
    system_configuration = get_system_configuration_data()
    project_path = system_configuration.filesystem.root_directory.joinpath(project, "configuration")

    # Generates the project directory hierarchy
    ensure_directory_exists(project_path)
    console.echo(message=f"Project {project} data structure: generated.", level=LogLevel.SUCCESS)


@configure.command("experiment")
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project for which to generate the new experiment configuration file.",
)
@click.option(
    "-e",
    "--experiment",
    type=str,
    required=True,
    help="The name of the experiment for which to create the configuration file.",
)
@click.option(
    "-sc",
    "--state_count",
    type=int,
    required=True,
    help="The number of runtime states supported by the experiment.",
)
@click.option(
    "-wc",
    "--water_reward_count",
    type=int,
    required=True,
    default=0,
    help="The number of water reward (reinforcing) trial types supported by the experiment.",
)
@click.option(
    "-gc",
    "--gas_puff_count",
    type=int,
    required=True,
    default=0,
    help="The number of gas puff (aversive) trial types supported by the experiment.",
)
def generate_experiment_configuration_file(
    project: str, experiment: str, state_count: int, water_reward_count: int, gas_puff_count: int
) -> None:  # pragma: no cover
    """Configures the local data acquisition system to execute the specified project's experiment."""
    # Resolves the acquisition system configuration. Uses the path to the local project directory and the project name
    # to determine where to save the experiment configuration file.
    acquisition_system = get_system_configuration_data()
    file_path = acquisition_system.filesystem.root_directory.joinpath(project, "configuration", f"{experiment}.yaml")

    if not acquisition_system.filesystem.root_directory.joinpath(project).exists():
        message = (
            f"Unable to generate the {experiment} experiment's configuration file as the {acquisition_system.name} "
            f"data acquisition system is currently not configured to acquire data for the {project} project. Use the "
            f"'sl-configure project' CLI command to create the project before creating new experiment configuration(s)."
        )
        console.error(message=message, error=ValueError)
        # Fallback to appease mypy, should not be reachable
        raise ValueError(message)

    # Generates precursor cue definitions
    cues = [
        Cue(name="Gray", code=0, length_cm=30.0),
        Cue(name="A", code=1, length_cm=30.0),
        Cue(name="B", code=2, length_cm=30.0),
        Cue(name="C", code=3, length_cm=30.0),
        Cue(name="D", code=4, length_cm=30.0),
    ]

    # Generates precursor segment definitions
    segments = [
        Segment(
            name="Segment_abcd",
            cue_sequence=["A", "Gray", "B", "Gray", "C", "Gray", "D", "Gray"],
        ),
    ]

    # Generates precursor trial structures for water reward (reinforcing) trials.
    trials: dict[str, WaterRewardTrial | GasPuffTrial] = {}
    trial_names: list[str] = []
    for trial in range(water_reward_count):
        trial_name = f"water_reward_{trial + 1}"
        trial_names.append(trial_name)
        trials[trial_name] = WaterRewardTrial(
            segment_name="Segment_abcd",
            stimulus_trigger_zone_start_cm=208.0,
            stimulus_trigger_zone_end_cm=222.0,
            stimulus_location_cm=208.0,
        )

    # Generates precursor trial structures for gas puff (aversive) trials.
    for trial in range(gas_puff_count):
        trial_name = f"gas_puff_{trial + 1}"
        trial_names.append(trial_name)
        trials[trial_name] = GasPuffTrial(
            segment_name="Segment_abcd",
            stimulus_trigger_zone_start_cm=208.0,
            stimulus_trigger_zone_end_cm=222.0,
            stimulus_location_cm=208.0,
        )

    # Generates a precursor experiment state field inside the 'states' dictionary for each requested experiment state.
    states = {}
    for state in range(state_count):
        states[f"state_{state + 1}"] = MesoscopeExperimentState(
            experiment_state_code=state + 1,  # Assumes experiment state sequences are 1-based
            system_state_code=0,
            state_duration_s=60,
            supports_trials=bool(trial_names),
            reinforcing_initial_guided_trials=3 if water_reward_count > 0 else 0,
            reinforcing_recovery_failed_threshold=9 if water_reward_count > 0 else 0,
            reinforcing_recovery_guided_trials=3 if water_reward_count > 0 else 0,
            aversive_initial_guided_trials=3 if gas_puff_count > 0 else 0,
            aversive_recovery_failed_threshold=9 if gas_puff_count > 0 else 0,
            aversive_recovery_guided_trials=3 if gas_puff_count > 0 else 0,
        )

    # Depending on the acquisition system, packs the resolved data into the experiment configuration class and
    # saves it to the project's configuration directory as a .yaml file.
    if acquisition_system.name == "mesoscope-vr":
        experiment_configuration = MesoscopeExperimentConfiguration(
            cues=cues,
            segments=segments,
            trial_structures=trials,
            experiment_states=states,
            vr_environment=VREnvironment(),
            unity_scene_name="",
            cue_offset_cm=10.0,
        )

    else:
        message = (
            f"Unable to generate the {experiment} experiment's configuration file for the {project} project, as the "
            f"local data acquisition system {acquisition_system.name} is not recognized (not supported). Currently, "
            f"only the following acquisition systems are supported: {','.join(list(AcquisitionSystems))}."
        )
        console.error(message=message, error=ValueError)
        # Fallback to appease mypy, should not be reachable
        raise ValueError(message)

    experiment_configuration.to_yaml(file_path=file_path)
    console.echo(
        message=f"{experiment} experiment's configuration file: created under the {project} project's "
        f"'configuration' directory.",
        level=LogLevel.SUCCESS,
    )
