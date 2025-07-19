"""This module provides the tools for working with the Sun lab BioHPC cluster. Specifically, the classes from this
module establish an API for submitting jobs to the shared data processing cluster (managed via SLURM) and monitoring
the running job status. All lab processing and analysis pipelines use this interface for accessing shared compute
resources.
"""

import stat
from random import randint
from pathlib import Path
import tempfile
from dataclasses import field, dataclass

import paramiko

# noinspection PyProtectedMember
from simple_slurm import Slurm  # type: ignore
from ataraxis_time import PrecisionTimer
from paramiko.client import SSHClient
from ataraxis_base_utilities import LogLevel, console
from ataraxis_data_structures import YamlConfig
from ataraxis_time.time_helpers import get_timestamp

from .job import Job, JupyterJob


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
    # noinspection PyArgumentList
    ServerCredentials(
        username=username,
        password=password,
        host=host,
        storage_root=storage_root,
        working_root=working_root,
        shared_directory_name=shared_directory_name,
    ).to_yaml(file_path=output_directory.joinpath("server_credentials.yaml"))


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
    storage_root: str = "/local/storage"
    """The path to the root storage (slow) server directory. Typically, this is the path to the top-level (root) 
    directory of the HDD RAID volume."""
    working_root: str = "/local/workdir"
    """The path to the root working (fast) server directory. Typically, this is the path to the top-level (root) 
    directory of the NVME RAID volume. If the server uses the same volume for both storage and working directories, 
    enter the same path under both 'storage_root' and 'working_root'."""
    shared_directory_name: str = "sun_data"
    """Stores the name of the shared directory used to store all Sun lab project data on the storage and working 
    server volumes."""
    raw_data_root: str = field(init=False, default_factory=lambda: "/local/storage/sun_data")
    """The path to the root directory used to store the raw data from all Sun lab projects on the target server."""
    processed_data_root: str = field(init=False, default_factory=lambda: "/local/workdir/sun_data")
    """The path to the root directory used to store the processed data from all Sun lab projects on the target 
    server."""
    user_data_root: str = field(init=False, default_factory=lambda: "/local/storage/YourNetID")
    """The path to the root directory of the user on the target server. Unlike raw and processed data roots, which are 
    shared between all Sun lab users, each user_data directory is unique for every server user."""
    user_working_root: str = field(init=False, default_factory=lambda: "/local/workdir/YourNetID")
    """The path to the root user working directory on the target server. This directory is unique for every user."""

    def __post_init__(self) -> None:
        """Statically resolves the paths to end-point directories using provided root directories."""

        # Shared Sun Lab directories statically use 'sun_data' root names
        self.raw_data_root = str(Path(self.storage_root).joinpath(self.shared_directory_name))
        self.processed_data_root = str(Path(self.working_root).joinpath(self.shared_directory_name))

        # User directories exist at the same level as the 'shared' root project directories, but user user-ids as names.
        self.user_data_root = str(Path(self.storage_root).joinpath(f"{self.username}"))
        self.user_working_root = str(Path(self.working_root).joinpath(f"{self.username}"))


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
        # Tracker used to prevent __del__ from calling stop() for a partially initialized class.
        self._open: bool = False

        # Loads the credentials from the provided .yaml file
        self._credentials: ServerCredentials = ServerCredentials.from_yaml(credentials_path)  # type: ignore

        # Initializes a timer class to optionally delay loop cycling below
        timer = PrecisionTimer("s")

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
                self._open = True
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
                    f"Could not SSH into {self._credentials.host}, retrying after a 2-second delay...",
                    level=LogLevel.WARNING,
                )
                attempt += 1
                timer.delay_noblock(delay=2, allow_sleep=True)

    def __del__(self) -> None:
        """If the instance is connected to the server, terminates the connection before the instance is destroyed."""
        self.close()

    def create_job(
        self,
        job_name: str,
        conda_environment: str,
        cpus_to_use: int = 10,
        ram_gb: int = 10,
        time_limit: int = 60,
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
        # Statically configures the working directory to be stored under:
        # user working root / job_logs / job_name_timestamp
        timestamp = get_timestamp()
        working_directory = Path(self.user_working_root.joinpath("job_logs", f"{job_name}_{timestamp}"))
        self.create_directory(remote_path=working_directory, parents=True)

        return Job(
            job_name=job_name,
            output_log=working_directory.joinpath("stdout.txt"),
            error_log=working_directory.joinpath("stderr.txt"),
            working_directory=working_directory,
            conda_environment=conda_environment,
            cpus_to_use=cpus_to_use,
            ram_gb=ram_gb,
            time_limit=time_limit,
        )

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

        # Statically configures the working directory to be stored under:
        # user working root / job_logs / job_name_timestamp
        timestamp = get_timestamp()
        working_directory = Path(self.user_working_root.joinpath("job_logs", f"{job_name}_{timestamp}"))
        self.create_directory(remote_path=working_directory, parents=True)

        # If necessary, generates and sets port to a random value between 8888 and 9999.
        if port == 0:
            port = randint(8888, 9999)

        job = JupyterJob(
            job_name=job_name,
            output_log=working_directory.joinpath("stdout.txt"),
            error_log=working_directory.joinpath("stderr.txt"),
            working_directory=working_directory,
            conda_environment=conda_environment,
            notebook_directory=notebook_directory,
            port=port,
            cpus_to_use=cpus_to_use,
            ram_gb=ram_gb,
            time_limit=time_limit,
            jupyter_args=jupyter_args,
        )

        # Submits the job to the server and, if submission is successful, returns the JupyterJob object extended to
        # include connection data received from the server.
        return self.submit_job(job)  # type: ignore[return-value]

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
        console.echo(message=f"Submitting '{job.job_name}' job to the remote server {self.host}...")

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
            message = f"Failed to submit the '{job.job_name}' job to the BioHPC cluster."
            console.error(message, RuntimeError)

            # Fallback to appease mypy, should not be reachable
            raise RuntimeError(message)

        # Otherwise, extracts the job id assigned to the job by SLURM from the response and writes it to the processed
        # Job object
        job_id = job_output.split()[-1]
        job.job_id = job_id

        # Special processing for Jupyter jobs
        if isinstance(job, JupyterJob):
            # Transfers host and user information to the JupyterJob object
            job.host = self.host
            job.user = self.user

            # Initializes a timer class to optionally delay loop cycling below
            timer = PrecisionTimer("s")

            timer.reset()
            while timer.elapsed < 120:  # Waits for at most 2 minutes before terminating with an error
                # Checks if the connection info file exists
                try:
                    # Pulls the connection info file
                    local_info_file = Path(f"/tmp/{job.job_name}_connection.txt")
                    self.pull_file(local_file_path=local_info_file, remote_file_path=job.connection_info_file)

                    # Parses connection data from the file and caches it inside Job class attributes
                    job.parse_connection_info(local_info_file)

                    # Removes the local file copy after it is parsed
                    local_info_file.unlink(missing_ok=True)

                    # Also removes the remote copy once the runtime is over
                    self.remove(remote_path=job.connection_info_file, is_dir=False)

                    # Breaks the waiting loop
                    break

                except Exception:
                    # The file doesn't exist yet or job initialization failed
                    if self.job_complete(job):
                        message = (
                            f"Remote jupyter server job {job.job_name} with id {job.job_id} encountered a startup and "
                            f"was terminated prematurely."
                        )
                        console.error(message, RuntimeError)

                timer.delay_noblock(delay=5, allow_sleep=True)  # Waits for 5 seconds before checking again
            else:
                # Only raises timeout error if the while loop is not broken in 120 seconds
                message = (
                    f"Remote jupyter server job {job.job_name} with id {job.job_id} did not start within 120 seconds "
                    f"from being submitted. Since all jupyter jobs are intended to be interactive and the server is "
                    f"busy running other jobs, this job is cancelled. Try again when the server is less busy."
                )
                console.error(message, TimeoutError)
                raise TimeoutError(message)  # Fallback to appease mypy

        console.echo(message=f"{job.job_name} job: Submitted to {self.host}.", level=LogLevel.SUCCESS)

        # Returns the updated job object
        return job

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

    def abort_job(self, job: Job | JupyterJob) -> None:
        """Aborts the target job if it is currently running on the server.

        Use this method to immediately abort running or queued jobs, without waiting for the timeout guard. If the job
        is queued, this method will remove it from the SLURM queue. If the job is already terminated, this method will
        do nothing.

        Args:
            job: The Job object that needs to be aborted.
        """

        # Sends the 'scancel' command to the server targeting the specific Job via ID, unless the job is already
        # complete
        if not self.job_complete(job):
            self._client.exec_command(f"scancel {job.job_id}")

        console.echo(message=f"{job.job_name} job: Aborted.", level=LogLevel.SUCCESS)

    def pull_file(self, local_file_path: Path, remote_file_path: Path) -> None:
        """Moves the specified file from the remote server to the local machine.

        Args:
            local_file_path: The path to the local instance of the file (where to copy the file).
            remote_file_path: The path to the target file on the remote server (the file to be copied).
        """
        sftp = self._client.open_sftp()
        try:
            sftp.get(localpath=local_file_path, remotepath=str(remote_file_path))
        finally:
            sftp.close()

    def push_file(self, local_file_path: Path, remote_file_path: Path) -> None:
        """Moves the specified file from the remote server to the local machine.

        Args:
            local_file_path: The path to the file that needs to be copied to the remote server.
            remote_file_path: The path to the file on the remote server (where to copy the file).
        """
        sftp = self._client.open_sftp()
        try:
            sftp.put(localpath=local_file_path, remotepath=str(remote_file_path))
        finally:
            sftp.close()

    def pull_directory(self, local_directory_path: Path, remote_directory_path: Path) -> None:
        """Recursively downloads the entire target directory from the remote server to the local machine.

        Args:
            local_directory_path: The path to the local directory where the remote directory will be copied.
            remote_directory_path: The path to the directory on the remote server to be downloaded.
        """
        sftp = self._client.open_sftp()

        try:
            # Creates the local directory if it doesn't exist
            local_directory_path.mkdir(parents=True, exist_ok=True)

            # Gets the list of items in the remote directory
            remote_items = sftp.listdir_attr(str(remote_directory_path))

            for item in remote_items:
                remote_item_path = remote_directory_path.joinpath(item.filename)
                local_item_path = local_directory_path.joinpath(item.filename)

                # Checks if item is a directory
                if stat.S_ISDIR(item.st_mode):  # type: ignore
                    # Recursively pulls the subdirectory
                    self.pull_directory(local_item_path, remote_item_path)
                else:
                    # Pulls the individual file using existing method
                    sftp.get(localpath=str(local_item_path), remotepath=str(remote_item_path))

        finally:
            sftp.close()

    def push_directory(self, local_directory_path: Path, remote_directory_path: Path) -> None:
        """Recursively uploads the entire target directory from the local machine to the remote server.

        Args:
            local_directory_path: The path to the local directory to be uploaded.
            remote_directory_path: The path on the remote server where the directory will be copied.
        """
        if not local_directory_path.exists() or not local_directory_path.is_dir():
            message = (
                f"Unable to upload the target local directory {local_directory_path} to the server, as it does not "
                f"exist."
            )
            console.error(message=message, error=FileNotFoundError)

        sftp = self._client.open_sftp()

        try:
            # Creates the remote directory using existing method
            self.create_directory(remote_directory_path, parents=True)

            # Iterates through all items in the local directory
            for local_item_path in local_directory_path.iterdir():
                remote_item_path = remote_directory_path.joinpath(local_item_path.name)

                if local_item_path.is_dir():
                    # Recursively pushes subdirectory
                    self.push_directory(local_item_path, remote_item_path)
                else:
                    # Pushes the individual file using existing method
                    sftp.put(localpath=str(local_item_path), remotepath=str(remote_item_path))

        finally:
            sftp.close()

    def remove(self, remote_path: Path, is_dir: bool) -> None:
        """Removes the specified file or directory from the remote server.

        Args:
            remote_path: The path to the file or directory on the remote server to be removed.
            is_dir: Determines whether the input path represents a directory or a file.
        """
        sftp = self._client.open_sftp()
        try:
            if is_dir:
                sftp.rmdir(path=str(remote_path))
            else:
                sftp.unlink(path=str(remote_path))
        finally:
            sftp.close()

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
        sftp = self._client.open_sftp()

        try:
            # Converts the target path to string for SFTP operations
            remote_path_str = str(remote_path)

            if parents:
                # Creates parent directories if needed:
                # Split the path into parts and create each level
                path_parts = Path(remote_path_str).parts
                current_path = ""

                for part in path_parts:
                    # Skips empty path parts
                    if not part:
                        continue

                    if current_path:
                        # Keeps stacking path components on top of the current_path object
                        current_path = str(Path(current_path).joinpath(part))
                    else:
                        # Initially, the current path is empty, so it is set to the first part
                        current_path = part

                    try:
                        # Checks if directory exists by trying to stat it
                        sftp.stat(current_path)
                    except FileNotFoundError:
                        # If the directory does not exist, creates it
                        sftp.mkdir(current_path)
            else:
                # Otherwise, only creates the final directory
                try:
                    # Checks if directory already exists
                    sftp.stat(remote_path_str)
                except FileNotFoundError:
                    # Creates the directory if it does not exist
                    sftp.mkdir(remote_path_str)

        # Ensures sftp connection is closed.
        finally:
            sftp.close()

    def exists(self, remote_path: Path) -> bool:
        """Returns True if the target file or directory exists on the remote server."""

        sftp = self._client.open_sftp()
        try:
            # Checks if the target file or directory exists by trying to stat it
            sftp.stat(str(remote_path))

            # If the request does not err, returns True (file or directory exists)
            return True

        # If the directory or file does not exist, returns False
        except FileNotFoundError:
            return False

    def close(self) -> None:
        """Closes the SSH connection to the server.

        This method has to be called before destroying the class instance to ensure proper resource cleanup.
        """
        # Prevents closing already closed connections
        if self._open:
            self._client.close()

    @property
    def raw_data_root(self) -> Path:
        """Returns the absolute path to the directory used to store the raw data for all Sun lab projects on the server
        accessible through this class.
        """
        return Path(self._credentials.raw_data_root)

    @property
    def processed_data_root(self) -> Path:
        """Returns the absolute path to the directory used to store the processed data for all Sun lab projects on the
        server accessible through this class.
        """
        return Path(self._credentials.processed_data_root)

    @property
    def user_data_root(self) -> Path:
        """Returns the absolute path to the directory used to store user-specific data on the server accessible through
        this class."""
        return Path(self._credentials.user_data_root)

    @property
    def user_working_root(self) -> Path:
        """Returns the absolute path to the user-specific working (fast) directory on the server accessible through
        this class."""
        return Path(self._credentials.user_working_root)

    @property
    def host(self) -> str:
        """Returns the hostname or IP address of the server accessible through this class."""
        return self._credentials.host

    @property
    def user(self) -> str:
        """Returns the username used to authenticate with the server."""
        return self._credentials.username
