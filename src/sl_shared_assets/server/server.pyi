from pathlib import Path
from dataclasses import dataclass

from simple_slurm import Slurm as Slurm
from paramiko.client import SSHClient as SSHClient
from ataraxis_data_structures import YamlConfig

from .job import Job as Job

def generate_server_credentials(
    output_directory: Path,
    username: str,
    password: str,
    host: str = "cbsuwsun.biohpc.cornell.edu",
    raw_data_root: str = "/workdir/sun_data",
    processed_data_root: str = "/storage/sun_data",
) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This function provides a convenience interface for generating new BioHPC server credential files. Generally, this is
    only used when setting up new host-computers in the lab.

    Args:
        output_directory: The directory where to save the generated server_credentials.yaml file.
        username: The username to use for server authentication.
        password: The password to use for server authentication.
        host: The hostname or IP address of the server to connect to.
        raw_data_root: The path to the root directory used to store the raw data from all Sun lab projects on the
            server.
        processed_data_root: The path to the root directory used to store the processed data from all Sun lab projects
            on the server.
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
    raw_data_root: str = ...
    processed_data_root: str = ...

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
    def submit_job(self, job: Job) -> Job:
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
    def job_complete(self, job: Job) -> bool:
        """Returns True if the job managed by the input Job instance has been completed or terminated its runtime due
        to an error.

        If the job is still running or is waiting inside the execution queue, returns False.

        Args:
            job: The Job object whose status needs to be checked.

        Raises:
            ValueError: If the input Job object does not contain a valid job_id, suggesting that it has not been
                submitted to the server.
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
    def remove(self, remote_path: Path, is_dir: bool) -> None:
        """Removes the specified file or directory from the remote server.

        Args:
            remote_path: The path to the file or directory on the remote server to be removed.
            is_dir: Determines whether the input path represents a directory or a file.
        """
    def close(self) -> None:
        """Closes the SSH connection to the server.

        This method has to be called before destroying the class instance to ensure proper resource cleanup.
        """
    @property
    def raw_data_root(self) -> str:
        """Returns the absolute path to the directory used to store the raw data for all Sun lab projects on the server
        accessible through this class.
        """
    @property
    def processed_data_root(self) -> str:
        """Returns the absolute path to the directory used to store the processed data for all Sun lab projects on the
        server accessible through this class.
        """
