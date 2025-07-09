from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

@dataclass()
class MesoscopeHardwareState(YamlConfig):
    """Stores configuration parameters (states) of the Mesoscope-VR system hardware modules used during training or
    experiment runtime.

    This information is used to read and decode the data saved to the .npz log files during runtime as part of data
    processing.

    Notes:
        This class stores 'static' Mesoscope-VR system configuration that does not change during experiment or training
        session runtime. This is in contrast to MesoscopeExperimentState class, which reflects the 'dynamic' state of
        the Mesoscope-VR system.

        This class partially overlaps with the MesoscopeSystemConfiguration class, which is also stored in the
        raw_data folder of each session. The primary reason to keep both classes is to ensure that the math (rounding)
        used during runtime matches the math (rounding) used during data processing. MesoscopeSystemConfiguration does
        not do any rounding or otherwise attempt to be repeatable, which is in contrast to hardware module that read
        those parameters. Reading values from this class guarantees the read value exactly matches the value used
        during runtime.

    Notes:
        All fields in this dataclass initialize to None. During log processing, any log associated with a hardware
        module that provides the data stored in a field will be processed, unless that field is None. Therefore, setting
        any field in this dataclass to None also functions as a flag for whether to parse the log associated with the
        module that provides this field's information.

        This class is automatically configured by _MesoscopeExperiment and _BehaviorTraining classes from sl-experiment
        library to facilitate log parsing.
    """

    cue_map: dict[int, float] | None = ...
    cm_per_pulse: float | None = ...
    maximum_break_strength: float | None = ...
    minimum_break_strength: float | None = ...
    lick_threshold: int | None = ...
    valve_scale_coefficient: float | None = ...
    valve_nonlinearity_exponent: float | None = ...
    torque_per_adc_unit: float | None = ...
    screens_initially_on: bool | None = ...
    recorded_mesoscope_ttl: bool | None = ...
    system_state_codes: dict[str, int] | None = ...

@dataclass()
class LickTrainingDescriptor(YamlConfig):
    """Stores the task and outcome information specific to lick training sessions that use the Mesoscope-VR system."""

    experimenter: str
    mouse_weight_g: float
    dispensed_water_volume_ml: float
    minimum_reward_delay_s: int
    maximum_reward_delay_s: int
    maximum_water_volume_ml: float
    maximum_training_time_m: int
    maximum_unconsumed_rewards: int = ...
    pause_dispensed_water_volume_ml: float = ...
    experimenter_notes: str = ...
    experimenter_given_water_volume_ml: float = ...
    incomplete: bool = ...

@dataclass()
class RunTrainingDescriptor(YamlConfig):
    """Stores the task and outcome information specific to run training sessions that use the Mesoscope-VR system."""

    experimenter: str
    mouse_weight_g: float
    dispensed_water_volume_ml: float
    final_run_speed_threshold_cm_s: float
    final_run_duration_threshold_s: float
    initial_run_speed_threshold_cm_s: float
    initial_run_duration_threshold_s: float
    increase_threshold_ml: float
    run_speed_increase_step_cm_s: float
    run_duration_increase_step_s: float
    maximum_water_volume_ml: float
    maximum_training_time_m: int
    maximum_unconsumed_rewards: int = ...
    maximum_idle_time_s: float = ...
    pause_dispensed_water_volume_ml: float = ...
    experimenter_notes: str = ...
    experimenter_given_water_volume_ml: float = ...
    incomplete: bool = ...

@dataclass()
class MesoscopeExperimentDescriptor(YamlConfig):
    """Stores the task and outcome information specific to experiment sessions that use the Mesoscope-VR system."""

    experimenter: str
    mouse_weight_g: float
    dispensed_water_volume_ml: float
    maximum_unconsumed_rewards: int = ...
    experimenter_notes: str = ...
    pause_dispensed_water_volume_ml: float = ...
    experimenter_given_water_volume_ml: float = ...
    incomplete: bool = ...

@dataclass()
class ZaberPositions(YamlConfig):
    """Stores Zaber motor positions reused between experiment sessions that use the Mesoscope-VR system.

    The class is specifically designed to store, save, and load the positions of the LickPort and HeadBar motors
    (axes). It is used to both store Zaber motor positions for each session for future analysis and to restore the same
    Zaber motor positions across consecutive runtimes for the same project and animal combination.

    Notes:
        The HeadBar axis (connection) also manages the motor that moves the running wheel along the x-axis. While the
        motor itself is not part of the HeadBar assembly, it is related to positioning the mouse in the VR system. This
        is in contrast to the LickPort group, which is related to positioning the lick tube relative to the mouse.

        All positions are saved using native motor units. All class fields initialize to default placeholders that are
        likely NOT safe to apply to the VR system. Do not apply the positions loaded from the file unless you are
        certain they are safe to use.

        Exercise caution when working with Zaber motors. The motors are powerful enough to damage the surrounding
        equipment and manipulated objects. Do not modify the data stored inside the .yaml file unless you know what you
        are doing.
    """

    headbar_z: int = ...
    headbar_pitch: int = ...
    headbar_roll: int = ...
    lickport_z: int = ...
    lickport_x: int = ...
    lickport_y: int = ...
    wheel_x: int = ...

@dataclass()
class MesoscopePositions(YamlConfig):
    """Stores real and virtual Mesoscope objective positions reused between experiment sessions that use the
    Mesoscope-VR system.

    Primarily, the class is used to help the experimenter to position the Mesoscope at the same position across
    multiple imaging sessions. It stores both the physical (real) position of the objective along the motorized
    X, Y, Z, and Roll axes and the virtual (ScanImage software) tip, tilt, and fastZ focus axes.

    Notes:
        Since the API to read and write these positions automatically is currently not available, this class relies on
        the experimenter manually entering all positions and setting the mesoscope to these positions when necessary.
    """

    mesoscope_x: float = ...
    mesoscope_y: float = ...
    mesoscope_roll: float = ...
    mesoscope_z: float = ...
    mesoscope_fast_z: float = ...
    mesoscope_tip: float = ...
    mesoscope_tilt: float = ...
