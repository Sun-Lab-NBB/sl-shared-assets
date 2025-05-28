"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from .tools import ascend_tyche_data, verify_session_checksum, generate_project_manifest
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
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session whose raw data needs to be verified for potential corruption.",
)
@click.option(
    "-c",
    "--create_processed_directories",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether to created the processed data hierarchy. This flag should be disabled for most runtimes. "
        "Primarily, it is used by lab acquisition system code to generate processed data directories on the remote "
        "compute servers as part of the data preprocessing pipeline."
    ),
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all projects is stored on the machine that runs "
        "this command. This argument is used when calling the CLI on the BioHPC server, which uses different data "
        "volumes for raw and processed data. Note, the input path must point to the root directory, as it will be "
        "automatically modified to include the project name, the animal id, and the session ID. This argument is only "
        "used if 'create_processed_directories' flag is True."
    ),
)
def verify_session_integrity(session_path: str, create_processed_directories: bool, processed_data_root: Path) -> None:
    """Checks the integrity of the target session's raw data (contents of the raw_data directory).

    This command assumes that the data has been checksummed during acquisition and contains an ax_checksum.txt file
    that stores the data checksum generated before transferring the data to long-term storage destination. This function
    always verified the integrity of the 'raw_data' directory. It does not work with 'processed_data' or any other
    directories. If the session data was corrupted, the command removes the 'telomere.bin' file, marking the session as
    'incomplete' and automatically excluding it from all further automated processing runtimes.

    The command is also used by Sun lab data acquisition systems to generate the processed data hierarchy for each
    processed session. This use case is fully automated and should not be triggered manually by the user.
    """
    session = Path(session_path)
    if verify_session_checksum(
        session, create_processed_data_directory=create_processed_directories, processed_data_root=processed_data_root
    ):
        console.echo(message=f"Session {session.stem} raw data integrity: verified.", level=LogLevel.SUCCESS)
    else:
        console.echo(message=f"Session {session.stem} raw data integrity: compromised!", level=LogLevel.ERROR)


@click.command()
@click.option(
    "-pp",
    "--project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the project directory where raw session data is stored.",
)
@click.option(
    "-od",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated project manifest file.",
)
@click.option(
    "-ppp",
    "--project_processed_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the project directory where processed session data is stored, if different from the "
        "directory used to store raw session data. Typically, this extra argument is only used when processing data "
        "stored on remote compute server(s)."
    ),
)
def generate_project_manifest_file(
    project_path: str, output_directory: str, project_processed_path: str | None
) -> None:
    """Generates the manifest .feather file that provides information about the data-processing state of all available
    project sessions.

    The manifest file is typically used when batch-processing session data on the remote compute server. It contains the
    comprehensive snapshot of the available project's data in a table-compatible format that can also be transferred
    between machines (as it is cached in a file).
    """
    generate_project_manifest(
        raw_project_directory=Path(project_path),
        output_directory=Path(output_directory),
        processed_project_directory=Path(project_processed_path) if project_processed_path else None,
    )
    console.echo(message=f"Project {Path(project_path).stem} data manifest file: generated.", level=LogLevel.SUCCESS)


@click.command()
@click.option(
    "-od",
    "--output_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to store the generated system configuration file.",
)
@click.option(
    "-as",
    "--acquisition_system",
    type=str,
    show_default=True,
    required=True,
    default="mesoscope-vr",
    help=(
        "The type (name) of the data acquisition system for which to generate the configuration file. Note, currently, "
        "only the following types are supported: mesoscope-vr."
    ),
)
def generate_system_configuration_file(output_directory: str, acquisition_system: str) -> None:
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
    path = Path(output_directory)
    if not path.is_dir():
        message = (
            f"Unable to generate the system configuration file for the system '{acquisition_system}'. The path to "
            f"the output directory ({path}) is not a valid directory path."
        )
        console.error(message=message, error=ValueError)
    else:
        ensure_directory_exists(path)

    # Mesoscope
    if acquisition_system.lower() == "mesoscope-vr":
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
            f"Unable to generate the system configuration file for the system '{acquisition_system}'. The input "
            f"acquisition system is not supported (not recognized). Currently, only the following acquisition "
            f"systems are supported: mesoscope-vr."
        )
        console.error(message=message, error=ValueError)


@click.command()
@click.option(
    "-od",
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
    "--project",
    type=str,
    required=True,
    help="The name of the project to be created.",
)
@click.option(
    "-sli",
    "--surgery_log_id",
    type=str,
    required=True,
    help="The 44-symbol alpha-numeric ID code used by the project's surgery log Google sheet.",
)
@click.option(
    "-wli",
    "--water_restriction_log_id",
    type=str,
    required=True,
    help="The 44-symbol alpha-numeric ID code used by the project's water restriction log Google sheet.",
)
def generate_project_configuration_file(project: str, surgery_log_id: str, water_restriction_log_id: str) -> None:
    """Generates a new project directory hierarchy and writes its configuration as a project_configuration.yaml file.

    This command creates new Sun lab projects. Until a project is created in this fashion, all data-acquisition and
    data-processing commands from sl-experiment and sl-forgery libraries targeting the project will not work. This
    command is intended to be called on the main computer of the data-acquisition system(s) used by the project. Note,
    this command assumes that the local machine (PC) is the main PC of the data acquisition system and has a valid
    acquisition system configuration .yaml file.
    """

    # Queries the data acquisition configuration data. Specifically, this is used to get the path to the root
    # directory where all projects are stored on the local machine.
    system_configuration = get_system_configuration_data()
    file_path = system_configuration.paths.root_directory.joinpath(
        project, "configuration", "project_configuration.yaml"
    )

    # Generates the initial project directory hierarchy
    ensure_directory_exists(file_path)

    # Saves project configuration data as a .yaml file to the 'configuration' directory of the created project
    configuration = ProjectConfiguration(
        project_name=project, surgery_sheet_id=surgery_log_id, water_log_sheet_id=water_restriction_log_id
    )
    configuration.save(path=file_path.joinpath())
    console.echo(message=f"Project {project} data structure and configuration file: generated.", level=LogLevel.SUCCESS)


@click.command()
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
    help="The name of the experiment. Note, the generated experiment configuration file will also use this name.",
)
@click.option(
    "-sc",
    "--state_count",
    type=int,
    required=True,
    help="The total number of experiment and acquisition system state combinations in the experiment.",
)
def generate_experiment_configuration_file(project: str, experiment: str, state_count: int) -> None:
    """Generates a precursor experiment configuration .yaml file for the target experiment inside the project's
    configuration folder.

    This command assists users in creating new experiment configurations, by statically resolving the structure (layout)
    of the appropriate experiment configuration file for the acquisition system of the local machine (PC). Specifically,
    the generated precursor will contain the correct number of experiment state entries initialized to nonsensical
    default value. The user needs to manually edit the configuration file to properly specify their experiment runtime
    parameters and state transitions before running the experiment. In a sense, this command acts as an 'experiment
    template' generator.
    """

    # Resolves the acquisition system configuration. Uses the path to the local project directory and the project name
    # to determine where to save the experiment configuration file
    acquisition_system = get_system_configuration_data()
    file_path = acquisition_system.paths.root_directory.joinpath(project, "configuration", f"{experiment}.yaml")

    if not acquisition_system.paths.root_directory.joinpath(project).exists():
        message = (
            f"Unable to generate the experiment {experiment} configuration file for the project {project}. "
            f"The target project does not exist on the local machine (PC). Use the "
            f"'sl-create-project' CLI command to create the project before creating new experiment configuration(s). "
        )
        console.error(message=message, error=ValueError)
        raise ValueError(message)  # Fall-back to appease mypy, should not be reachable

    # Loops over the number of requested states and, for each, generates a precursor experiment state field inside the
    # 'states' dictionary.
    states = {}
    for state in range(state_count):
        states[f"state_{state + 1}"] = ExperimentState(
            experiment_state_code=state + 1,  # Assumes experiment state sequences are 1-based
            system_state_code=0,
            state_duration_s=60,
        )

    # Depending on the acquisition system, packs state data into the appropriate experiment configuration class and
    # saves it to the project's configuration folder as a .yaml file.
    if acquisition_system.name == "mesoscope-vr":
        experiment_configuration = MesoscopeExperimentConfiguration(experiment_states=states)

    else:
        message = (
            f"Unable to generate the experiment {experiment} configuration file for the project {project}. "
            f"The data acquisition system of the local machine (PC) is not supported (not recognized). Currently, only "
            f"the following acquisition systems are supported: mesoscope-vr."
        )
        console.error(message=message, error=ValueError)
        raise ValueError(message)  # Fall-back to appease mypy, should not be reachable

    experiment_configuration.to_yaml(file_path=file_path)
    console.echo(message=f"Experiment {experiment} configuration file: generated.", level=LogLevel.SUCCESS)


@click.command()
@click.option(
    "-id",
    "--input_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory that stores original Tyche animal folders.",
)
def ascend_tyche_directory(input_directory: str) -> None:
    """Restructures old Tyche project data to use the modern Sun lab data structure and uploads them to the processing
    server.

    This command is used to convert ('ascend') the old Tyche project data to the modern Sun lab structure. After
    ascension, the data can be processed and analyzed using all modern Sun lab (sl-) tools and libraries. Note, this
    process expects the input data to be preprocessed using an old Sun lab mesoscope data preprocessing pipeline. It
    will not work for any other project or data. Also, this command will only work on a machine (PC) that belongs to a
    valid Sun lab data acquisition system, such as VRPC of the Mesoscope-VR system.
    """
    ascend_tyche_data(root_directory=Path(input_directory))
