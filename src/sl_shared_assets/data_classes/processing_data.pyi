from enum import IntEnum, StrEnum
from pathlib import Path
from dataclasses import field, dataclass

from ataraxis_data_structures import YamlConfig

class TrackerFiles(StrEnum):
    MANIFEST = "manifest_generation_tracker.yaml"
    CHECKSUM = "checksum_resolution_tracker.yaml"
    TRANSFER = "data_transfer_tracker.yaml"
    BEHAVIOR = "behavior_processing_tracker.yaml"
    SUITE2P = "suite2p_processing_tracker.yaml"
    VIDEO = "video_processing_tracker.yaml"
    MULTIDAY = "multiday_processing_tracker.yaml"
    FORGING = "dataset_forging_tracker.yaml"

class ProcessingPipelines(StrEnum):
    MANIFEST = "manifest generation"
    CHECKSUM = "checksum resolution"
    TRANSFER = "data transfer"
    BEHAVIOR = "behavior processing"
    SUITE2P = "single-day suite2p processing"
    VIDEO = "video processing"
    MULTIDAY = "multi-day suite2p processing"
    FORGING = "dataset forging"

class ProcessingStatus(IntEnum):
    RUNNING = 0
    SUCCEEDED = 1
    FAILED = 2
    ABORTED = 3

@dataclass()
class ProcessingTracker(YamlConfig):
    file_path: Path
    _complete: bool = ...
    _encountered_error: bool = ...
    _running: bool = ...
    _manager_id: int = ...
    lock_path: str = field(init=False)
    _job_count: int = ...
    _completed_jobs: int = ...
    def __post_init__(self) -> None: ...
    def _load_state(self) -> None: ...
    def _save_state(self) -> None: ...
    def start(self, manager_id: int, job_count: int = 1) -> None: ...
    def error(self, manager_id: int) -> None: ...
    def stop(self, manager_id: int) -> None: ...
    def abort(self) -> None: ...
    @property
    def complete(self) -> bool: ...
    @property
    def encountered_error(self) -> bool: ...
    @property
    def running(self) -> bool: ...
