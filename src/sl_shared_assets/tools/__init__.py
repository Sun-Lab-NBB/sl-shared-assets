"""This package provides helper tools used to automate routine operations, such as transferring or verifying the
integrity of the data. The tools from this package are used by most other data processing libraries in the lab. Since
version 5.0.0, this package also provides low-level data processing pipelines and service routines used to work with
remote compute servers."""

from .transfer_tools import delete_directory, transfer_directory
from .packaging_tools import calculate_directory_checksum
from .processing_pipelines import (
    fetch_remote_project_manifest,
    generate_remote_project_manifest,
    compose_remote_processing_pipeline,
)
from .project_management_tools import (
    ProjectManifest,
    archive_session,
    prepare_session,
    resolve_checksum,
    generate_project_manifest,
)

__all__ = [
    "ProjectManifest",
    "archive_session",
    "calculate_directory_checksum",
    "compose_remote_processing_pipeline",
    "delete_directory",
    "fetch_remote_project_manifest",
    "generate_project_manifest",
    "generate_remote_project_manifest",
    "prepare_session",
    "resolve_checksum",
    "transfer_directory",
]
