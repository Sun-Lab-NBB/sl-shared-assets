from enum import IntEnum, StrEnum
from pathlib import Path
from dataclasses import field, dataclass

from ataraxis_data_structures import YamlConfig

class ProcessingPipelines(StrEnum):
    MANIFEST = "manifest"
    ADOPTION = "adoption"
    CHECKSUM = "checksum"
    BEHAVIOR = "behavior"
    VIDEO = "video"
    SUITE2P = "suite2p"
    MULTIDAY = "multiday"
    FORGING = "forging"
    REPORT = "report"

class ManagingTrackers(StrEnum):
    CHECKSUM = "checksum.yaml"
    MANIFEST = "manifest.yaml"

class ProcessingTrackers(StrEnum):
    SUITE2P = "suite2p.yaml"
    BEHAVIOR = "behavior.yaml"
    VIDEO = "video.yaml"

class DatasetTrackers(StrEnum):
    FORGING = "forging.yaml"
    MULTIDAY = "multiday.yaml"

class ProcessingStatus(IntEnum):
    SCHEDULED = 0
    RUNNING = 1
    SUCCEEDED = 2
    FAILED = 3

@dataclass
class JobState:
    status: ProcessingStatus = ...
    slurm_job_id: int | None = ...

@dataclass()
class ProcessingTracker(YamlConfig):
    file_path: Path
    jobs: dict[str, JobState] = field(default_factory=dict)
    lock_path: str = field(init=False)
    def __post_init__(self) -> None: ...
    @staticmethod
    def generate_job_id(session_path: Path, job_name: str) -> str: ...
    @staticmethod
    def _get_slurm_job_id() -> int | None: ...
    def _load_state(self) -> None: ...
    def _save_state(self) -> None: ...
    def initialize_jobs(self, job_ids: list[str]) -> None: ...
    def start_job(self, job_id: str) -> None: ...
    def complete_job(self, job_id: str) -> None: ...
    def fail_job(self, job_id: str) -> None: ...
    def get_job_status(self, job_id: str) -> ProcessingStatus: ...
    def reset(self) -> None: ...
    @property
    def complete(self) -> bool: ...
    @property
    def encountered_error(self) -> bool: ...
