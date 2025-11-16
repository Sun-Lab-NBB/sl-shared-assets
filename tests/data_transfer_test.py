from pathlib import Path
import multiprocessing

multiprocessing.set_start_method("spawn")  # Improves reproducibility.
import os

import pytest

from sl_shared_assets import (
    delete_directory,
    transfer_directory,
    calculate_directory_checksum,
)


@pytest.fixture
def sample_directory_structure(tmp_path) -> Path:
    """Creates a sample directory structure for testing.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Returns:
        Path to the root of the created directory structure.
    """
    root = tmp_path / "test_source"
    root.mkdir()

    # Creates files in root
    (root / "file1.txt").write_text("content1")
    (root / "file2.txt").write_text("content2")

    # Creates subdirectories with files
    subdir1 = root / "subdir1"
    subdir1.mkdir()
    (subdir1 / "file3.txt").write_text("content3")
    (subdir1 / "file4.txt").write_text("content4")

    subdir2 = root / "subdir2"
    subdir2.mkdir()
    (subdir2 / "file5.txt").write_text("content5")

    # Creates a nested subdirectory
    nested = subdir1 / "nested"
    nested.mkdir()
    (nested / "file6.txt").write_text("content6")

    return root


@pytest.fixture
def large_directory_structure(tmp_path) -> Path:
    """Creates a larger directory structure for performance testing.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Returns:
        Path to the root of the created directory structure.
    """
    root = tmp_path / "large_source"
    root.mkdir()

    # Creates multiple files and subdirectories
    for i in range(20):
        (root / f"file_{i}.txt").write_text(f"content_{i}" * 100)

    for i in range(5):
        subdir = root / f"subdir_{i}"
        subdir.mkdir()
        for j in range(10):
            (subdir / f"file_{j}.txt").write_text(f"nested_content_{i}_{j}" * 50)

    return root


def test_delete_directory_basic(tmp_path):
    """Verifies basic directory deletion functionality.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    # Creates a simple directory structure
    test_dir = tmp_path / "to_delete"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content")
    (test_dir / "file2.txt").write_text("content")

    # Verifies directory exists
    assert test_dir.exists()

    # Deletes directory
    delete_directory(test_dir)

    # Verifies directory is gone
    assert not test_dir.exists()


def test_delete_directory_nested(tmp_path):
    """Verifies deletion of nested directory structures.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    # Creates nested structure
    root = tmp_path / "nested_root"
    root.mkdir()
    level1 = root / "level1"
    level1.mkdir()
    level2 = level1 / "level2"
    level2.mkdir()

    # Adds files at each level
    (root / "file1.txt").write_text("content1")
    (level1 / "file2.txt").write_text("content2")
    (level2 / "file3.txt").write_text("content3")

    # Deletes entire structure
    delete_directory(root)

    # Verifies all levels are deleted
    assert not root.exists()
    assert not level1.exists()
    assert not level2.exists()


def test_delete_directory_nonexistent(tmp_path):
    """Verifies that deleting a non-existent directory does not raise errors.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    nonexistent = tmp_path / "does_not_exist"
    # Should not raise any exception
    delete_directory(nonexistent)


def test_delete_directory_empty(tmp_path):
    """Verifies deletion of empty directories.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    assert empty_dir.exists()
    delete_directory(empty_dir)
    assert not empty_dir.exists()


def test_transfer_directory_basic(sample_directory_structure, tmp_path):
    """Verifies basic directory transfer functionality.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = sample_directory_structure
    destination = tmp_path / "test_destination"

    # Performs transfer
    transfer_directory(source=source, destination=destination)

    # Verifies destination exists
    assert destination.exists()

    # Verifies all files were transferred
    assert (destination / "file1.txt").exists()
    assert (destination / "file2.txt").exists()
    assert (destination / "subdir1" / "file3.txt").exists()
    assert (destination / "subdir1" / "file4.txt").exists()
    assert (destination / "subdir2" / "file5.txt").exists()
    assert (destination / "subdir1" / "nested" / "file6.txt").exists()

    # Verifies content integrity
    assert (destination / "file1.txt").read_text() == "content1"
    assert (destination / "subdir1" / "nested" / "file6.txt").read_text() == "content6"

    # Verifies source still exists (no removal)
    assert source.exists()


@pytest.mark.parametrize("num_threads", [1, 2, 4, -1])
def test_transfer_directory_multithreading(sample_directory_structure, tmp_path, num_threads):
    """Verifies that transfer_directory works correctly with different thread counts.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
        num_threads: Number of threads to use for transfer.
    """
    source = sample_directory_structure
    destination = tmp_path / f"dest_threads_{num_threads}"

    transfer_directory(source=source, destination=destination, num_threads=num_threads)

    # Verifies all files were transferred correctly
    assert (destination / "file1.txt").exists()
    assert (destination / "subdir1" / "file3.txt").exists()
    assert (destination / "subdir1" / "nested" / "file6.txt").exists()

    # Verifies content
    assert (destination / "file1.txt").read_text() == "content1"


def test_transfer_directory_with_removal(sample_directory_structure, tmp_path):
    """Verifies that the source directory is removed when remove_source=True.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_with_removal"

    # Stores original file count
    original_files = list(source.rglob("*.txt"))
    assert len(original_files) > 0

    # Performs transfer with removal
    transfer_directory(source=source, destination=destination, remove_source=True)

    # Verifies destination has all files
    transferred_files = list(destination.rglob("*.txt"))
    assert len(transferred_files) == len(original_files)

    # Verifies the source is deleted
    assert not source.exists()


def test_transfer_directory_with_integrity_check(sample_directory_structure, tmp_path):
    """Verifies the integrity verification feature of transfer_directory.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_integrity"

    # Performs transfer with integrity verification
    transfer_directory(source=source, destination=destination, verify_integrity=True)

    # Verifies destination exists and has correct files
    assert destination.exists()
    assert (destination / "file1.txt").exists()
    assert (destination / "subdir1" / "file3.txt").exists()

    # Verifies the checksum file was created in the source
    assert (source / "ax_checksum.txt").exists()


def test_transfer_directory_with_existing_checksum(sample_directory_structure, tmp_path):
    """Verifies transfer when the checksum file already exists.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_existing_checksum"

    # Pre-creates checksum
    calculate_directory_checksum(directory=source, progress=False, save_checksum=True)
    assert (source / "ax_checksum.txt").exists()

    # Performs transfer with verification
    transfer_directory(source=source, destination=destination, verify_integrity=True)

    # Verifies successful transfer
    assert destination.exists()
    assert (destination / "file1.txt").read_text() == "content1"


def test_transfer_directory_nonexistent_source(tmp_path):
    """Verifies that transferring a non-existent source raises FileNotFoundError.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = tmp_path / "nonexistent"
    destination = tmp_path / "destination"

    with pytest.raises(FileNotFoundError):
        transfer_directory(source=source, destination=destination)


def test_transfer_directory_preserves_structure(tmp_path):
    """Verifies that complex directory hierarchies are preserved during transfer.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    # Creates complex structure
    source = tmp_path / "complex_source"
    source.mkdir()

    # Creates multiple levels
    (source / "level1").mkdir()
    (source / "level1" / "level2").mkdir()
    (source / "level1" / "level2" / "level3").mkdir()
    (source / "level1" / "sibling").mkdir()

    # Adds files at different levels
    (source / "root.txt").write_text("root")
    (source / "level1" / "l1.txt").write_text("level1")
    (source / "level1" / "level2" / "l2.txt").write_text("level2")
    (source / "level1" / "level2" / "level3" / "l3.txt").write_text("level3")
    (source / "level1" / "sibling" / "sib.txt").write_text("sibling")

    destination = tmp_path / "complex_dest"
    transfer_directory(source=source, destination=destination)

    # Verifies structure
    assert (destination / "root.txt").exists()
    assert (destination / "level1" / "l1.txt").exists()
    assert (destination / "level1" / "level2" / "l2.txt").exists()
    assert (destination / "level1" / "level2" / "level3" / "l3.txt").exists()
    assert (destination / "level1" / "sibling" / "sib.txt").exists()

    # Verifies content
    assert (destination / "level1" / "level2" / "level3" / "l3.txt").read_text() == "level3"


def test_transfer_directory_empty_source(tmp_path):
    """Verifies transfer of an empty directory.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = tmp_path / "empty_source"
    source.mkdir()
    destination = tmp_path / "empty_dest"

    transfer_directory(source=source, destination=destination)

    # Verifies destination exists but is empty
    assert destination.exists()
    assert len(list(destination.iterdir())) == 0


def test_transfer_directory_large_dataset(large_directory_structure, tmp_path):
    """Verifies transfer of a larger directory structure with multiple threads.

    Args:
        large_directory_structure: Fixture providing a large directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = large_directory_structure
    destination = tmp_path / "large_dest"

    # Counts files in the source
    source_files = list(source.rglob("*.txt"))
    source_count = len(source_files)

    # Performs parallel transfer
    transfer_directory(source=source, destination=destination, num_threads=4)

    # Verifies all files transferred
    dest_files = list(destination.rglob("*.txt"))
    assert len(dest_files) == source_count

    # Spot checks some files
    assert (destination / "file_0.txt").exists()
    assert (destination / "subdir_0" / "file_0.txt").exists()


def test_transfer_directory_with_integrity_and_removal(sample_directory_structure, tmp_path):
    """Verifies combined integrity verification and source removal.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_integrity_removal"

    # Performs transfer with both options
    transfer_directory(
        source=source,
        destination=destination,
        verify_integrity=True,
        remove_source=True,
    )

    # Verifies destination has files
    assert destination.exists()
    assert (destination / "file1.txt").exists()
    assert (destination / "subdir1" / "file3.txt").exists()

    # Verifies the source is removed
    assert not source.exists()


def test_delete_directory_parallel_performance(tmp_path):
    """Verifies that parallel deletion works with many files.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    # Creates a directory with many files
    test_dir = tmp_path / "many_files"
    test_dir.mkdir()

    for i in range(100):
        (test_dir / f"file_{i}.txt").write_text(f"content_{i}")

    # Creates subdirectories
    for i in range(10):
        subdir = test_dir / f"subdir_{i}"
        subdir.mkdir()
        for j in range(10):
            (subdir / f"file_{j}.txt").write_text(f"content_{i}_{j}")

    # Verifies creation
    assert test_dir.exists()
    file_count = len(list(test_dir.rglob("*.txt")))
    assert file_count == 200

    # Deletes in parallel
    delete_directory(test_dir)

    # Verifies deletion
    assert not test_dir.exists()


def test_transfer_directory_metadata_preservation(sample_directory_structure, tmp_path):
    """Verifies that file metadata is preserved during transfer.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_metadata"

    # Gets original file stats
    original_file = source / "file1.txt"
    original_stat = original_file.stat()

    # Performs transfer
    transfer_directory(source=source, destination=destination)

    # Gets transferred file stats
    transferred_file = destination / "file1.txt"
    transferred_stat = transferred_file.stat()

    # Verifies metadata (shutil.copy2 should preserve modification time)
    assert transferred_stat.st_size == original_stat.st_size
    # Note: Depending on filesystem, mtime might not be exactly preserved
    # but should be very close
    assert abs(transferred_stat.st_mtime - original_stat.st_mtime) < 1


def test_transfer_directory_to_existing_destination(sample_directory_structure, tmp_path):
    """Verifies transfer when the destination directory already exists.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = sample_directory_structure
    destination = tmp_path / "existing_dest"

    # Pre-creates destination
    destination.mkdir()
    (destination / "existing_file.txt").write_text("existing")

    # Performs transfer
    transfer_directory(source=source, destination=destination)

    # Verifies both old and new files exist
    assert (destination / "existing_file.txt").exists()
    assert (destination / "file1.txt").exists()
    assert (destination / "subdir1" / "file3.txt").exists()


def test_transfer_directory_single_vs_multi_thread_consistency(sample_directory_structure, tmp_path):
    """Verifies that single-threaded and multithreaded transfers produce identical results.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    source = sample_directory_structure
    dest_single = tmp_path / "dest_single"
    dest_multi = tmp_path / "dest_multi"

    # Single-threaded transfer
    transfer_directory(source=source, destination=dest_single, num_threads=1)

    # Multithreaded transfer
    transfer_directory(source=source, destination=dest_multi, num_threads=4)

    # Compares file lists
    single_files = sorted([f.relative_to(dest_single) for f in dest_single.rglob("*") if f.is_file()])
    multi_files = sorted([f.relative_to(dest_multi) for f in dest_multi.rglob("*") if f.is_file()])

    assert single_files == multi_files

    # Verifies content matches
    for rel_path in single_files:
        single_content = (dest_single / rel_path).read_text()
        multi_content = (dest_multi / rel_path).read_text()
        assert single_content == multi_content


def test_calculate_directory_checksum_basic(sample_directory_structure):
    """Verifies basic checksum calculation functionality.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
    """
    checksum = calculate_directory_checksum(directory=sample_directory_structure, save_checksum=False)

    # Verifies checksum is a valid hex string
    assert isinstance(checksum, str)
    assert len(checksum) == 32  # xxHash3-128 produces 128-bit = 32 hex chars
    assert all(c in "0123456789abcdef" for c in checksum)


def test_calculate_directory_checksum_saves_file(sample_directory_structure):
    """Verifies that the checksum file is saved when save_checksum=True.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
    """
    checksum = calculate_directory_checksum(directory=sample_directory_structure, save_checksum=True)

    # Verifies checksum file exists
    checksum_file = sample_directory_structure / "ax_checksum.txt"
    assert checksum_file.exists()

    # Verifies file content matches returned checksum
    saved_checksum = checksum_file.read_text().strip()
    assert saved_checksum == checksum


def test_calculate_directory_checksum_consistency(sample_directory_structure):
    """Verifies that calculating checksum multiple times produces identical results.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
    """
    checksum1 = calculate_directory_checksum(directory=sample_directory_structure, save_checksum=False)
    checksum2 = calculate_directory_checksum(directory=sample_directory_structure, save_checksum=False)
    checksum3 = calculate_directory_checksum(directory=sample_directory_structure, save_checksum=False)

    assert checksum1 == checksum2 == checksum3


@pytest.mark.parametrize("num_processes", [1, 2, 4, None])
def test_calculate_directory_checksum_multiprocessing(sample_directory_structure, num_processes):
    """Verifies that checksum calculation produces consistent results with different process counts.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        num_processes: Number of processes to use for checksum calculation.
    """
    checksum = calculate_directory_checksum(
        directory=sample_directory_structure, num_processes=num_processes, save_checksum=False
    )

    # Verifies checksum is valid
    assert isinstance(checksum, str)
    assert len(checksum) == 32

    # Verifies consistency across different process counts by comparing with a single process
    checksum_single = calculate_directory_checksum(
        directory=sample_directory_structure, num_processes=1, save_checksum=False
    )
    assert checksum == checksum_single


@pytest.mark.parametrize("progress", [True, False])
def test_calculate_directory_checksum_progress_mode(sample_directory_structure, progress):
    """Verifies that progress mode produces identical checksums (only affects progress display).

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        progress: Whether to enable progress tracking.
    """
    checksum = calculate_directory_checksum(
        directory=sample_directory_structure, progress=progress, save_checksum=False
    )

    # Verifies checksum is valid
    assert isinstance(checksum, str)
    assert len(checksum) == 32


def test_calculate_directory_checksum_excludes_service_files(tmp_path):
    """Verifies that service files are excluded from checksum calculation.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    # Creates a directory with regular and service files
    test_dir = tmp_path / "test_exclude"
    test_dir.mkdir()

    (test_dir / "regular_file.txt").write_text("content")
    (test_dir / "ax_checksum.txt").write_text("should_be_excluded")
    (test_dir / "nk.bin").write_bytes(b"excluded_binary")

    checksum_with_service = calculate_directory_checksum(directory=test_dir, save_checksum=False)

    # Creates identical directory without service files
    test_dir2 = tmp_path / "test_no_service"
    test_dir2.mkdir()
    (test_dir2 / "regular_file.txt").write_text("content")

    checksum_without_service = calculate_directory_checksum(directory=test_dir2, save_checksum=False)

    # Verifies checksums match (service files were excluded)
    assert checksum_with_service == checksum_without_service


def test_calculate_directory_checksum_empty_directory(tmp_path):
    """Verifies checksum calculation for an empty directory.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    checksum = calculate_directory_checksum(directory=empty_dir, save_checksum=False)

    # Verifies a valid checksum is still generated
    assert isinstance(checksum, str)
    assert len(checksum) == 32


def test_calculate_directory_checksum_content_sensitivity(tmp_path):
    """Verifies that checksum changes when file content changes.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    test_dir = tmp_path / "content_test"
    test_dir.mkdir()

    # Creates the initial file
    (test_dir / "file.txt").write_text("original content")
    checksum1 = calculate_directory_checksum(directory=test_dir, save_checksum=False)

    # Modifies content
    (test_dir / "file.txt").write_text("modified content")
    checksum2 = calculate_directory_checksum(directory=test_dir, save_checksum=False)

    # Verifies checksums differ
    assert checksum1 != checksum2


def test_calculate_directory_checksum_structure_sensitivity(tmp_path):
    """Verifies that checksum changes when the directory structure changes.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    test_dir = tmp_path / "structure_test"
    test_dir.mkdir()

    # Creates initial structure
    (test_dir / "file.txt").write_text("content")
    checksum1 = calculate_directory_checksum(directory=test_dir, save_checksum=False)

    # Adds a new file
    (test_dir / "file2.txt").write_text("content")
    checksum2 = calculate_directory_checksum(directory=test_dir, save_checksum=False)

    # Verifies checksums differ
    assert checksum1 != checksum2


def test_calculate_directory_checksum_path_sensitivity(tmp_path):
    """Verifies that checksum reflects file paths (not just content).

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    # Creates two directories with the same content but different paths
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    (dir1 / "path_a").mkdir()
    (dir1 / "path_a" / "file.txt").write_text("same content")

    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    (dir2 / "path_b").mkdir()
    (dir2 / "path_b" / "file.txt").write_text("same content")

    checksum1 = calculate_directory_checksum(directory=dir1, save_checksum=False)
    checksum2 = calculate_directory_checksum(directory=dir2, save_checksum=False)

    # Verifies checksums differ due to different paths
    assert checksum1 != checksum2


def test_calculate_directory_checksum_large_files(tmp_path):
    """Verifies checksum calculation with large files (tests chunked reading).

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    test_dir = tmp_path / "large_files"
    test_dir.mkdir()

    # Creates a file larger than the chunk size (8 MB chunks in implementation)
    large_content = b"x" * (10 * 1024 * 1024)  # 10 MB
    (test_dir / "large_file.bin").write_bytes(large_content)

    checksum1 = calculate_directory_checksum(directory=test_dir, save_checksum=False)

    # Verifies checksum is generated
    assert isinstance(checksum1, str)
    assert len(checksum1) == 32

    # Verifies consistency
    checksum2 = calculate_directory_checksum(directory=test_dir, save_checksum=False)
    assert checksum1 == checksum2


def test_calculate_directory_checksum_nested_structure(tmp_path):
    """Verifies checksum calculation with deeply nested directory structures.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    # Creates a deeply nested structure
    test_dir = tmp_path / "nested"
    current = test_dir
    for i in range(5):
        current /= f"level_{i}"
        current.mkdir(parents=True, exist_ok=True)
        (current / f"file_{i}.txt").write_text(f"content_{i}")

    checksum = calculate_directory_checksum(directory=test_dir, save_checksum=False)

    # Verifies checksum is valid
    assert isinstance(checksum, str)
    assert len(checksum) == 32


def test_calculate_directory_checksum_with_existing_checksum_file(tmp_path):
    """Verifies behavior when the checksum file already exists.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    test_dir = tmp_path / "existing_checksum"
    test_dir.mkdir()
    (test_dir / "file.txt").write_text("content")

    # Pre-creates a checksum file with wrong content
    (test_dir / "ax_checksum.txt").write_text("old_checksum_value")

    # Calculates new checksum with save enabled
    new_checksum = calculate_directory_checksum(directory=test_dir, save_checksum=True)

    # Verifies a file is overwritten with correct checksum
    saved_checksum = (test_dir / "ax_checksum.txt").read_text().strip()
    assert saved_checksum == new_checksum
    assert saved_checksum != "old_checksum_value"


def test_calculate_directory_checksum_different_structures(tmp_path):
    """Verifies that different directory structures produce different checksums.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    # Creates first structure
    dir1 = tmp_path / "struct1"
    dir1.mkdir()
    (dir1 / "a.txt").write_text("content_a")
    (dir1 / "b.txt").write_text("content_b")

    # Creates second structure with same files in subdirectory
    dir2 = tmp_path / "struct2"
    dir2.mkdir()
    subdir = dir2 / "subdir"
    subdir.mkdir()
    (subdir / "a.txt").write_text("content_a")
    (subdir / "b.txt").write_text("content_b")

    checksum1 = calculate_directory_checksum(directory=dir1, save_checksum=False)
    checksum2 = calculate_directory_checksum(directory=dir2, save_checksum=False)

    # Verifies different structures produce different checksums
    assert checksum1 != checksum2


def test_calculate_directory_checksum_binary_files(tmp_path):
    """Verifies checksum calculation with binary files.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    """
    test_dir = tmp_path / "binary_test"
    test_dir.mkdir()

    # Creates various binary files
    (test_dir / "data.bin").write_bytes(bytes(range(256)))
    (test_dir / "zeros.bin").write_bytes(b"\x00" * 1000)
    (test_dir / "random.bin").write_bytes(os.urandom(500))

    checksum = calculate_directory_checksum(directory=test_dir, save_checksum=False)

    # Verifies checksum is valid
    assert isinstance(checksum, str)
    assert len(checksum) == 32

    # Verifies consistency
    checksum2 = calculate_directory_checksum(directory=test_dir, save_checksum=False)
    assert checksum == checksum2


def test_transfer_directory_integrity_check_detects_corruption(sample_directory_structure, tmp_path, monkeypatch):
    """Verifies that integrity verification detects corrupted transfers.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying behavior.

    This test simulates a corrupted file transfer by monkeypatching the checksum
    calculation to return different values for source and destination.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_corrupted"

    # Tracks which directory is being checksummed
    checksum_calls = []
    original_calculate_checksum = calculate_directory_checksum

    def mock_calculate_checksum(directory, progress=False, save_checksum=False, num_processes=None):
        """Mocks calculate_directory_checksum to return different values for source and destination."""
        checksum_calls.append(directory)
        result = original_calculate_checksum(
            directory=directory, progress=progress, save_checksum=save_checksum, num_processes=num_processes
        )

        # Returns different checksum for destination to simulate corruption
        if directory == destination:
            return "corrupted_checksum_00000000000000"
        return result

    # Applies monkeypatch
    monkeypatch.setattr(
        "sl_shared_assets.data_transfer.transfer_tools.calculate_directory_checksum", mock_calculate_checksum
    )

    # Attempts transfer with integrity verification
    with pytest.raises(RuntimeError) as exc_info:
        transfer_directory(
            source=source,
            destination=destination,
            verify_integrity=True,
        )

    # Verifies the error message contains expected information
    # Normalizes whitespace since the error message may contain line breaks
    error_message = str(exc_info.value).replace("\n", " ")
    assert "Checksum mismatch detected" in error_message
    assert "corrupted in transmission" in error_message

    # Verifies both source and destination were checksummed
    assert len(checksum_calls) >= 2  # At least initial checksum and verification


def test_transfer_directory_checksum_path_truncation(tmp_path, monkeypatch):
    """Verifies that error messages truncate long paths to the last 6 parts.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying behavior.

    This test verifies the Path(*parts[-6:]) truncation in error messages.
    """
    # Creates the deeply nested source path
    source = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "source"
    source.mkdir(parents=True)
    (source / "file.txt").write_text("content")

    destination = tmp_path / "x" / "y" / "z" / "w" / "v" / "u" / "dest"
    destination.mkdir(parents=True)

    # Pre-calculates checksum
    calculate_directory_checksum(directory=source, save_checksum=True)

    # Tracks the original function
    original_calculate_checksum = calculate_directory_checksum

    # Mocks calculate_directory_checksum to return a corrupted hash for destination
    def mock_calculate(directory, progress=False, save_checksum=False, num_processes=None):
        result = original_calculate_checksum(
            directory=directory, progress=progress, save_checksum=save_checksum, num_processes=num_processes
        )
        if directory == destination:
            return "corrupted_hash_00000000000000"
        return result

    # Applies a monkeypatch to where the function is called in transfer_tools
    monkeypatch.setattr("sl_shared_assets.data_transfer.transfer_tools.calculate_directory_checksum", mock_calculate)

    with pytest.raises(RuntimeError) as exc_info:
        transfer_directory(
            source=source,
            destination=destination,
            verify_integrity=True,
        )

    # Verifies the error message contains truncated paths (not full paths)
    error_message = str(exc_info.value)
    assert "Checksum mismatch detected" in error_message

    # Verifies the paths show the last 6 parts (e/f/source and v/u/dest)
    # The Path(*parts[-6:]) will show just the meaningful components
    assert "e/f/source" in error_message or "e\\f\\source" in error_message  # Unix or Windows path separator
    assert "v/u/dest" in error_message or "v\\u\\dest" in error_message


def test_transfer_directory_integrity_check_corruption_prevents_removal(
    sample_directory_structure, tmp_path, monkeypatch
):
    """Verifies that the source is NOT removed when an integrity check fails.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for modifying behavior.

    This test ensures that if a transfer is corrupted, the source data is preserved.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_corrupted_no_removal"

    # Mocks checksum to simulate corruption
    original_calculate_checksum = calculate_directory_checksum

    def mock_calculate_checksum(directory, progress=False, save_checksum=False, num_processes=None):
        result = original_calculate_checksum(
            directory=directory, progress=progress, save_checksum=save_checksum, num_processes=num_processes
        )
        if directory == destination:
            return "different_checksum_1234567890abcd"
        return result

    monkeypatch.setattr(
        "sl_shared_assets.data_transfer.transfer_tools.calculate_directory_checksum", mock_calculate_checksum
    )

    # Attempts transfer with both verification and removal enabled
    with pytest.raises(RuntimeError):
        transfer_directory(
            source=source,
            destination=destination,
            verify_integrity=True,
            remove_source=True,
        )

    # Verifies the source still exists (was not removed due to failed verification)
    assert source.exists()
    assert (source / "file1.txt").exists()


def test_transfer_directory_integrity_check_with_progress(sample_directory_structure, tmp_path):
    """Verifies that integrity verification works with progress tracking enabled.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures progress bars don't interfere with integrity verification.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_progress_integrity"

    # Performs transfer with both progress and integrity enabled
    transfer_directory(
        source=source,
        destination=destination,
        verify_integrity=True,
        progress=True,
    )

    # Verifies successful transfer
    assert destination.exists()
    assert (destination / "file1.txt").exists()
    assert (destination / "subdir1" / "file3.txt").exists()

    # Verifies the checksum file exists
    assert (source / "ax_checksum.txt").exists()


def test_transfer_directory_creates_checksum_when_missing(tmp_path):
    """Verifies that checksum is automatically created if missing when verify_integrity=True.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the function handles missing checksums gracefully.
    """
    # Creates the source without a pre-calculated checksum
    source = tmp_path / "source_no_checksum"
    source.mkdir()
    (source / "file1.txt").write_text("content1")
    (source / "file2.txt").write_text("content2")

    destination = tmp_path / "dest_auto_checksum"

    # Verifies no checksum exists initially
    assert not (source / "ax_checksum.txt").exists()

    # Performs transfer with integrity verification
    transfer_directory(
        source=source,
        destination=destination,
        verify_integrity=True,
    )

    # Verifies checksum was automatically created
    assert (source / "ax_checksum.txt").exists()

    # Verifies successful transfer
    assert destination.exists()
    assert (destination / "file1.txt").read_text() == "content1"


def test_transfer_directory_preserves_checksum_file(sample_directory_structure, tmp_path):
    """Verifies that the original checksum file is preserved in the source.

    Args:
        sample_directory_structure: Fixture providing a sample directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures the checksum file created during transfer remains in the source.
    """
    source = sample_directory_structure
    destination = tmp_path / "dest_checksum_preserved"

    # Verifies no checksum initially
    assert not (source / "ax_checksum.txt").exists()

    # Performs transfer with integrity verification
    transfer_directory(
        source=source,
        destination=destination,
        verify_integrity=True,
    )

    # Verifies the checksum file exists and persists in the source
    assert (source / "ax_checksum.txt").exists()

    # Verifies the checksum file is readable and valid
    checksum_content = (source / "ax_checksum.txt").read_text().strip()
    assert len(checksum_content) == 32  # xxHash3-128 hex string
    assert all(c in "0123456789abcdef" for c in checksum_content)


def test_transfer_directory_integrity_multithread_consistency(large_directory_structure, tmp_path):
    """Verifies that integrity checking works correctly with multithreaded transfers.

    Args:
        large_directory_structure: Fixture providing a large directory structure.
        tmp_path: Pytest fixture providing a temporary directory path.

    This test ensures parallel file transfers don't compromise integrity verification.
    """
    source = large_directory_structure
    destination = tmp_path / "dest_multi_integrity"

    # Performs multithreaded transfer with integrity verification
    transfer_directory(
        source=source,
        destination=destination,
        num_threads=4,
        verify_integrity=True,
    )

    # Verifies all files transferred correctly
    source_files = sorted([f.relative_to(source) for f in source.rglob("*.txt")])
    dest_files = sorted([f.relative_to(destination) for f in destination.rglob("*.txt")])

    assert source_files == dest_files

    # Spot checks file contents
    assert (destination / "file_0.txt").exists()
    assert (destination / "subdir_0" / "file_0.txt").exists()

    # Verifies the source checksum file was created
    assert (source / "ax_checksum.txt").exists()
