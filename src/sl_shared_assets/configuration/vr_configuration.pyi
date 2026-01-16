from enum import StrEnum
from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

class TriggerType(StrEnum):
    LICK = "lick"
    OCCUPANCY = "occupancy"

_UINT8_MAX: int
_PROBABILITY_SUM_TOLERANCE: float

@dataclass
class Cue:
    name: str
    code: int
    length_cm: float
    def __post_init__(self) -> None: ...

@dataclass
class Segment:
    name: str
    cue_sequence: list[str]
    transition_probabilities: list[float] | None
    def __post_init__(self) -> None: ...

@dataclass
class VREnvironment:
    corridor_spacing_cm: float
    segments_per_corridor: int
    padding_prefab_name: str
    cm_per_unity_unit: float

@dataclass
class TrialStructure:
    segment_name: str
    stimulus_trigger_zone_start_cm: float
    stimulus_trigger_zone_end_cm: float
    stimulus_location_cm: float
    show_stimulus_collision_boundary: bool
    trigger_type: str | TriggerType

@dataclass
class TaskTemplate(YamlConfig):
    cues: list[Cue]
    segments: list[Segment]
    trial_structures: dict[str, TrialStructure]
    vr_environment: VREnvironment
    cue_offset_cm: float
    @property
    def _cue_by_name(self) -> dict[str, Cue]: ...
    @property
    def _segment_by_name(self) -> dict[str, Segment]: ...
    def _get_segment_length_cm(self, segment_name: str) -> float: ...
    def __post_init__(self) -> None: ...
    @staticmethod
    def _validate_zone_positions(trial_name: str, trial_structure: TrialStructure, segment_length: float) -> None: ...
