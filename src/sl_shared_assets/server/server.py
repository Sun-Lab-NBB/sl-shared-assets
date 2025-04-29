"""This module provides the tools for working with the Sun lab BioHPC cluster. Specifically, the classes from this
module establish an API for submitting jobs to the shared data processing cluster (managed via SLURM) and monitoring
the running job status. All lab processing and analysis pipelines use this interface for accessing shared compute
resources.
"""

import time
from pathlib import Path
import tempfile
from dataclasses import dataclass

import paramiko

# noinspection PyProtectedMember
from simple_slurm import Slurm  # type: ignore
from paramiko.client import SSHClient
from ataraxis_base_utilities import LogLevel, console
from ataraxis_data_structures import YamlConfig

from .job import Job


def generate_server_credentials(
    output_directory: Path, username: str, password: str, host: str = "cbsuwsun.biohpc.cornell.edu"
) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This function provides a convenience interface for generating new BioHPC server credential files. Generally, this is
    only used when setting up new host-computers in the lab.
    """
    ServerCredentials(username=username, password=password, host=host).to_yaml(
        file_path=output_directory.joinpath("server_credentials.yaml")
    )


@dataclass()
class ServerCredentials(YamlConfig):
    """This class stores the hostname and credentials used to log into the BioHPC cluster to run Sun lab processing
    pipelines.

    Primarily, this is used as part of the sl-experiment library runtime to start data processing once it is
    transferred to the BioHPC server during preprocessing. However, the same file can be used together with the Server
    class API to run any computation jobs on the lab's BioHPC server.
    """

    username: str = "YourNetID"
    """The username to use for server authentication."""
    password: str = "YourPassword"
    """The password to use for server authentication."""
    host: str = "cbsuwsun.biohpc.cornell.edu"
    """The hostname or IP address of the server to connect to."""


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

    def __init__(self, credentials_path: Path) -> None:
        # Tracker used to prevent __del__ from classing stop() for a partially initialized class.
        self._open: bool = False

        # Loads the credentials from the provided .yaml file
        self._credentials: ServerCredentials = ServerCredentials.from_yaml(credentials_path)  # type: ignore

        # Establishes the SSH connection to the specified processing server. At most, attempts to connect to the server
        # 30 times before terminating with an error
        attempt = 0
        while True:
            console.echo(
                f"Trying to connect to {self._credentials.host} (attempt {attempt}/30)...", level=LogLevel.INFO
            )
            try:
                self._client: SSHClient = paramiko.SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._client.connect(
                    self._credentials.host, username=self._credentials.username, password=self._credentials.password
                )
                console.echo(f"Connected to {self._credentials.host}", level=LogLevel.SUCCESS)
                break
            except paramiko.AuthenticationException:
                message = (
                    f"Authentication failed when connecting to {self._credentials.host} using "
                    f"{self._credentials.username} user."
                )
                console.error(message, RuntimeError)
                raise RuntimeError
            except:
                if attempt == 30:
                    message = f"Could not connect to {self._credentials.host} after 30 attempts. Aborting runtime."
                    console.error(message, RuntimeError)
                    raise RuntimeError

                console.echo(
                    f"Could not SSH to {self._credentials.host}, retrying after a 2-second delay...",
                    level=LogLevel.WARNING,
                )
                attempt += 1
                time.sleep(2)

    def __del__(self) -> None:
        """If the instance is connected to the server, terminates the connection before the instance is destroyed."""
        self.close()

    def submit_job(self, job: Job) -> Job:
        """Submits the input job to the managed BioHPC server via SLURM job manager.

        This method submits various jobs for execution via SLURM-managed BioHPC cluster. As part of its runtime, the
        method translates the Job object into the shell script, moves the script to the target working directory on
        the server, and instructs the server to execute the shell script (via SLURM).

        Args:
            job: The Job object that contains all job data.

        Returns:
            The job object whose 'job_id' attribute had been modified with the job ID, if the job was successfully
            submitted.

        Raises:
            RuntimeError: If job submission to the server fails.
        """

        # Generates a temporary shell script on the local machine. Uses tempfile to automatically remove the
        # local script as soon as it is uploaded to the server.
        with tempfile.TemporaryDirectory() as temp_dir:
            local_script_path = Path(temp_dir).joinpath(f"{job.job_name}.sh")
            fixed_script_content = job.command_script

            # Creates a temporary script file locally and dumps translated command data into the file
            with open(local_script_path, "w") as f:
                f.write(fixed_script_content)

            # Uploads the command script to the server
            sftp = self._client.open_sftp()
            sftp.put(localpath=local_script_path, remotepath=job.remote_script_path)
            sftp.close()

        # Makes the server-side script executable
        self._client.exec_command(f"chmod +x {job.remote_script_path}")

        # Submits the job to SLURM with sbatch and verifies submission state
        job_output = self._client.exec_command(f"sbatch {job.remote_script_path}")[1].read().strip().decode()

        # If batch_job is not in the output received from SLURM in response to issuing the submission command, raises an
        # error.
        if "Submitted batch job" not in job_output:
            message = f"Failed to submit the {job.job_name} job to the BioHPC cluster."
            console.error(message, RuntimeError)

            # Fallback to appease mypy, should not be reachable
            raise RuntimeError(message)

        # Otherwise, extracts the job id assigned to the job by SLURM from the response and writes it to the processed
        # Job object
        job_id = job_output.split()[-1]
        job.job_id = job_id
        return job

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

        if job.job_id is None:
            message = (
                f"The input Job object for the job {job.job_name} does not contain a valid job_id. This indicates that "
                f"the job has not been submitted to the server."
            )
            console.error(message, ValueError)

            # This is here to appease mypy, it should not be reachable
            raise ValueError(message)

        if job.job_id not in self._client.exec_command(f"squeue -j {job.job_id}")[1].read().decode().strip():
            return True
        else:
            return False

    def close(self) -> None:
        """Closes the SSH connection to the server.

        This method has to be called before destroying the class instance to ensure proper resource cleanup.
        """
        # Prevents closing already closed connections
        if self._open:
            self._client.close()
