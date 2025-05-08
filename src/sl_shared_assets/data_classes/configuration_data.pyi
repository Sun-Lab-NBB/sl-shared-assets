from pathlib import Path as Path
from dataclasses import field, dataclass

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig

@dataclass()
class ExperimentState:
    """Encapsulates the information used to set and maintain the desired experiment and Mesoscope-VR system state.

    Primarily, experiment runtime logic (task logic) is resolved by the Unity game engine. However, the Mesoscope-VR
    system configuration may also need to change throughout the experiment to optimize the runtime by disabling or
    reconfiguring specific hardware modules. For example, some experiment stages may require the running wheel to be
    locked to prevent the animal from running, and other may require the VR screens to be turned off.
    """

    experiment_state_code: int
    vr_state_code: int
    state_duration_s: float

@dataclass()
class ExperimentConfiguration(YamlConfig):
    """Stores the configuration of a single experiment runtime.

    Primarily, this includes the sequence of experiment and Virtual Reality (Mesoscope-VR) states that defines the flow
    of the experiment runtime. During runtime, the main runtime control function traverses the sequence of states
    stored in this class instance start-to-end in the exact order specified by the user. Together with custom Unity
    projects that define the task logic (how the system responds to animal interactions with the VR system) this class
    allows flexibly implementing a wide range of experiments.

    Each project should define one or more experiment configurations and save them as .yaml files inside the project
    'configuration' folder. The name for each configuration file is defined by the user and is used to identify and load
    the experiment configuration when 'sl-run-experiment' CLI command exposed by the sl-experiment library is executed.
    """

    cue_map: dict[int, float] = field(default_factory=Incomplete)
    experiment_states: dict[str, ExperimentState] = field(default_factory=Incomplete)
