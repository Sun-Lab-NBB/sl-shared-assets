"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from .tools import verify_session_checksum, generate_project_manifest
from .server import generate_server_credentials
from .data_classes import (
    ExperimentState,
    ProjectConfiguration,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
    get_system_configuration_data,
    set_system_configuration_file,
)


@click.command()
@click.option(
    "-s",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session whose raw data needs to be verified for potential corruption.",
)
def verify_session_integrity(session_path: str) -> None:
    """Checks the integrity of the target session's raw_data folder contents.

    This command assumes that the data has been checksummed during acquisition and contains an ax_checksum.txt file
    that stores the data checksum generated before transferring the data to long-term storage destination. This function
    always verified the integrity of the 'raw_data' directory. It does not work with 'processed_data' or any other
    directories.
    """
    session_path = Path(session_path)
    verify_session_checksum(session_path)
    console.echo(message=f"Session {session_path.name} raw data integrity: verified.", level=LogLevel.SUCCESS)


@click.command()
@click.option(
    "-pr",
    "--project_raw_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the project's directory where raw session data is stored.",
)
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated project manifest file.",
)
@click.option(
    "-pp",
    "--project_processed_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the project's directory where processed session data is stored, if different from the "
        "project's raw session data directory."
    ),
)
def generate_project_manifest_file(
    project_raw_path: str, output_directory: str, project_processed_path: str | None
) -> None:
    """Generates a manifest .feather file that provides information about the data-processing state of all available
    project sessions.

    The manifest file is typically used when batch-processing session data on the remote compute server. It contains the
    comprehensive snapshot of the available project's data in a table-compatible format that can also be transferred
    between machines (as it is cached in a file). Note, this command is generally not intended to be called manually.
    instead, it is primarily designed to be used by higher-order data processing CLI commands exposed by sl-forgery
    library.
    """
    generate_project_manifest(
        raw_project_directory=Path(project_raw_path),
        output_directory=Path(output_directory),
        processed_project_directory=Path(project_processed_path) if project_processed_path else None,
    )
    console.echo(
        message=f"Project {Path(project_raw_path).name} data manifest file: generated.", level=LogLevel.SUCCESS
    )


@click.command()
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated system configuration file.",
)
@click.option(
    "-t",
    "--target_system",
    type=str,
    show_default=True,
    required=True,
    default="Mesoscope-VR",
    help=(
        "The type (name) of the data acquisition system for which to generate the configuration file. Note, currently, "
        "only the following types are supported: Mesoscope-VR."
    ),
)
def generate_system_configuration_file(path: str, target_system: str) -> None:
    """Generates a precursor system configuration file for the target acquisition system and configures all local
    Sun lab libraries to use that file to load the acquisition system configuration data.

    This command is typically used when setting up a new data acquisition system in the lab. The system configuration
    only needs to be specified on the machine (PC) that runs the sl-experiment library and manages the acquisition
    runtime if the system uses multiple machines (PCs). Once the system configuration .yaml file is created via this
    command, editing the configuration parameters in the file will automatically take effect during all following
    runtimes.
    """

    # Verifies that the input path is a valid directory path and, if necessary, creates the directory specified by the
    # path.
    path = Path(path)
    if not path.is_dir():
        message = (
            f"Unable to generate the system configuration file for the system '{target_system}'. The path to "
            f"the output directory ({path}) is not a valid directory path."
        )
        console.error(message=message, error=ValueError)
    else:
        ensure_directory_exists(path)

    # Mesoscope
    if target_system == "Mesoscope-VR":
        file_name = "mesoscope_system_configuration.yaml"
        file_path = path.joinpath(file_name)
        system_configuration = MesoscopeSystemConfiguration()
        system_configuration.save(file_path)
        set_system_configuration_file(file_path)
        message = (
            f"Mesoscope-VR system configuration file: generated. Edit the configuration parameters stored inside the "
            f"{file_name} file to match the state of the acquisition system and use context."
        )
        console.echo(message=message, level=LogLevel.SUCCESS)

    # For unsupported system types, raises an error message
    else:
        message = (
            f"Unable to generate the system configuration file for the system '{target_system}'. The input "
            f"acquisition system is not supported (not recognized). Currently, only the following acquisition "
            f"systems are supported: Mesoscope-VR."
        )
        console.error(message=message, error=ValueError)


@click.command()
@click.option(
    "-o",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated server credentials file.",
)
@click.option(
    "-h",
    "--host",
    type=str,
    required=True,
    show_default=True,
    default="cbsuwsun.biohpc.cornell.edu",
    help="The host name or IP address of the server to connect to.",
)
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
def generate_server_credentials_file(output_directory: str, host: str, username: str, password: str) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This command is used to set up access to compute servers and clusters on new machines (PCs). The data stored inside
    the server_credentials.yaml file generated by this command is used by the Server and Job classes used in many Sun
    lab data processing libraries.
    """
    generate_server_credentials(
        output_directory=Path(output_directory), username=username, password=password, host=host
    )
    message = (
        f"Server access credentials file: generated. If necessary, remember to edit the data acquisition system "
        f"configuration file to include the path to the credentials file generated via this CLI."
    )
    console.echo(message=message, level=LogLevel.SUCCESS)


@click.command()
@click.option(
    "-p",
    "--project_name",
    type=str,
    required=True,
    help="The name of the project to be created.",
)
@click.option(
    "-s",
    "--surgery_log_id",
    type=str,
    required=True,
    help="The 44-symbol alpha-numeric ID code used by teh project's surgery log Google sheet.",
)
@click.option(
    "-w",
    "--water_restriction_log_id",
    type=str,
    required=True,
    help="The 44-symbol alpha-numeric ID code used by teh project's water restriction log Google sheet.",
)
def generate_project_configuration_file(project_name: str, surgery_log_id: str, water_restriction_log_id: str) -> None:
    """Generates a new project directory hierarchy and writes its configuration as a project_configuration.yaml file.

    This command creates new Sun lab projects. Until a project is created in this fashion, all data-acquisition and
    data-processing commands from sl-experiment and sl-forgery libraries targeting the project will not work. This
    command is intended to be called on the main computer of the data-acquisition system(s) used by the project. Note,
    this command assumes that the local machine (PC) is the main PC of a data acquisition system and has a valid
    acquisition system configuration .yaml file.
    """

    # Queries the data acquisition configuration data. Specifically, this is used to get the path to the root
    # directory where all projects are stored on the local machine.
    system_configuration = get_system_configuration_data()
    file_path = system_configuration.paths.root_directory.joinpath(
        project_name, "configuration", "project_configuration.yaml"
    )

    # Generates the initial project directory hierarchy
    ensure_directory_exists(file_path)

    # Saves project configuration data as a .yaml file to the 'configuration' directory of the created project
    configuration = ProjectConfiguration(
        project_name=project_name, surgery_sheet_id=surgery_log_id, water_log_sheet_id=water_restriction_log_id
    )
    configuration.save(path=file_path.joinpath())
    console.echo(
        message=f"Project {project_name} data structure and configuration file: generated.", level=LogLevel.SUCCESS
    )


@click.command()
@click.option(
    "-p",
    "--project_name",
    type=str,
    required=True,
    help="The name of the project for which to generate the new experiment configuration file.",
)
@click.option(
    "-e",
    "--experiment_name",
    type=str,
    required=True,
    help="The name of the generated experiment (and its configuration file).",
)
@click.option(
    "-n",
    "--state_combination_number",
    type=int,
    required=True,
    help="The total number of experiment and acquisition system state combinations in the experiment.",
)
def generate_experiment_configuration_file(
    project_name: str, experiment_name: str, state_combination_number: int
) -> None:
    # Resolves the acquisition system configuration. Uses the path to the local project directory and the project name
    # to determine where to save the experiment configuration file
    acquisition_system = get_system_configuration_data()
    file_path = acquisition_system.paths.root_directory.joinpath(
        project_name, "configuration", f"{experiment_name}.yaml"
    )

    # Loops over the number of requested states and, for each, generates a precursor experiment state field.
    states = {}
    for state in range(1, state_combination_number + 1):
        states[f"state_{state}"] = ExperimentState(
            experiment_state_code=state,
            system_state_code=0,
            state_duration_s=60,
        )

    # Depending on the acquisition system, uses packs state data into the appropriate experiment configuration class and
    # saves it to the project's configuration folder as a .yaml file.
    if acquisition_system.name == "Mesoscope-VR":
        experiment_configuration = MesoscopeExperimentConfiguration(experiment_states=states)

    else:
        message = (
            f"Unable to generate the experiment {experiment_name} configuration file for the project {project_name}. "
            f"The data acquisition system of the local machine (PC) is not supported (not recognized). Currently, only "
            f"the following acquisition systems are supported: Mesoscope-VR."
        )
        console.error(message=message, error=ValueError)
        raise ValueError(message)  # Fall-back to appease mypy, should not be reachable

    experiment_configuration.to_yaml(file_path=file_path)
    console.echo(message=f"Experiment {experiment_name} configuration file: generated.", level=LogLevel.SUCCESS)
