"""This module provides classes used to store the training and experiment data acquired by the sl-experiment library.
Some classes from this library store raw data later processed by Sun lab data processing pipelines. Others are used to
restore the data acquisition and runtime management system to the same state across training or experiment sessions for
the same animal.
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

    cue_map: dict[int, float] | None = None
    """MesoscopeExperiment instance property. Stores the dictionary that maps the integer id-codes associated with each 
    wall cue in the Virtual Reality task environment with distances in real-world centimeters animals should run on the 
    wheel to fully traverse the cue region on a linearized track."""
    cm_per_pulse: float | None = None
    """EncoderInterface instance property. Stores the conversion factor used to translate encoder pulses into 
    real-world centimeters."""
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
    activity data with the mesoscope."""
    system_state_codes: dict[str, int] | None = None
    """A MesoscopeVRSystem property. A dictionary that maps integer state-codes used by the Mesoscope-VR system to 
    communicate its states to human-readable state names."""


@dataclass()
class LickTrainingDescriptor(YamlConfig):
    """Stores the task and outcome information specific to lick training sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    dispensed_water_volume_ml: float
    """Stores the total water volume, in milliliters, dispensed during runtime. This excludes the water volume 
    dispensed during the paused (idle) state."""
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
    pause_dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter replaces this field with their 
    notes made during runtime."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    incomplete: bool = False
    """If this field is set to True, the session is marked as 'incomplete' and automatically excluded from all further 
    Sun lab automated processing and analysis."""


@dataclass()
class RunTrainingDescriptor(YamlConfig):
    """Stores the task and outcome information specific to run training sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    dispensed_water_volume_ml: float
    """Stores the total water volume, in milliliters, dispensed during runtime."""
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
    pause_dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter will replace this field with their 
    notes made during runtime."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    incomplete: bool = False
    """If this field is set to True, the session is marked as 'incomplete' and automatically excluded from all further 
    Sun lab automated processing and analysis."""


@dataclass()
class MesoscopeExperimentDescriptor(YamlConfig):
    """Stores the task and outcome information specific to experiment sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    dispensed_water_volume_ml: float
    """Stores the total water volume, in milliliters, dispensed during runtime."""
    maximum_unconsumed_rewards: int = 1
    """Stores the maximum number of consecutive rewards that can be delivered without the animal consuming them. If 
    the animal receives this many rewards without licking (consuming) them, reward delivery is paused until the animal 
    consumes the rewards."""
    experimenter_notes: str = "Replace this with your notes."
    """This field is not set during runtime. It is expected that each experimenter will replace this field with their 
    notes made during runtime."""
    pause_dispensed_water_volume_ml: float = 0.0
    """Stores the total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    incomplete: bool = False
    """If this field is set to True, the session is marked as 'incomplete' and automatically excluded from all further 
    Sun lab automated processing and analysis."""


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

    headbar_z: int = 0
    """The absolute position, in native motor units, of the HeadBar z-axis motor."""
    headbar_pitch: int = 0
    """The absolute position, in native motor units, of the HeadBar pitch-axis motor."""
    headbar_roll: int = 0
    """The absolute position, in native motor units, of the HeadBar roll-axis motor."""
    lickport_z: int = 0
    """The absolute position, in native motor units, of the LickPort z-axis motor."""
    lickport_x: int = 0
    """The absolute position, in native motor units, of the LickPort x-axis motor."""
    lickport_y: int = 0
    """The absolute position, in native motor units, of the LickPort y-axis motor."""
    wheel_x: int = 0
    """The absolute position, in native motor units, of the running wheel platform x-axis motor. Although this motor is
    not itself part of the HeadBar assembly, it is controlled through the HeadBar controller port."""


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

    mesoscope_x: float = 0.0
    """The X-axis position, in centimeters, of the Mesoscope objective used during session runtime."""
    mesoscope_y: float = 0.0
    """The Y-axis position, in centimeters, of the Mesoscope objective used during session runtime."""
    mesoscope_roll: float = 0.0
    """The Roll-axis position, in degrees, of the Mesoscope objective used during session runtime."""
    mesoscope_z: float = 0.0
    """The Z-axis position, in centimeters, of the Mesoscope objective used during session runtime."""
    mesoscope_fast_z: float = 0.0
    """The Fast-Z-axis position, in micrometers, of the Mesoscope objective used during session runtime."""
    mesoscope_tip: float = 0.0
    """The Tilt-axis position, in degrees, of the Mesoscope objective used during session runtime."""
    mesoscope_tilt: float = 0.0
    """The Tip-axis position, in degrees, of the Mesoscope objective used during session runtime."""
