"""STUB!"""

from ..server import Server, ServerCredentials, Job
from pathlib import Path


class ProjectData:
    def __init__(self, credentials_path: Path, project_directory: Path):

        gather_data = Job(
            job_name=f"Gather project {project_directory.name} data.",
            output_log=project_directory.joinpath('gather_data.txt'),
            error_log=project_directory.joinpath('gather_data_errors.txt'),
            working_directory=project_directory,
            conda_environment='manage',
            cpus_to_use=2,
            ram_gb=10,
            time_limit=60,
        )

        gather_data.add_command()

        self._server = Server(credentials_path=credentials_path)

    def __del__(self):
        self._server.close()