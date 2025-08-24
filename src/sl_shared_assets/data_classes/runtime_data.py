"""This module provides classes used by data acquisition systems to store certain types of acquired data. Note,
different data acquisition session types use different combinations of classes from this module.
"""

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

    cm_per_pulse: float | None = None
    """EncoderInterface instance property. Stores the conversion factor used to translate encoder pulses into 
    real-world centimeters. This conversion factor is fixed for each data acquisition system and does not change 
    between experiments."""
    maximum_break_strength: float | None = None
    """BreakInterface instance property. Stores the breaking torque, in Newton centimeters, applied by the break to 
    the edge of the running wheel when it is engaged at 100% strength."""
    minimum_break_strength: float | None = None
    """BreakInterface instance property. Stores the breaking torque, in Newton centimeters, applied by the break to 
    the edge of the running wheel when it is engaged at 0% strength (completely disengaged)."""
    lick_threshold: int | None = None
    """LickInterface instance property. Determines the threshold, in 12-bit Analog to Digital Converter (ADC) units, 
    above which an interaction value reported by the lick sensor is considered a lick (compared to noise or non-lick 
    touch)."""
    valve_scale_coefficient: float | None = None
    """ValveInterface instance property. To dispense precise water volumes during runtime, ValveInterface uses power 
    law equation applied to valve calibration data to determine how long to keep the valve open. This stores the 
    scale_coefficient of the power law equation that describes the relationship between valve open time and dispensed 
    water volume, derived from calibration data."""
    valve_nonlinearity_exponent: float | None = None
    """ValveInterface instance property. To dispense precise water volumes during runtime, ValveInterface uses power 
    law equation applied to valve calibration data to determine how long to keep the valve open. This stores the 
    nonlinearity_exponent of the power law equation that describes the relationship between valve open time and 
    dispensed water volume, derived from calibration data."""
    torque_per_adc_unit: float | None = None
    """TorqueInterface instance property. Stores the conversion factor used to translate torque values reported by the 
    sensor as 12-bit Analog to Digital Converter (ADC) units, into real-world Newton centimeters (N·cm) of torque that 
    had to be applied to the edge of the running wheel to produce the observed ADC value."""
    screens_initially_on: bool | None = None
    """ScreenInterface instance property. Stores the initial state of the Virtual Reality screens at the beginning of 
    the session runtime."""
    recorded_mesoscope_ttl: bool | None = None
    """TTLInterface instance property. A boolean flag that determines whether the processed session recorded brain 
    activity data with the mesoscope. In that case, attempts to parse the Mesoscope frame scanning TTL pulse data to 
    synchronize Mesoscope data to behavior data."""
    system_state_codes: dict[str, int] | None = None
    """A _MesoscopeVRSystem instance property. A dictionary that maps integer state-codes used by the Mesoscope-VR 
    system to communicate its states (system states) to human-readable state names."""


@dataclass()
class LickTrainingDescriptor(YamlConfig):
    """Stores the task and outcome information specific to lick training sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    minimum_reward_delay_s: int
    """Stores the minimum delay, in seconds, that can separate the delivery of two consecutive water rewards."""
    maximum_reward_delay_s: int
    """Stores the maximum delay, in seconds, that can separate the delivery of two consecutive water rewards."""
    maximum_water_volume_ml: float
    """Stores the maximum volume of water the system is allowed to dispense during training."""
    maximum_training_time_m: int
    """Stores the maximum time, in minutes, the system is allowed to run the training for."""
    maximum_unconsumed_rewards: int = 1
    """Stores the maximum number of consecutive rewards that can be delivered without the animal consuming them. If 
    the animal receives this many rewards without licking (consuming) them, reward delivery is paused until the animal 
    consumes the rewards."""
    dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during runtime. This excludes the water volume 
    dispensed during the paused (idle) state."""
    pause_dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    preferred_session_water_volume_ml: float = 0.0
    """The volume of water, in milliliters, the animal should be receiving during the session runtime if its 
    performance matches experimenter-specified threshold."""
    incomplete: bool = False
    """If this field is set to True, the session is marked as 'incomplete' and automatically excluded from all further 
    Sun lab automated processing and analysis."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter replaces this field with their 
    notes made during runtime."""


@dataclass()
class RunTrainingDescriptor(YamlConfig):
    """Stores the task and outcome information specific to run training sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    final_run_speed_threshold_cm_s: float
    """Stores the final running speed threshold, in centimeters per second, that was active at the end of training."""
    final_run_duration_threshold_s: float
    """Stores the final running duration threshold, in seconds, that was active at the end of training."""
    initial_run_speed_threshold_cm_s: float
    """Stores the initial running speed threshold, in centimeters per second, used during training."""
    initial_run_duration_threshold_s: float
    """Stores the initial running duration threshold, in seconds, used during training."""
    increase_threshold_ml: float
    """Stores the volume of water delivered to the animal, in milliliters, that triggers the increase in the running 
    speed and duration thresholds."""
    run_speed_increase_step_cm_s: float
    """Stores the value, in centimeters per second, used by the system to increment the running speed threshold each 
    time the animal receives 'increase_threshold' volume of water."""
    run_duration_increase_step_s: float
    """Stores the value, in seconds, used by the system to increment the duration threshold each time the animal 
    receives 'increase_threshold' volume of water."""
    maximum_water_volume_ml: float
    """Stores the maximum volume of water the system is allowed to dispense during training."""
    maximum_training_time_m: int
    """Stores the maximum time, in minutes, the system is allowed to run the training for."""
    maximum_unconsumed_rewards: int = 1
    """Stores the maximum number of consecutive rewards that can be delivered without the animal consuming them. If 
    the animal receives this many rewards without licking (consuming) them, reward delivery is paused until the animal 
    consumes the rewards."""
    maximum_idle_time_s: float = 0.0
    """Stores the maximum time, in seconds, the animal can dip below the running speed threshold to still receive the 
    reward. This allows animals that 'run' by taking a series of large steps, briefly dipping below speed threshold at 
    the end of each step, to still get water rewards."""
    dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during runtime. This excludes the water volume 
    dispensed during the paused (idle) state."""
    pause_dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    preferred_session_water_volume_ml: float = 0.0
    """The volume of water, in milliliters, the animal should be receiving during the session runtime if its 
    performance matches experimenter-specified threshold."""
    incomplete: bool = False
    """If this field is set to True, the session is marked as 'incomplete' and automatically excluded from all further 
    Sun lab automated processing and analysis."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter will replace this field with their 
    notes made during runtime."""


@dataclass()
class MesoscopeExperimentDescriptor(YamlConfig):
    """Stores the task and outcome information specific to experiment sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    maximum_unconsumed_rewards: int = 1
    """Stores the maximum number of consecutive rewards that can be delivered without the animal consuming them. If 
    the animal receives this many rewards without licking (consuming) them, reward delivery is paused until the animal 
    consumes the rewards."""
    dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during runtime. This excludes the water volume 
    dispensed during the paused (idle) state."""
    pause_dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    preferred_session_water_volume_ml: float = 0.0
    """The volume of water, in milliliters, the animal should be receiving during the session runtime if its 
    performance matches experimenter-specified threshold."""
    incomplete: bool = False
    """If this field is set to True, the session is marked as 'incomplete' and automatically excluded from all further 
    Sun lab automated processing and analysis."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter will replace this field with their 
    notes made during runtime."""


@dataclass()
class WindowCheckingDescriptor(YamlConfig):
    """Stores the outcome information specific to window checking sessions that use the Mesoscope-VR system.

    Notes:
        Window Checking sessions are different from all other sessions. Unlike other sessions, their purpose is not to
        generate data but rather to assess the suitability of the particular animal to be included in training and
        experiment cohorts. These sessions are automatically excluded from any automated data processing and analysis.
    """

    experimenter: str
    """The ID of the experimenter running the session."""
    surgery_quality: int = 0
    """The quality of the cranial window and surgical intervention on a scale from 0 (non-usable) to 
    3 (high-tier publication grade) inclusive."""
    incomplete: bool = True
    """Window checking sessions are always considered 'incomplete', as they do not contain the full range of 
    information collected as part of a 'standard' behavior training or experiment session."""
    experimenter_notes: str = "Replace this with your notes."
    """The notes on the quality of the cranial window and animal's suitability for the target project."""


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

    headbar_z: int = 0
    """The absolute position, in native motor units, of the HeadBar z-axis motor."""
    headbar_pitch: int = 0
    """The absolute position, in native motor units, of the HeadBar pitch-axis motor."""
    headbar_roll: int = 0
    """The absolute position, in native motor units, of the HeadBar roll-axis motor."""
    lickport_z: int = 0
    """The absolute position, in native motor units, of the LickPort z-axis motor."""
    lickport_y: int = 0
    """The absolute position, in native motor units, of the LickPort y-axis motor."""
    lickport_x: int = 0
    """The absolute position, in native motor units, of the LickPort x-axis motor."""
    wheel_x: int = 0
    """The absolute position, in native motor units, of the running wheel platform x-axis motor."""


@dataclass()
class MesoscopePositions(YamlConfig):
    """Stores the positions of real and virtual Mesoscope objective axes reused between experiment sessions that use the
    Mesoscope-VR system.

    This class is designed to help the experimenter move the Mesoscope to the same imaging plane across imaging
    sessions. It stores both the physical (real) position of the objective along the motorized X, Y, Z, and Roll axes,
    and the virtual (ScanImage software) tip, tilt, and fastZ (virtual zoom) axes.
    """

    mesoscope_x: float = 0.0
    """The Mesoscope objective X-axis position, in micrometers."""
    mesoscope_y: float = 0.0
    """The Mesoscope objective Y-axis position, in micrometers."""
    mesoscope_roll: float = 0.0
    """The Mesoscope objective Roll-axis position, in degrees."""
    mesoscope_z: float = 0.0
    """The Mesoscope objective Z-axis position, in micrometers."""
    mesoscope_fast_z: float = 0.0
    """The ScanImage FastZ (virtual Z-axis) position, in micrometers."""
    mesoscope_tip: float = 0.0
    """The ScanImage Tilt position, in degrees.."""
    mesoscope_tilt: float = 0.0
    """The ScanImage Tip position, in degrees."""
    laser_power_mw: float = 0.0
    """The laser excitation power at the sample, in milliwatts."""
    red_dot_alignment_z: float = 0.0
    """The Mesoscope objective Z-axis position, in micrometers, used for red-dot alignment procedure."""
