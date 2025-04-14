import time
from pathlib import Path

import paramiko
from ataraxis_base_utilities import console, LogLevel
from paramiko.client import SSHClient
from simple_slurm import Slurm
import datetime
import re
from dataclasses import dataclass
from ataraxis_data_structures import YamlConfig


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
    transferred to the BioHPC server during preprocessing.
    """

    username: str = "YourNetID"
    """The username to use for server authentication."""
    password: str = "YourPassword"
    """The password to use for server authentication."""
    host: str = "cbsuwsun.biohpc.cornell.edu"
    """The hostname or IP address of the server to connect to."""


class Server:
    """Encapsulates access to the Sun lab BioHPC processing server.

    This class provides the API that allows accessing the BioHPC server and creating and submitting various
    SLURM-managed jobs to the cluster. It functions as the central interface used by all processing pipelines in the
    lab to execute costly data processing on the server.

    Notes:
        All lab processing pipelines expect the data to be stored on the server, using the default data format defined
        in the sl-experiment repository: https://github.com/Sun-Lab-NBB/sl-experiment. Additionally, this class expects
        all processing logic to be packaged and installed into dedicated conda environments on the server.

    Args:
        credentials_path: The path to the.yaml file containing the server hostname and access credentials.

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

    @staticmethod
    def generate_slurm_header(
        job_name: str, output_log: Path, error_log: Path, cpus_to_use=20, ram_gb=4, time_limit=60
    ) -> Slurm:
        """Creates a SLURM command object and fills it with initial job configuration data.

        This method is used to generate the initial SLURM command object and fill it with job (slurm) configuration and
        conda initialization data. It is used by all processing pipelines available in this library as the initial
        configuration point when writing job shell scripts.

        Notes:
            This does not contain the command to initialize the specific conda environment to be used during processing.
            This has to be provided as part of the additional; command configuration, typically via
            "source activate {ENV_NAME}".

        Args:
            job_name: The name of the slurm job to be created.
            output_log: The path to the .txt file on the processing server, where to store the standard output of the
                job.
            error_log: The path to the .txt file on the processing server, where to store the standard error of the
                job.
            cpus_to_use: The number of CPUs to use for the job.
            ram_gb: The amount of RAM to allocate for the job in Gigabytes.
            time_limit: The maximum time limit for the job, in minutes. It is highly advised to set an adequate maximum
                runtime limit to prevent jobs from hogging the server for a long period of time.
        """

        # Builds the slurm command object filled with configuration information
        slurm_command = Slurm(
            cpus_per_task=cpus_to_use,
            job_name=job_name,
            output=str(output_log),
            error=str(error_log),
            mem=f"{ram_gb}G",
            time=datetime.timedelta(minutes=time_limit),
        )

        # Adds commands to initialize conda as part of the job runtime
        slurm_command.add_cmd("eval $(conda shell.bash hook)")
        slurm_command.add_cmd("conda init bash")

        return slurm_command

    def submit_job(self, slurm_command: Slurm, working_directory: Path) -> str | None:
        """Submits the input SLURM command to the managed BioHPC server via the shell script.

        This method submits various commands for execution via SLURM-managed BioHPC cluster. As part of its runtime, the
        method translates the Slurm object into the shell script, moves the script to the target working directory on
        the server, and instructs the server to execute the shell script (via SLURM).

        Args:
            slurm_command: The Slurm (command) object containing the job configuration and individual commands to run
                as part of the processing pipeline.
            working_directory: The path to the working directory on the server where the shell script is moved
                and executed.

        Returns:
            The job ID assigned to the job by SLURM manager if the command submission is successful. None, if command
            submission fails.
        """

        # Extracts the job name from the slurm command text and uses it to generate the name for the remote script
        job_name_pattern = r"#SBATCH\s+--job-name\s+(\S+)"
        match = re.search(job_name_pattern, str(slurm_command))
        job_name = match.group(1)

        # Resolves the paths to the local and remote (server-side) .sh script files.
        local_script_path = Path("temp_script.sh")
        remote_script_path = str(working_directory.joinpath(f"{job_name}.sh"))

        # Appends the command to clean up (remove) the temporary script file after processing runtime is over
        slurm_command.add_cmd(f"rm -f {remote_script_path}")

        # Translates the command to string format
        script_content = str(slurm_command)

        # Replaces escaped $ (/$) with $. This is essential, as without this correction things like conda
        # initialization would not work as expected.
        fixed_script_content = script_content.replace("\\$", "$")

        # Creates a temporary script file locally and dumps translated command data into the file
        with open(local_script_path, "w") as f:
            f.write(fixed_script_content)

        # Uploads the command script to the server
        sftp = self._client.open_sftp()
        sftp.put(localpath=local_script_path, remotepath=remote_script_path)
        sftp.close()

        # Removes the temporary local .sh file
        local_script_path.unlink()

        # Makes the server-side script executable
        self._client.exec_command(f"chmod +x {remote_script_path}")

        # Submits the job to SLURM with sbatch and verifies submission state by returning either the ID of the job or
        # None to indicate no job has been submitted.
        job_output = self._client.exec_command(f"sbatch {remote_script_path}")[1].read().strip().decode()
        job_id = job_output.split()[-1] if "Submitted batch job" in job_output else None
        return job_id

    def job_complete(self, job_id: str) -> bool:
        """Returns True if the job with the given ID has been completed or terminated its runtime due to an error.

        If the job is still running or is waiting inside the execution queue, returns False.

        Args:
            job_id: The numeric ID of the job to check, assigned by SLURM.
        """
        if j_id not in self._client.exec_command(f"squeue -j {job_id}")[1].read().decode().strip():
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


if __name__ == "__main__":
    # Creates SSHClient for server access
    console.enable()
    cred_path = Path("/home/cyberaxolotl/Desktop/test/server_credentials.yaml")
    server = Server(credentials_path=cred_path)

    # Generates SLURM job header
    slurm = server.generate_slurm_header(
        job_name="test_job",
        output_log=Path("/workdir/ik278/test_job_stdout.txt"),
        error_log=Path("/workdir/ik278/test_job_stderr.txt"),
        cpus_to_use=1,
    )

    # Adds test runtime command
    slurm.add_cmd("python --version > /workdir/ik278/mamba_version.txt")

    # Submits the job to the server
    j_id = server.submit_job(slurm_command=slurm, working_directory=Path("/workdir/ik278/"))

    if j_id:
        console.echo(f"Successfully submitted job with ID {j_id} to the server.", level=LogLevel.SUCCESS)

        max_wait_time = 60  # Maximum wait time in seconds
        wait_interval = 1  # Check every 1 second
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            if server.job_complete(job_id=j_id):
                console.echo("Job completed", level=LogLevel.SUCCESS)
                break

            console.echo(f"Job still running. Waiting {wait_interval} seconds...", level=LogLevel.INFO)
            time.sleep(wait_interval)
            elapsed_time += wait_interval

    # Close the connection
    server.close()
