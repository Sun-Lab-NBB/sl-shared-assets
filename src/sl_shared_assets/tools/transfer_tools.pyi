from pathlib import Path

from .packaging_tools import calculate_directory_checksum as calculate_directory_checksum

def delete_directory(directory_path: Path) -> None:
    """Removes the input directory and all its subdirectories using parallel processing.

    This function outperforms default approaches like subprocess call with rm -rf and shutil rmtree for directories with
    a comparably small number of large files. For example, this is the case for the mesoscope frame directories, which
    are deleted ~6 times faster with this method over sh.rmtree. Potentially, it may also outperform these approaches
    for all comparatively shallow directories.

    Notes:
        This function is often combined with the transfer_directory function to remove the source directory after
        it has been transferred.

    Args:
        directory_path: The path to the directory to delete.
    """

def _transfer_file(source_file: Path, source_directory: Path, destination_directory: Path) -> None:
    """Copies the input file from the source directory to the destination directory while preserving the file metadata.

    This worker method is used by the transfer_directory() method to move multiple files in parallel.

    Notes:
        If the file is found under a hierarchy of subdirectories inside the input source_directory, that hierarchy will
        be preserved in the destination directory.

    Args:
        source_file: The file to be copied.
        source_directory: The root directory where the file is located.
        destination_directory: The destination directory where to move the file.
    """

def transfer_directory(
    source: Path, destination: Path, num_threads: int = 1, verify_integrity: bool = False, remove_source: bool = False
) -> None:
    """Copies the contents of the input directory tree from source to destination while preserving the folder
    structure.

    Notes:
        This method recreates the moved directory hierarchy on the destination if the hierarchy does not exist. This is
        done before copying the files.

        The method executes a multithreading copy operation and does not by default remove the source data after the
        copy is complete.

        If the method is configured to verify transferred data integrity, it generates xxHash-128 checksum of the data
        before and after the transfer and compares the two checksums to detect data corruption.

    Args:
        source: The path to the directory that needs to be moved.
        destination: The path to the destination directory where to move the contents of the source directory.
        num_threads: The number of threads to use for parallel file transfer. This number should be set depending on the
            type of transfer (local or remote) and is not guaranteed to provide improved transfer performance. For local
            transfers, setting this number above 1 will likely provide a performance boost. For remote transfers using
            a single TCP / IP socket (such as non-multichannel SMB protocol), the number should be set to 1. Setting
            this value to a number below 1 instructs the function to use all available CPU cores.
        verify_integrity: Determines whether to perform integrity verification for the transferred files.
        remove_source: Determines whether to remove the source directory and all of its contents after the transfer is
            complete and optionally verified.

    Raises:
        RuntimeError: If the transferred files do not pass the xxHas3-128 checksum integrity verification.
    """
