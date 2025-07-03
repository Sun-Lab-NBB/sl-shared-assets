from pathlib import Path
from dataclasses import dataclass

from _typeshed import Incomplete
from simple_slurm import Slurm

@dataclass
class _JupyterConnectionInfo:
    """Stores the data used to establish the connection with a Jupyter notebook server running under SLURM control on a
    remote Sun lab server.

    More specifically, this class is used to transfer the connection metadata collected on the remote server back to
    the local machine that requested the server to be established.
    """

    compute_node: str
    port: int
    token: str
    @property
    def localhost_url(self) -> str:
        """Returns the localhost URL for connecting to the server.

        To use this URL, first set up an SSH tunnel to the server via the specific Jupyter communication port and the
        remote server access credentials.
        """

class Job:
    """Aggregates the data of a single SLURM-managed job to be executed on the Sun lab BioHPC cluster.

    This class provides the API for constructing any server-side job in the Sun lab. Internally, it wraps an instance
    of a Slurm class to package the job data into the format expected by the SLURM job manager. All jobs managed by this
    class instance should be submitted to an initialized Server class 'submit_job' method to be executed on the server.

    Notes:
        The initialization method of the class contains the arguments for configuring the SLURM and Conda environments
        used by the job. Do not submit additional SLURM or Conda commands via the 'add_command' method, as this may
        produce unexpected behavior.

        Each job can be conceptualized as a sequence of shell instructions to execute on the remote compute server. For
        the lab, that means that the bulk of the command consists of calling various CLIs exposed by data processing or
        analysis pipelines, installed in the Conda environment on the server. Other than that, the job contains commands
        for activating the target conda environment and, in some cases, doing other preparatory or cleanup work. The
        source code of a 'remote' job is typically identical to what a human operator would type in a 'local' terminal
        to run the same job on their PC.

        A key feature of server-side jobs is that they are executed on virtual machines managed by SLURM. Since the
        server has a lot more compute and memory resources than likely needed by individual jobs, each job typically
        requests a subset of these resources. Upon being executed, SLURM creates an isolated environment with the
        requested resources and runs the job in that environment.

        Since all jobs are expected to use the CLIs from python packages (pre)installed on the BioHPC server, make sure
        that the target environment is installed and configured before submitting jobs to the server. See notes in
        ReadMe to learn more about configuring server-side conda environments.

    Args:
        job_name: The descriptive name of the SLURM job to be created. Primarily, this name is used in terminal
            printouts to identify the job to human operators.
        output_log: The absolute path to the .txt file on the processing server, where to store the standard output
            data of the job.
        error_log: The absolute path to the .txt file on the processing server, where to store the standard error
            data of the job.
        working_directory: The absolute path to the directory where temporary job files will be stored. During runtime,
            classes from this library use that directory to store files such as the job's shell script. All such files
            are automatically removed from the directory at the end of a non-errors runtime.
        conda_environment: The name of the conda environment to activate on the server before running the job logic. The
            environment should contain the necessary Python packages and CLIs to support running the job's logic.
        cpus_to_use: The number of CPUs to use for the job.
        ram_gb: The amount of RAM to allocate for the job, in Gigabytes.
        time_limit: The maximum time limit for the job, in minutes. If the job is still running at the end of this time
            period, it will be forcibly terminated. It is highly advised to always set adequate maximum runtime limits
            to prevent jobs from hogging the server in case of runtime or algorithm errors.

    Attributes:
        remote_script_path: Stores the path to the script file relative to the root of the remote server that runs the
            command.
        job_id: Stores the unique job identifier assigned by the SLURM manager to this job, when it is accepted for
            execution. This field initialized to None and is overwritten by the Server class that submits the job.
        job_name: Stores the descriptive name of the SLURM job.
        _command: Stores the managed SLURM command object.
    """

    remote_script_path: Incomplete
    job_id: str | None
    job_name: str
    _command: Slurm
    def __init__(
        self,
        job_name: str,
        output_log: Path,
        error_log: Path,
        working_directory: Path,
        conda_environment: str,
        cpus_to_use: int = 10,
        ram_gb: int = 10,
        time_limit: int = 60,
    ) -> None: ...
    def __repr__(self) -> str:
        """Returns the string representation of the Job instance."""
    def add_command(self, command: str) -> None:
        """Adds the input command string to the end of the managed SLURM job command list.

        This method is a wrapper around simple_slurm's 'add_cmd' method. It is used to iteratively build the shell
        command sequence of the job.

        Args:
            command: The command string to add to the command list, e.g.: 'python main.py --input 1'.
        """
    @property
    def command_script(self) -> str:
        """Translates the managed job data into a shell-script-writable string and returns it to caller.

        This method is used by the Server class to translate the job into the format that can be submitted to and
        executed on the remote compute server. Do not call this method manually unless you know what you are doing.
        The returned string is safe to dump into a .sh (shell script) file and move to the BioHPC server for execution.
        """

class JupyterJob(Job):
    """Specialized Job instance designed to launch a Jupyter notebook server on SLURM.

    This class extends the base Job class to include Jupyter-specific configuration and commands for starting a
    notebook server in a SLURM environment. Using this specialized job allows users to set up remote Jupyter servers
    while still benefitting from SLURM's job management and fair airtime policies.

    Notes:
        Jupyter servers directly compete for resources with headless data processing jobs. Therefore, it is important
        to minimize the resource footprint and the runtime of each Jupyter server, if possible.

    Args:
        job_name: The descriptive name of the Jupyter SLURM job to be created. Primarily, this name is used in terminal
            printouts to identify the job to human operators.
        output_log: The absolute path to the .txt file on the processing server, where to store the standard output
            data of the job.
        error_log: The absolute path to the .txt file on the processing server, where to store the standard error
            data of the job.
        working_directory: The absolute path to the directory where temporary job files will be stored. During runtime,
            classes from this library use that directory to store files such as the job's shell script. All such files
            are automatically removed from the directory at the end of a non-errors runtime.
        conda_environment: The name of the conda environment to activate on the server before running the job logic. The
            environment should contain the necessary Python packages and CLIs to support running the job's logic. For
            Jupyter jobs, this necessarily includes the Jupyter notebook and jupyterlab packages.
        port: The connection port number for Jupyter server. Do not change the default value unless you know what you
            are doing, as the server has most common communication ports closed for security reasons.
        notebook_directory: The directory to use as Jupyter's root. During runtime, Jupyter will only have access to
            items stored in or under this directory. For most runtimes, this should be set to the user's root data or
            working directory.
        cpus_to_use: The number of CPUs to allocate to the Jupyter server. Keep this value as small as possible to avoid
            interfering with headless data processing jobs.
        ram_gb: The amount of RAM, in GB, to allocate to the Jupyter server. Keep this value as small as possible to
            avoid interfering with headless data processing jobs.
        time_limit: The maximum Jupyter server uptime, in minutes. Set this to the expected duration of your jupyter
            session.
        jupyter_args: Stores additional arguments to pass to jupyter notebook initialization command.

    Attributes:
        port: Stores the connection port of the managed Jupyter server.
        notebook_dir: Stores the absolute path to the directory used as Jupyter's root, relative to the remote server
            root.
        connection_info: Stores the JupyterConnectionInfo instance after the Jupyter server is instantiated.
        host: Stores the hostname of the remote server.
        user: Stores the username used to connect with the remote server.
        connection_info_file: The absolute path to the file that stores connection information, relative to the remote
            server root.
        _command: Stores the shell command for launching the Jupyter server.
    """

    port: Incomplete
    notebook_dir: Incomplete
    connection_info: _JupyterConnectionInfo | None
    host: str | None
    user: str | None
    connection_info_file: Incomplete
    def __init__(
        self,
        job_name: str,
        output_log: Path,
        error_log: Path,
        working_directory: Path,
        conda_environment: str,
        notebook_directory: Path,
        port: int = 9999,
        cpus_to_use: int = 2,
        ram_gb: int = 32,
        time_limit: int = 120,
        jupyter_args: str = "",
    ) -> None: ...
    def _build_jupyter_command(self, jupyter_args: str) -> None:
        """Builds the command to launch Jupyter notebook server on the remote Sun lab server."""
    def parse_connection_info(self, info_file: Path) -> None:
        """Parses the connection information file created by the Jupyter job on the server.

        Use this method to parse the connection file fetched from the server to finalize setting up the Jupyter
        server job.

        Args:
            info_file: The path to the .txt file generated by the remote server that stores the Jupyter connection
                information to be parsed.
        """
    def print_connection_info(self) -> None:
        """Constructs and displays the command to set up the SSH tunnel to the server and the link to the localhost
        server view in the terminal.

        The SSH command should be used via a separate terminal or subprocess call to establish the secure SSH tunnel to
        the Jupyter server. Once the SSH tunnel is established, the printed localhost url can be used to view the
        server from the local machine.
        """
