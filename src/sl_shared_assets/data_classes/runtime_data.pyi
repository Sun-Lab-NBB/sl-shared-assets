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
        session runtime. This is in contrast to MesoscopeExperimentConfiguration class, which reflects the 'dynamic'
        state of the Mesoscope-VR system during each experiment.

        This class partially overlaps with the MesoscopeSystemConfiguration class, which is also stored in the
        raw_data folder of each session. The primary reason to keep both classes is to ensure that the math (rounding)
        used during runtime matches the math (rounding) used during data processing. MesoscopeSystemConfiguration does
        not do any rounding or otherwise attempt to be repeatable, which is in contrast to hardware modules that read
        and apply those parameters. Reading values from this class guarantees the read value exactly matches the value
        used during runtime.

    Notes:
        All fields in this dataclass initialize to None. During log processing, any log associated with a hardware
        module that provides the data stored in a field will be processed, unless that field is None. Therefore, setting
        any field in this dataclass to None also functions as a flag for whether to parse the log associated with the
        module that provides this field's information.

        This class is automatically configured by _MesoscopeVRSystem class from the sl-experiment library to facilitate
        proper log parsing.
    """

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
class WindowCheckingDescriptor(YamlConfig):
    """Stores the outcome information specific to window checking sessions that use the Mesoscope-VR system.

    Notes:
        Window Checking sessions are different from all other sessions. Unlike other sessions, their purpose is not to
        generate data but rather to assess the suitability of the particular animal to be included in training and
        experiment cohorts. These sessions are automatically excluded from any automated data processing and analysis.
    """

    experimenter: str
    experimenter_notes: str = ...
    surgery_quality: int = ...
    incomplete: bool = ...

@dataclass()
class ZaberPositions(YamlConfig):
    """Stores Zaber motor positions reused between experiment sessions that use the Mesoscope-VR system.

    The class is specifically designed to store, save, and load the positions of the LickPort, HeadBar, and Wheel motors
    (axes). It is used to both store Zaber motor positions for each session for future analysis and to restore the
    Zaber motors to the same positions across consecutive runtimes for the same project and animal combination.

    Notes:
        By default, the class initializes all fields to 0, which is the position of the home sensor for each motor. The
        class assumes that the motor groups are assembled and arranged in a way that ensures all motors can safely move
        to the home sensor positions from any runtime configuration.
    """

    headbar_z: int = ...
    headbar_pitch: int = ...
    headbar_roll: int = ...
    lickport_z: int = ...
    lickport_y: int = ...
    lickport_x: int = ...
    wheel_x: int = ...

@dataclass()
class MesoscopePositions(YamlConfig):
    """Stores the positions of real and virtual Mesoscope objective axes reused between experiment sessions that use the
    Mesoscope-VR system.

    This class is designed to help the experimenter move the Mesoscope to the same imaging plane across imaging
    sessions. It stores both the physical (real) position of the objective along the motorized X, Y, Z, and Roll axes,
    and the virtual (ScanImage software) tip, tilt, and fastZ (virtual zoom) axes.
    """

    mesoscope_x: float = ...
    mesoscope_y: float = ...
    mesoscope_roll: float = ...
    mesoscope_z: float = ...
    mesoscope_fast_z: float = ...
    mesoscope_tip: float = ...
    mesoscope_tilt: float = ...
    laser_power_mw: float = ...
    red_dot_alignment_z: float = ...
