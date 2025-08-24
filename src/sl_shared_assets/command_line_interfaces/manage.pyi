from typing import Any
from pathlib import Path

import click
from _typeshed import Incomplete

from ..tools import (
    acquire_lock as acquire_lock,
    release_lock as release_lock,
    archive_session as archive_session,
    prepare_session as prepare_session,
    resolve_checksum as resolve_checksum,
    generate_project_manifest as generate_project_manifest,
)

CONTEXT_SETTINGS: Incomplete

def manage() -> None:
    """This Command-Line Interface (CLI) allows managing session and project data acquired in the Sun lab.

    This CLI is intended to run on the Sun lab remote compute server(s) and should not be called by the end-user
    directly. Instead, commands from this CLI are designed to be accessed through the bindings in the sl-experiment and
    sl-forgery libraries.
    """

@click.pass_context
def manage_session(
    ctx: Any, session_path: Path, processed_data_root: Path | None, manager_id: int, reset_tracker: bool
) -> None:
    """This group provides commands for managing the data of a Sun lab data acquisition session.

    Commands from this group are used to support data processing and dataset-formation (forging) on remote compute
    servers."""

@click.pass_context
def lock_session(ctx: Any) -> None:
    """Acquires the lock for the target session's data.

    This command is used to ensure that the target session's data can only be accessed from the specified manager
    process. Calling this command is a prerequisite for all other session data management, processing, or dataset
    formation commands. If this command is called as part of runtime, the 'unlock' command must be called at the end
    of that runtime to properly release the session's data lock. This command respects the '--reset-tracker' flag of the
    'session' command group and, if this flag is present, forcibly resets the session lock file before re-acquiring it
    for the specified manager process.
    """

@click.pass_context
def unlock_session(ctx: Any) -> None:
    """Releases the lock for the target session's data.

    This command is used to reverse the effect of the 'lock' command, allowing other manager processes to work with
    the session's data. This command can only be called from the same manager process used to acquire the
    session's data lock.
    """

@click.pass_context
def resolve_session_checksum(ctx: Any, recalculate_checksum: bool) -> None:
    """Resolves the data integrity checksum for the target session's 'raw_data' directory.

    This command can be used to verify the integrity of the session's 'raw_data' directory using an existing
    checksum or to re-generate the checksum to reflect the current state of the directory. It only works with the
    'raw_data' session directory and ignores all other directories. Primarily, this command is used to verify the
    integrity of the session's data as it is transferred from data acquisition systems to long-term storage
    destinations.
    """

@click.pass_context
def prepare_session_for_processing(ctx: Any) -> None:
    """Prepares the target session for data processing by moving all session data to the working volume.

    This command is intended to run on remote compute servers that use slow HDD volumes to maximize data integrity and
    fast NVME volumes to maximize data processing speed. For such systems, moving the data to the fast volume before
    processing results in a measurable processing time decrease.
    """

@click.pass_context
def archive_session_for_storage(ctx: Any) -> None:
    """Prepares the target session for long-term storage by moving all session data to the storage volume.

    This command is primarily intended to run on remote compute servers that use slow HDD volumes to maximize data
    integrity and fast NVME volumes to maximize data processing speed. For such systems, moving all sessions that are no
    longer actively processed or analyzed to the slow drive volume frees up the processing volume space and ensures
    long-term data integrity.
    """

@click.pass_context
def manage_project(ctx: Any, project_path: Path, processed_data_root: Path | None) -> None:
    """This group provides commands for managing the data of a Sun lab project.

    Commands from this group are used to support all interactions with the data stored on the Sun lab remote compute
    server(s)."""

@click.pass_context
def generate_project_manifest_file(ctx: Any) -> None:
    """Generates the manifest .feather file that captures the current state of the target project's data.

    The manifest file contains the comprehensive snapshot of the available project's data. It includes the information
    about the management and processing pipelines that have been applied to each session's data, as well as the
    descriptive information about each session. The manifest file is used as an entry-point for all interactions with
    the Sun lab data stored on the remote compute server(s).
    """
