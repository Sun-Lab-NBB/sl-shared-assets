"""This module provides the core Job class, used as the starting point for all SLURM-managed job executed on lab compute
server(s). Specifically, the Job class acts as a wrapper around the SLURM configuration and specific logic of each
job. During runtime, Server class interacts with input job objects to manage their transfer and execution on the
remote servers."""

# noinspection PyProtectedMember
from pathlib import Path
import datetime

from simple_slurm import Slurm  # type: ignore


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
    ) -> None:
        # Resolves the paths to the remote (server-side) .sh script file. This is the path where the job script
        # will be stored on the server, once it is transferred by the Server class instance.
        self.remote_script_path = str(working_directory.joinpath(f"{job_name}.sh"))

        # Defines additional arguments used by the Server class that executed the job.
        self.job_id: str | None = None  # This is set by the Server that submits the job.
        self.job_name: str = job_name  # Also stores the job name to support more informative terminal prints

        # Builds the slurm command object filled with configuration information
        self._command: Slurm = Slurm(
            cpus_per_task=cpus_to_use,
            job_name=job_name,
            output=str(output_log),
            error=str(error_log),
            mem=f"{ram_gb}G",
            time=datetime.timedelta(minutes=time_limit),
        )

        # Conda shell initialization commands
        self._command.add_cmd("eval $(conda shell.bash hook)")
        self._command.add_cmd("conda init bash")

        # Activates the target conda environment for the command.
        self._command.add_cmd(f"conda activate {conda_environment}")

    def __repr__(self) -> str:
        """Returns the string representation of the Job instance."""
        return f"Job(name={self.job_name}, id={self.job_id})"

    def add_command(self, command: str) -> None:
        """Adds the input command string to the end of the managed SLURM job command list.

        This method is a wrapper around simple_slurm's 'add_cmd' method. It is used to iteratively build the shell
        command sequence of the job.

        Args:
            command: The command string to add to the command list, e.g.: 'python main.py --input 1'.
        """

        self._command.add_cmd(command)

    @property
    def command_script(self) -> str:
        """Translates the managed job data into a shell-script-writable string and returns it to caller.

        This method is used by the Server class to translate the job into the format that can be submitted to and
        executed on the remote compute server. Do not call this method manually unless you know what you are doing.
        The returned string is safe to dump into a .sh (shell script) file and move to the BioHPC server for execution.
        """

        # Appends the command to clean up (remove) the temporary script file after processing runtime is over
        self._command.add_cmd(f"rm -f {self.remote_script_path}")

        # Translates the command to string format
        script_content = str(self._command)

        # Replaces escaped $ (/$) with $. This is essential, as without this correction, things like conda
        # initialization would not work as expected.
        fixed_script_content = script_content.replace("\\$", "$")

        # Returns the script content to caller as a string
        return fixed_script_content
