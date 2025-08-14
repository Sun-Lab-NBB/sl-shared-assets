"""This package provides the classes and methods used by all Sun lab libraries to work with the data stored on remote
compute servers, such as the BioHPC server. It provides tools for submitting and monitoring jobs, running complex
processing pipelines and interactively working with the data via a Jupyter lab server."""

from .job import Job, JupyterJob
from .server import Server, ServerCredentials, generate_server_credentials
from .pipeline import (
    ProcessingStatus,
    TrackerFileNames,
    ProcessingTracker,
    ProcessingPipeline,
    ProcessingPipelines,
    generate_manager_id,
)
from .filesystem import (
    RemotePaths,
    get_working_directory,
    set_working_directory,
    get_credentials_file_path,
    get_remote_filesystem_paths,
)

__all__ = [
    "Job",
    "JupyterJob",
    "ProcessingPipeline",
    "ProcessingPipelines",
    "ProcessingStatus",
    "ProcessingTracker",
    "RemotePaths",
    "Server",
    "ServerCredentials",
    "TrackerFileNames",
    "generate_manager_id",
    "generate_server_credentials",
    "get_credentials_file_path",
    "get_remote_filesystem_paths",
    "get_working_directory",
    "set_working_directory",
]
