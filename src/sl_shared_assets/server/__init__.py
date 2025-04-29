"""This package provides the classes and methods used by all Sun lab libraries to submit remote jobs to the BioHPC
and other compute servers. This package is also used across all Sun lab members private code to interface with the
shared server."""

from .job import Job
from .server import Server, ServerCredentials, generate_server_credentials

__all__ = ["Server", "ServerCredentials", "generate_server_credentials", "Job"]
