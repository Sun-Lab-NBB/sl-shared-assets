"""This module provides tools for moving the data between destinations within or across machines (PCs). All methods in
this module expect that the destinations and sources are mounted on the host-machine file-system via the SMB or an
equivalent protocol.
"""

import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm
from ataraxis_base_utilities import console, ensure_directory_exists

from .packaging_tools import calculate_directory_checksum


def _transfer_file(source_file: Path, source_directory: Path, destination_directory: Path) -> None:
    """Copies the input file from the source directory to the destination directory while preserving the file metadata.

    This is a worker method used by the transfer_directory() method to move multiple files in parallel.

    Notes:
        If the file is found under a hierarchy of subdirectories inside the input source_directory, that hierarchy will
        be preserved in the destination directory.

    Args:
        source_file: The file to be copied.
        source_directory: The root directory where the file is located.
        destination_directory: The destination directory where to move the file.
    """
    relative = source_file.relative_to(source_directory)
    dest_file = destination_directory / relative
    shutil.copy2(source_file, dest_file)


def transfer_directory(source: Path, destination: Path, num_threads: int = 1, verify_integrity: bool = False) -> None:
    """Copies the contents of the input directory tree from source to destination while preserving the folder
    structure.

    Notes:
        This method recreates the moved directory hierarchy on the destination if the hierarchy does not exist. This is
        done before copying the files.

        The method executes a multithreading copy operation and does not remove the source data after the copy is
        complete. This behavior is intended and relies on other modules cleaning up the no-longer source data.

        If the method is configured to verify transferred data integrity, it reruns the xxHash3-128 checksum calculation
        and compares the returned checksum to the one stored in the source directory. The method assumes that all input
        directories contain the 'ax_checksum.txt' file that stores the 'source' directory checksum at the highest level
        of the input directory tree.

    Args:
        source: The path to the directory that needs to be moved.
        destination: The path to the destination directory where to move the contents of the source directory.
        num_threads: The number of threads to use for parallel file transfer. This number should be set depending on the
            type of transfer (local or remote) and is not guaranteed to provide improved transfer performance. For local
            transfers, setting this number above 1 will likely provide a performance boost. For remote transfers using
            a single TCP / IP socket (such as non-multichannel SMB protocol), the number should be set to 1.
        verify_integrity: Determines whether to perform integrity verification for the transferred files. Note,
            transfer integrity is generally not a concern for most runtimes and may require considerable processing
            time. Therefore, it is often preferable to disable this option to optimize method runtime speed.

    Raises:
        RuntimeError: If the transferred files do not pass the xxHas3-128 checksum integrity verification.
    """
    if not source.exists():
        message = f"Unable to transfer the source directory {source}, as it does not exist."
        console.error(message=message, error=FileNotFoundError)

    # If transfer integrity verification is enabled, but the source directory does not contain the 'ax_checksum.txt'
    # file, checksums the directory before the transfer operation.
    if verify_integrity and not source.joinpath("ax_checksum.txt").exists():
        calculate_directory_checksum(directory=source, batch=False, save_checksum=True)

    # Ensures the destination root directory exists.
    ensure_directory_exists(destination)

    # Collects all items (files and directories) in the source directory.
    all_items = tuple(source.rglob("*"))

    # Loops over all items (files and directories). Adds files to the file_list variable. Uses directories to reinstate
    # the source subdirectory hierarchy in the destination directory.
    file_list = []
    for item in sorted(all_items, key=lambda x: len(x.relative_to(source).parts)):
        # Recreates directory structure on destination
        if item.is_dir():
            dest_dir = destination / item.relative_to(source)
            dest_dir.mkdir(parents=True, exist_ok=True)
        # Also builds the list of files to be moved
        else:  # is_file()
            file_list.append(item)

    # Copies the data to the destination. For parallel workflows, the method uses the ThreadPoolExecutor to move
    # multiple files at the same time. Since I/O operations do not hold GIL, we do not need to parallelize with
    # Processes here.
    if num_threads > 1:
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {executor.submit(_transfer_file, file, source, destination): file for file in file_list}
            for future in tqdm(
                as_completed(futures),
                total=len(file_list),
                desc=f"Transferring files to {Path(*destination.parts[-6:])}",
                unit="file",
            ):
                # Propagates any exceptions from the file transfer.
                future.result()
    else:
        for file in tqdm(file_list, desc=f"Transferring files to {Path(*destination.parts[-6:])}", unit="file"):
            _transfer_file(file, source, destination)

    # Verifies the integrity of the transferred directory by rerunning xxHash3-128 calculation.
    if verify_integrity:
        destination_checksum = calculate_directory_checksum(directory=destination, batch=False, save_checksum=False)
        with source.joinpath("ax_checksum.txt").open("r") as local_checksum:
            message = (
                f"Checksum mismatch detected when transferring {Path(*source.parts[-6:])} to "
                f"{Path(*destination.parts[-6:])}! The data was likely corrupted in transmission."
            )
            if not destination_checksum == local_checksum.readline().strip():
                console.error(message=message, error=RuntimeError)
