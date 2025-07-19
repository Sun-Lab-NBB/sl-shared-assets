from pathlib import Path
from dataclasses import field, dataclass

from _typeshed import Incomplete
from simple_slurm import Slurm as Slurm
from paramiko.client import SSHClient as SSHClient
from ataraxis_data_structures import YamlConfig

from .job import (
    Job as Job,
    JupyterJob as JupyterJob,
)

def generate_server_credentials(
    output_directory: Path,
    username: str,
    password: str,
    host: str = "cbsuwsun.biohpc.cornell.edu",
    storage_root: str = "/local/workdir",
    working_root: str = "/local/storage",
    shared_directory_name: str = "sun_data",
) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This function provides a convenience interface for generating new BioHPC server credential files. Generally, this is
    only used when setting up new host-computers or users in the lab.

    Args:
        output_directory: The directory where to save the generated server_credentials.yaml file.
        username: The username to use for server authentication.
        password: The password to use for server authentication.
        host: The hostname or IP address of the server to connect to.
        storage_root: The path to the root storage (slow) server directory. Typically, this is the path to the
            top-level (root) directory of the HDD RAID volume.
        working_root: The path to the root working (fast) server directory. Typically, this is the path to the
            top-level (root) directory of the NVME RAID volume. If the server uses the same volume for both storage and
            working directories, enter the same path under both 'storage_root' and 'working_root'.
        shared_directory_name: The name of the shared directory used to store all Sun lab project data on the storage
            and working server volumes.
    """
@dataclass()
class ServerCredentials(YamlConfig):
    """This class stores the hostname and credentials used to log into the BioHPC cluster to run Sun lab processing
    pipelines.

    Primarily, this is used as part of the sl-experiment library runtime to start data processing once it is
    transferred to the BioHPC server during preprocessing. However, the same file can be used together with the Server
    class API to run any computation jobs on the lab's BioHPC server.
    """

    username: str = ...
    password: str = ...
    host: str = ...
    storage_root: str = ...
    working_root: str = ...
    shared_directory_name: str = ...
    raw_data_root: str = field(init=False, default_factory=Incomplete)
    processed_data_root: str = field(init=False, default_factory=Incomplete)
    user_data_root: str = field(init=False, default_factory=Incomplete)
    user_working_root: str = field(init=False, default_factory=Incomplete)
    def __post_init__(self) -> None:
        """Statically resolves the paths to end-point directories using provided root directories."""

class Server:
    """Encapsulates access to the Sun lab BioHPC processing server.

    This class provides the API that allows accessing the BioHPC server to create and submit various SLURM-managed jobs
    to the server. It functions as the central interface used by all processing pipelines in the lab to execute costly
    data processing on the server.

    Notes:
        All lab processing pipelines expect the data to be stored on the server and all processing logic to be packaged
        and installed into dedicated conda environments on the server.

        This class assumes that the target server has SLURM job manager installed and accessible to the user whose
        credentials are used to connect to the server as part of this class instantiation.

    Args:
        credentials_path: The path to the locally stored .yaml file that contains the server hostname and access
            credentials.

    Attributes:
        _open: Tracks whether the connection to the server is open or not.
        _client: Stores the initialized SSHClient instance used to interface with the server.
    """

    _open: bool
    _credentials: ServerCredentials
    _client: SSHClient
    def __init__(self, credentials_path: Path) -> None: ...
    def __del__(self) -> None:
        """If the instance is connected to the server, terminates the connection before the instance is destroyed."""
    def create_job(
        self, job_name: str, conda_environment: str, cpus_to_use: int = 10, ram_gb: int = 10, time_limit: int = 60
    ) -> Job:
        """Creates and returns a new Job instance.

        Use this method to generate Job objects for all headless jobs that need to be run on the remote server. The
        generated Job is a precursor that requires further configuration by the user before it can be submitted to the
        server for execution.

        Args:
            job_name: The descriptive name of the SLURM job to be created. Primarily, this name is used in terminal
                printouts to identify the job to human operators.
            conda_environment: The name of the conda environment to activate on the server before running the job logic.
                The environment should contain the necessary Python packages and CLIs to support running the job's
                logic.
            cpus_to_use: The number of CPUs to use for the job.
            ram_gb: The amount of RAM to allocate for the job, in Gigabytes.
            time_limit: The maximum time limit for the job, in minutes. If the job is still running at the end of this
                time period, it will be forcibly terminated. It is highly advised to always set adequate maximum runtime
                limits to prevent jobs from hogging the server in case of runtime or algorithm errors.

        Returns:
            The initialized Job instance pre-filled with SLURM configuration data and conda activation commands. Modify
            the returned instance with any additional commands as necessary for the job to fulfill its intended
            purpose. Note, the Job requires submission via submit_job() to be executed by the server.
        """
    def launch_jupyter_server(
        self,
        job_name: str,
        conda_environment: str,
        notebook_directory: Path,
        cpus_to_use: int = 2,
        ram_gb: int = 32,
        time_limit: int = 240,
        port: int = 0,
        jupyter_args: str = "",
    ) -> JupyterJob:
        """Launches a Jupyter notebook server on the target remote Sun lab server.

        Use this method to run interactive Jupyter sessions on the remote server under SLURM control. Unlike the
        create_job(), this method automatically submits the job for execution as part of its runtime. Therefore, the
        returned JupyterJob instance should only be used to query information about how to connect to the remote
        Jupyter server.

        Args:
            job_name: The descriptive name of the Jupyter SLURM job to be created. Primarily, this name is used in
                terminal printouts to identify the job to human operators.
            conda_environment: The name of the conda environment to activate on the server before running the job logic.
                The environment should contain the necessary Python packages and CLIs to support running the job's
                logic. For Jupyter jobs, this necessarily includes the Jupyter notebook and jupyterlab packages.
            port: The connection port number for Jupyter server. If set to 0 (default), a random port number between
                8888 and 9999 will be assigned to this connection to reduce the possibility of colliding with other
                user sessions.
            notebook_directory: The directory to use as Jupyter's root. During runtime, Jupyter will only have GUI
                access to items stored in or under this directory. For most runtimes, this should be set to the user's
                root data or working directory.
            cpus_to_use: The number of CPUs to allocate to the Jupyter server. Keep this value as small as possible to
                avoid interfering with headless data processing jobs.
            ram_gb: The amount of RAM, in GB, to allocate to the Jupyter server. Keep this value as small as possible to
                avoid interfering with headless data processing jobs.
            time_limit: The maximum Jupyter server uptime, in minutes. Set this to the expected duration of your jupyter
                session.
            jupyter_args: Stores additional arguments to pass to jupyter notebook initialization command.

        Returns:
            The initialized JupyterJob instance that stores information on how to connect to the created Jupyter server.
            Do NOT re-submit the job to the server, as this is done as part of this method's runtime.

        Raises:
            TimeoutError: If the target Jupyter server doesn't start within 120 minutes from this method being called.
            RuntimeError: If job submission fails for any reason.
        """
    def submit_job(self, job: Job | JupyterJob) -> Job | JupyterJob:
        """Submits the input job to the managed BioHPC server via SLURM job manager.

        This method submits various jobs for execution via SLURM-managed BioHPC cluster. As part of its runtime, the
        method translates the Job object into the shell script, moves the script to the target working directory on
        the server, and instructs the server to execute the shell script (via SLURM).

        Args:
            job: The Job object that contains all job data.

        Returns:
            The job object whose 'job_id' attribute had been modified with the job ID if the job was successfully
            submitted.

        Raises:
            RuntimeError: If job submission to the server fails.
        """
    def job_complete(self, job: Job | JupyterJob) -> bool:
        """Returns True if the job managed by the input Job instance has been completed or terminated its runtime due
        to an error.

        If the job is still running or is waiting inside the execution queue, returns False.

        Args:
            job: The Job object whose status needs to be checked.

        Raises:
            ValueError: If the input Job object does not contain a valid job_id, suggesting that it has not been
                submitted to the server.
        """
    def abort_job(self, job: Job | JupyterJob) -> None:
        """Aborts the target job if it is currently running on the server.

        Use this method to immediately abort running or queued jobs, without waiting for the timeout guard. If the job
        is queued, this method will remove it from the SLURM queue. If the job is already terminated, this method will
        do nothing.

        Args:
            job: The Job object that needs to be aborted.
        """
    def pull_file(self, local_file_path: Path, remote_file_path: Path) -> None:
        """Moves the specified file from the remote server to the local machine.

        Args:
            local_file_path: The path to the local instance of the file (where to copy the file).
            remote_file_path: The path to the target file on the remote server (the file to be copied).
        """
    def push_file(self, local_file_path: Path, remote_file_path: Path) -> None:
        """Moves the specified file from the remote server to the local machine.

        Args:
            local_file_path: The path to the file that needs to be copied to the remote server.
            remote_file_path: The path to the file on the remote server (where to copy the file).
        """
    def pull_directory(self, local_directory_path: Path, remote_directory_path: Path) -> None:
        """Recursively downloads the entire target directory from the remote server to the local machine.

        Args:
            local_directory_path: The path to the local directory where the remote directory will be copied.
            remote_directory_path: The path to the directory on the remote server to be downloaded.
        """
    def push_directory(self, local_directory_path: Path, remote_directory_path: Path) -> None:
        """Recursively uploads the entire target directory from the local machine to the remote server.

        Args:
            local_directory_path: The path to the local directory to be uploaded.
            remote_directory_path: The path on the remote server where the directory will be copied.
        """
    def remove(self, remote_path: Path, is_dir: bool) -> None:
        """Removes the specified file or directory from the remote server.

        Args:
            remote_path: The path to the file or directory on the remote server to be removed.
            is_dir: Determines whether the input path represents a directory or a file.
        """
    def create_directory(self, remote_path: Path, parents: bool = True) -> None:
        """Creates the specified directory tree on the managed remote server via SFTP.

        This method creates directories on the remote server, with options to create parent directories and handle
        existing directories gracefully.

        Args:
            remote_path: The absolute path to the directory to create on the remote server, relative to the server
                root.
            parents: Determines whether to create parent directories, if they are missing. Otherwise, if parents do not
                exist, raises a FileNotFoundError.

        Notes:
            This method silently assumes that it is fine if the directory already exists and treats it as a successful
            runtime end-point.
        """
    def exists(self, remote_path: Path) -> bool:
        """Returns True if the target file or directory exists on the remote server."""
    def close(self) -> None:
        """Closes the SSH connection to the server.

        This method has to be called before destroying the class instance to ensure proper resource cleanup.
        """
    @property
    def raw_data_root(self) -> Path:
        """Returns the absolute path to the directory used to store the raw data for all Sun lab projects on the server
        accessible through this class.
        """
    @property
    def processed_data_root(self) -> Path:
        """Returns the absolute path to the directory used to store the processed data for all Sun lab projects on the
        server accessible through this class.
        """
    @property
    def user_data_root(self) -> Path:
        """Returns the absolute path to the directory used to store user-specific data on the server accessible through
        this class."""
    @property
    def user_working_root(self) -> Path:
        """Returns the absolute path to the user-specific working (fast) directory on the server accessible through
        this class."""
    @property
    def host(self) -> str:
        """Returns the hostname or IP address of the server accessible through this class."""
    @property
    def user(self) -> str:
        """Returns the username used to authenticate with the server."""
