"""This package provides assets for safely transferring data between destinations available on the local filesystem
and efficiently removing it from the local filesystem.
"""

from .checksum_tools import calculate_directory_checksum
from .transfer_tools import delete_directory, transfer_directory

__all__ = [
    "calculate_directory_checksum",
    "delete_directory",
    "transfer_directory",
]
