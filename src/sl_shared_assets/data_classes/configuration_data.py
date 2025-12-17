"""This module provides the assets used to configure data acquisition and processing runtimes in the Sun lab."""

from copy import deepcopy
from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass

import appdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

# Constants for validation
_UINT8_MAX = 255
"""Maximum value for uint8 cue codes."""
_PROBABILITY_SUM_TOLERANCE = 0.001
"""Tolerance for validating probability sums to 1.0."""


class AcquisitionSystems(StrEnum):
    """Defines the data acquisition systems currently used in the Sun lab."""

    MESOSCOPE_VR = "mesoscope"
    """This system is built around the 2-Photon Random Access Mesoscope (2P-RAM) and relies on Virtual Reality (VR)
    environments running in Unity game engine to conduct experiments."""


@dataclass()
class Cue:
    """Defines a single visual cue used in the experiment task's Virtual Reality (VR) environment.

    Notes:
        Each cue has a unique name (used in the Unity segment (prefab) definitions) and a unique uint8 code (used during
        MQTT communication and analysis). Cues are not loaded as individual prefabs - they are baked into segment
        prefabs.
    """

    name: str
    """The visual identifier for the cue (e.g., 'A', 'B', 'Gray'). Used to reference the cue in segment definitions."""
    code: int
    """The unique uint8 code (0-255) that identifies the cue during MQTT communication and data analysis."""
    length_cm: float
    """The length of the cue in centimeters."""

    def __post_init__(self) -> None:
        """Validates cue definition parameters."""
        if not 0 <= self.code <= _UINT8_MAX:
            message = f"Cue code must be a uint8 value (0-255), got {self.code} for cue '{self.name}'."
            console.error(message=message, error=ValueError)
        if self.length_cm <= 0:
            message = f"Cue length must be positive, got {self.length_cm} cm for cue '{self.name}'."
            console.error(message=message, error=ValueError)


@dataclass()
class Segment:
    """Defines a visual segment (sequence of cues) used in the experiment task's Virtual Reality (VR) environment.

    Notes:
        Segments are the building blocks of the infinite corridor, each containing a sequence of visual cues
        and optional transition probabilities for segment-to-segment transitions.
    """

    name: str
    """The unique identifier of the segment's Unity prefab file."""
    cue_sequence: list[str]
    """The ordered sequence of cue names that comprise this segment."""
    transition_probabilities: list[float] | None = None
    """Optional transition probabilities to other segments that make up the task's corridor environment. If provided,
    must sum to 1.0."""

    def __post_init__(self) -> None:
        """Validates segment definition parameters."""
        if not self.cue_sequence:
            message = f"Segment '{self.name}' must have at least one cue in its cue_sequence."
            console.error(message=message, error=ValueError)

        if self.transition_probabilities:
            prob_sum = sum(self.transition_probabilities)
            if abs(prob_sum - 1.0) > _PROBABILITY_SUM_TOLERANCE:
                message = f"Segment '{self.name}' transition probabilities sum to {prob_sum}, but must sum to 1.0."
                console.error(message=message, error=ValueError)


@dataclass()
class VREnvironment:
    """Defines the Unity VR corridor system configuration.

    Notes:
        This class is primarily used by Unity to configure the task environment. Python parses these values
        from the YAML configuration file but does not use them at runtime.
    """

    corridor_spacing_cm: float = 20.0
    """The horizontal spacing between corridor instances in centimeters."""
    segments_per_corridor: int = 3
    """The number of segments visible in each corridor instance (corridor depth)."""
    padding_prefab_name: str = "Padding"
    """The name of the Unity prefab used for corridor padding."""
    cm_per_unity_unit: float = 10.0
    """The conversion factor from centimeters to Unity units."""


@dataclass()
class MesoscopeExperimentState:
    """Defines the structure and runtime parameters of an experiment state (phase)."""

    experiment_state_code: int
    """The unique identifier code of the experiment state."""
    system_state_code: int
    """The data acquisition system's state (configuration snapshot) code associated with the experiment state."""
    state_duration_s: float
    """The time, in seconds, to maintain the experiment state while executing the experiment."""
    supports_trials: bool = True
    """Determines whether trials are executed during this experiment state. When False, no trial-related processing
    occurs during this phase."""
    # Reinforcing (water reward) trial guidance parameters
    reinforcing_initial_guided_trials: int = 0
    """The number of reinforcing trials after the onset of the experiment state that use the guidance mode."""
    reinforcing_recovery_failed_threshold: int = 0
    """The number of sequentially failed reinforcing trials after which to enable the recovery guidance mode."""
    reinforcing_recovery_guided_trials: int = 0
    """The number of guided reinforcing trials to use in the recovery guidance mode."""
    # Aversive (gas puff) trial guidance parameters
    aversive_initial_guided_trials: int = 0
    """The number of aversive trials after the onset of the experiment state that use the guidance mode."""
    aversive_recovery_failed_threshold: int = 0
    """The number of sequentially failed aversive trials after which to enable the recovery guidance mode."""
    aversive_recovery_guided_trials: int = 0
    """The number of guided aversive trials to use in the recovery guidance mode."""


@dataclass()
class _MesoscopeBaseTrial:
    """Defines the shared structure and task parameters common to all supported experiment trial types.

    Notes:
        The trigger mode and guidance behavior are determined by the trial type:
        - WaterRewardTrial: Uses 'lick' trigger mode; guidance delivers stimulus on collision.
        - GasPuffTrial: Uses 'occupancy' trigger mode; guidance emits OccupancyFailed for movement blocking.
    """

    segment_name: str
    """The name of the Unity Segment this trial is based on."""
    stimulus_trigger_zone_start_cm: float
    """The position of the trial stimulus trigger zone starting boundary, in centimeters."""
    stimulus_trigger_zone_end_cm: float
    """The position of the trial stimulus trigger zone ending boundary, in centimeters."""
    stimulus_location_cm: float
    """The location of the invisible boundary (wall) with which the animal must collide to elicit the stimulus."""
    show_stimulus_collision_boundary: bool = False
    """Determines whether the stimulus collision boundary is visible to the animal during this trial type. When True,
    the boundary marker is displayed in the Virtual Reality environment at the stimulus location."""

    # Derived fields - populated by MesoscopeExperimentConfiguration.__post_init__
    cue_sequence: list[int] = field(default_factory=list)
    """The sequence of segment wall cues identifiers experienced by the animal when participating in this type of
    trials."""
    trial_length_cm: float = 0.0
    """The total length of the trial environment in centimeters."""

    def validate_zones(self) -> None:
        """Validates stimulus zone positions.

        Notes:
            This method must be called after trial_length_cm is populated by MesoscopeExperimentConfiguration.
        """
        if self.trial_length_cm <= 0:
            message = "Cannot validate zones: trial_length_cm must be populated first."
            console.error(message=message, error=ValueError)

        if self.stimulus_trigger_zone_end_cm < self.stimulus_trigger_zone_start_cm:
            message = (
                f"The 'stimulus_trigger_zone_end_cm' ({self.stimulus_trigger_zone_end_cm}) must be greater than or "
                f"equal to 'stimulus_trigger_zone_start_cm' ({self.stimulus_trigger_zone_start_cm})."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= self.stimulus_trigger_zone_start_cm <= self.trial_length_cm:
            message = (
                f"The 'stimulus_trigger_zone_start_cm' ({self.stimulus_trigger_zone_start_cm}) must be within the "
                f"trial length (0 to {self.trial_length_cm} cm)."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= self.stimulus_trigger_zone_end_cm <= self.trial_length_cm:
            message = (
                f"The 'stimulus_trigger_zone_end_cm' ({self.stimulus_trigger_zone_end_cm}) must be within the "
                f"trial length (0 to {self.trial_length_cm} cm)."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= self.stimulus_location_cm <= self.trial_length_cm:
            message = (
                f"The 'stimulus_location_cm' ({self.stimulus_location_cm}) must be within the "
                f"trial length (0 to {self.trial_length_cm} cm)."
            )
            console.error(message=message, error=ValueError)

        if self.stimulus_location_cm < self.stimulus_trigger_zone_start_cm:
            message = (
                f"The 'stimulus_location_cm' ({self.stimulus_location_cm}) cannot precede the "
                f"'stimulus_trigger_zone_start_cm' ({self.stimulus_trigger_zone_start_cm}). The stimulus location must "
                f"be at or after the start of the trigger zone."
            )
            console.error(message=message, error=ValueError)


@dataclass()
class WaterRewardTrial(_MesoscopeBaseTrial):
    """Defines a trial that delivers water rewards (reinforcing stimuli) when the animal licks in the trigger zone.

    Notes:
        Trigger mode: The animal must lick while inside the stimulus trigger zone to receive the water reward.
        Guidance mode: The animal receives the reward upon colliding with the stimulus boundary (no lick required).
    """

    reward_size_ul: float = 5.0
    """The volume of water, in microliters, to deliver when the animal successfully completes the trial."""
    reward_tone_duration_ms: int = 300
    """The duration, in milliseconds, to sound the auditory tone when delivering the water reward."""


@dataclass()
class GasPuffTrial(_MesoscopeBaseTrial):
    """Defines a trial that delivers N2 gas puffs (aversive stimuli) when the animal fails to meet occupancy duration.

    Notes:
        Trigger mode: The animal must occupy the stimulus trigger zone for the specified duration to disarm the
        stimulus boundary and avoid the gas puff. If the animal exits the zone early or collides with the boundary
        before meeting the occupancy threshold, the gas puff is delivered.
        Guidance mode: When the animal exits the zone early, an OccupancyFailed message is emitted, allowing
        sl-experiment to block movement and prevent the animal from reaching the armed boundary.
    """

    puff_duration_ms: int = 100
    """The duration, in milliseconds, for which to deliver the N2 gas puff when the animal fails the trial."""
    occupancy_duration_ms: int = 1000
    """The time, in milliseconds, the animal must occupy the trigger zone to disarm the stimulus boundary and avoid
    the gas puff."""


# noinspection PyArgumentList
@dataclass()
class MesoscopeExperimentConfiguration(YamlConfig):
    """Defines an experiment session that uses the Mesoscope_VR data acquisition system.

    This is the unified configuration that serves both the data acquisition system (sl-experiment),
    the analysis pipeline (sl-forgery), and the Unity VR environment (sl-unity-tasks).
    """

    # Virtual Reality building block configuration
    cues: list[Cue]
    """Defines the Virtual Reality environment wall cues used in the experiment."""
    segments: list[Segment]
    """Defines the Virtual Reality environment segments (sequences of wall cues) for the Unity corridor system."""

    # Task configuration
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial]
    """Defines experiment's structure by specifying the types of trials used by the phases (states) of the
    experiment."""
    experiment_states: dict[str, MesoscopeExperimentState]
    """Defines the experiment's flow by specifying the sequence of experiment and data acquisition system states
    executed during runtime."""

    # VR environment configuration
    vr_environment: VREnvironment
    """Defines the Virtual Reality corridor used during the experiment."""
    unity_scene_name: str
    """The name of the Virtual Reality task (Unity Scene) used during the experiment."""
    cue_offset_cm: float = 0.0
    """Specifies the offset of the animal's starting position relative to the Virtual Reality (VR) environment's cue
    sequence origin, in centimeters."""

    @property
    def _cue_by_name(self) -> dict[str, Cue]:
        """Returns the mapping of cue names to their Cue class instances for all VR cues used in the experiment."""
        return {cue.name: cue for cue in self.cues}

    @property
    def _cue_name_to_code(self) -> dict[str, int]:
        """Returns the mapping of cue names to their unique identifier codes for all VR cues used in the experiment."""
        return {cue.name: cue.code for cue in self.cues}

    @property
    def _segment_by_name(self) -> dict[str, Segment]:
        """Returns the mapping of segment names to their Segment class instances for all VR segments used in the
        experiment.
        """
        return {seg.name: seg for seg in self.segments}

    def _get_segment_length_cm(self, segment_name: str) -> float:
        """Returns the total length of the VR segment in centimeters."""
        segment = self._segment_by_name[segment_name]
        cue_map = self._cue_by_name
        return sum(cue_map[cue_name].length_cm for cue_name in segment.cue_sequence)

    def _get_segment_cue_codes(self, segment_name: str) -> list[int]:
        """Returns the sequence of cue codes for the specified segment's cue sequence."""
        segment = self._segment_by_name[segment_name]
        return [self._cue_name_to_code[name] for name in segment.cue_sequence]

    def __post_init__(self) -> None:
        """Validates experiment configuration and populates derived trial fields."""
        # Ensures cue codes are unique
        codes = [cue.code for cue in self.cues]
        if len(codes) != len(set(codes)):
            duplicate_codes = [c for c in codes if codes.count(c) > 1]
            message = (
                f"Duplicate cue codes found: {set(duplicate_codes)} in the {self.vr_environment} VR environment "
                f"definition. Each cue must use a unique integer code."
            )
            console.error(message=message, error=ValueError)

        # Ensures cue names are unique
        names = [cue.name for cue in self.cues]
        if len(names) != len(set(names)):
            duplicate_names = [n for n in names if names.count(n) > 1]
            message = (
                f"Duplicate cue names found: {set(duplicate_names)} in the {self.vr_environment} VR environment "
                f"definition. Each cue must use a unique name."
            )
            console.error(message=message, error=ValueError)

        # Ensures segment cue sequences reference valid cues
        cue_names = {cue.name for cue in self.cues}
        for seg in self.segments:
            for cue_name in seg.cue_sequence:
                if cue_name not in cue_names:
                    message = (
                        f"Segment '{seg.name}'  references unknown cue '{cue_name}'. "
                        f"Available cues: {', '.join(sorted(cue_names))}."
                    )
                    console.error(message=message, error=ValueError)

        # Populates the derived trial fields and validates them
        segment_names = {seg.name for seg in self.segments}
        for trial_name, trial in self.trial_structures.items():
            # Validates segment reference
            if trial.segment_name not in segment_names:
                message = (
                    f"Trial '{trial_name}' references unknown segment '{trial.segment_name}'. "
                    f"Available segments: {', '.join(sorted(segment_names))}."
                )
                console.error(message=message, error=ValueError)

            # Populates cue_sequence from segment
            trial.cue_sequence = self._get_segment_cue_codes(trial.segment_name)

            # Populates trial_length_cm from segment
            trial.trial_length_cm = self._get_segment_length_cm(trial.segment_name)

            # Validates zone positions with populated trial_length_cm
            trial.validate_zones()


@dataclass()
class MesoscopeFileSystem:
    """Stores the filesystem configuration of the Mesoscope-VR data acquisition system."""

    root_directory: Path = Path()
    """The absolute path to the directory where all projects are stored on the main data acquisition system PC."""
    server_directory: Path = Path()
    """The absolute path to the local-filesystem-mounted directory where all projects are stored on the remote compute 
    server."""
    nas_directory: Path = Path()
    """The absolute path to the local-filesystem-mounted directory where all projects are stored on the NAS backup 
    storage volume."""
    mesoscope_directory: Path = Path()
    """The absolute path to the local-filesystem-mounted directory where all Mesoscope-acquired data is aggregated 
    during acquisition by the PC that manages the Mesoscope during runtime."""


@dataclass()
class MesoscopeGoogleSheets:
    """Stores the identifiers for the Google Sheets used by the Mesoscope-VR data acquisition system."""

    surgery_sheet_id: str = ""
    """The identifier of the Google Sheet that stores information about surgical interventions performed on the animals 
    that participate in data acquisition sessions."""
    water_log_sheet_id: str = ""
    """The identifier of the Google Sheet that stores information about water restriction and handling for all 
    animals that participate in data acquisition sessions."""


@dataclass()
class MesoscopeCameras:
    """Stores the video camera configuration of the Mesoscope-VR data acquisition system."""

    face_camera_index: int = 0
    """The index of the face camera in the list of all available Harvester-managed cameras."""
    body_camera_index: int = 1
    """The index of the body camera in the list of all available Harvester-managed cameras."""
    face_camera_quantization: int = 20
    """The quantization parameter used by the face camera to encode acquired frames as video files."""
    face_camera_preset: int = 7
    """The encoding speed preset used by the face camera to encode acquired frames as video files. Must be one of the 
    valid members of the EncoderSpeedPresets enumeration from the ataraxis-video-system library."""
    body_camera_quantization: int = 20
    """The quantization parameter used by the body camera to encode acquired frames as video files."""
    body_camera_preset: int = 7
    """The encoding speed preset used by the body camera to encode acquired frames as video files. Must be one of the 
    valid members of the EncoderSpeedPresets enumeration from the ataraxis-video-system library."""


@dataclass()
class MesoscopeMicroControllers:
    """Stores the microcontroller configuration of the Mesoscope-VR data acquisition system."""

    actor_port: str = "/dev/ttyACM0"
    """The USB port used by the Actor Microcontroller."""
    sensor_port: str = "/dev/ttyACM1"
    """The USB port used by the Sensor Microcontroller."""
    encoder_port: str = "/dev/ttyACM2"
    """The USB port used by the Encoder Microcontroller."""
    keepalive_interval_ms: int = 500
    """The interval, in milliseconds, at which the microcontrollers are expected to receive and send the keepalive 
    messages used to ensure that all controllers function as expected during runtime."""
    minimum_brake_strength_g_cm: float = 43.2047
    """The torque applied by the running wheel brake at the minimum operational voltage, in gram centimeter."""
    maximum_brake_strength_g_cm: float = 1152.1246
    """The torque applied by the running wheel brake at the maximum operational voltage, in gram centimeter."""
    wheel_diameter_cm: float = 15.0333
    """The diameter of the running wheel, in centimeters."""
    lick_threshold_adc: int = 600
    """The threshold voltage, in raw analog units recorded by a 3.3 Volt 12-bit Analog-to-Digital-Converter (ADC), 
    interpreted as the animal's tongue contacting the lick sensor."""
    lick_signal_threshold_adc: int = 300
    """The minimum voltage, in raw analog units recorded by a 3.3 Volt 12-bit Analog-to-Digital-Converter (ADC), 
    reported to the PC as a non-zero value. Voltages below this level are interpreted as 'no-lick' noise and are 
    pulled to 0."""
    lick_delta_threshold_adc: int = 300
    """The minimum absolute difference between two consecutive lick sensor readouts, in raw analog units recorded by 
    a 3.3 Volt 12-bit Analog-to-Digital-Converter (ADC), for the change to be reported to the PC."""
    lick_averaging_pool_size: int = 2
    """The number of lick sensor readouts to average together to produce the final lick sensor readout value."""
    torque_baseline_voltage_adc: int = 2048
    """The voltage level, in raw analog units measured by a 3.3 Volt 12-bit Analog-to-Digital-Converter (ADC) after the 
    AD620 amplifier, that corresponds to no torque (0) readout."""
    torque_maximum_voltage_adc: int = 3443
    """The voltage level, in raw analog units measured by a 3.3 Volt 12-bit Analog-to-Digital-Converter (ADC) 
    after the AD620 amplifier, that corresponds to the absolute maximum torque detectable by the sensor."""
    torque_sensor_capacity_g_cm: float = 720.0779
    """The maximum torque detectable by the sensor, in grams centimeter (g cm)."""
    torque_report_cw: bool = True
    """Determines whether the torque sensor should report torques in the Clockwise (CW) direction."""
    torque_report_ccw: bool = True
    """Determines whether the sensor should report torque in the Counter-Clockwise (CCW) direction."""
    torque_signal_threshold_adc: int = 150
    """The minimum voltage, in raw analog units recorded by a 3.3 Volt 12-bit Analog-to-Digital-Converter (ADC), 
    reported to the PC as a non-zero value. Voltages below this level are interpreted as noise and are pulled to 0."""
    torque_delta_threshold_adc: int = 100
    """The minimum absolute difference between two consecutive torque sensor readouts, in raw analog units recorded by 
    a 3.3 Volt 12-bit Analog-to-Digital-Converter (ADC), for the change to be reported to the PC."""
    torque_averaging_pool_size: int = 4
    """The number of torque sensor readouts to average together to produce the final torque sensor readout value."""
    wheel_encoder_ppr: int = 8192
    """The resolution of the wheel's quadrature encoder, in Pulses Per Revolution (PPR)."""
    wheel_encoder_report_cw: bool = False
    """Determines whether the encoder should report rotation in the Clockwise (CW) direction."""
    wheel_encoder_report_ccw: bool = True
    """Determines whether the encoder should report rotation in the CounterClockwise (CCW) direction."""
    wheel_encoder_delta_threshold_pulse: int = 15
    """The minimum absolute difference between two consecutive encoder readouts, in encoder pulse counts, for the 
    change to be reported to the PC."""
    wheel_encoder_polling_delay_us: int = 500
    """The delay, in microseconds, between consecutive encoder state readouts."""
    cm_per_unity_unit: float = 10.0
    """The length of each Virtual Reality (VR) environment's distance 'unit' (Unity unit) in real-world centimeters."""
    screen_trigger_pulse_duration_ms: int = 500
    """The duration, in milliseconds, of the TTL pulse used to toggle the VR screen power state."""
    sensor_polling_delay_ms: int = 1
    """The delay, in milliseconds, between any two successive readouts of any sensor other than the encoder."""
    mesoscope_frame_averaging_pool_size = 0
    """The number of digital pin readouts to average together when determining the current logic level of the incoming 
    TTL signal sent by the mesoscope at the onset of each frame's acquisition."""
    valve_calibration_data: dict[int | float, int | float] | tuple[tuple[int | float, int | float], ...] = (
        (15000, 1.10),
        (30000, 3.0),
        (45000, 6.25),
        (60000, 10.90),
    )
    """Maps water delivery solenoid valve open times, in microseconds, to the dispensed volumes of water, in 
    microliters."""


@dataclass()
class MesoscopeExternalAssets:
    """Stores the third-party asset configuration of the Mesoscope-VR data acquisition system."""

    headbar_port: str = "/dev/ttyUSB0"
    """The USB port used by the HeadBar Zaber motor controllers."""
    lickport_port: str = "/dev/ttyUSB1"
    """The USB port used by the LickPort Zaber motor controllers."""
    wheel_port: str = "/dev/ttyUSB2"
    """The USB port used by the Wheel Zaber motor controllers."""
    unity_ip: str = "127.0.0.1"
    """The IP address of the MQTT broker used to communicate with the Unity game engine."""
    unity_port: int = 1883
    """The port number of the MQTT broker used to communicate with the Unity game engine."""


@dataclass()
class MesoscopeSystemConfiguration(YamlConfig):
    """Defines the hardware and software asset configuration for the Mesoscope-VR data acquisition system."""

    name: str = str(AcquisitionSystems.MESOSCOPE_VR)
    """The descriptive name of the data acquisition system."""
    filesystem: MesoscopeFileSystem = field(default_factory=MesoscopeFileSystem)
    """Stores the filesystem configuration."""
    sheets: MesoscopeGoogleSheets = field(default_factory=MesoscopeGoogleSheets)
    """Stores the identifiers and access credentials for the Google Sheets."""
    cameras: MesoscopeCameras = field(default_factory=MesoscopeCameras)
    """Stores the video cameras configuration."""
    microcontrollers: MesoscopeMicroControllers = field(default_factory=MesoscopeMicroControllers)
    """Stores the microcontrollers configuration."""
    assets: MesoscopeExternalAssets = field(default_factory=MesoscopeExternalAssets)
    """Stores the third-party hardware and firmware assets configuration."""

    def __post_init__(self) -> None:
        """Ensures that all instance assets are stored as the expected types."""
        # Restores Path objects from strings.
        self.filesystem.root_directory = Path(self.filesystem.root_directory)
        self.filesystem.server_directory = Path(self.filesystem.server_directory)
        self.filesystem.nas_directory = Path(self.filesystem.nas_directory)
        self.filesystem.mesoscope_directory = Path(self.filesystem.mesoscope_directory)

        # Converts valve_calibration data from a dictionary to a tuple of tuples.
        if not isinstance(self.microcontrollers.valve_calibration_data, tuple):
            self.microcontrollers.valve_calibration_data = tuple(
                (k, v) for k, v in self.microcontrollers.valve_calibration_data.items()
            )

        # Verifies the contents of the valve calibration data loaded from the config file.
        valve_calibration_data = self.microcontrollers.valve_calibration_data
        element_count = 2
        if not all(
            isinstance(item, tuple)
            and len(item) == element_count
            and isinstance(item[0], (int | float))
            and isinstance(item[1], (int | float))
            for item in valve_calibration_data
        ):
            message = (
                f"Unable to initialize the MesoscopeSystemConfiguration class. Expected each item under the "
                f"'valve_calibration_data' field of the Mesoscope-VR acquisition system configuration .yaml file to be "
                f"a tuple of two integer or float values, but instead encountered {valve_calibration_data} with at "
                f"least one incompatible element."
            )
            console.error(message=message, error=TypeError)

    def save(self, path: Path) -> None:
        """Saves the instance's data to disk as a .YAML file.

        Args:
            path: The path to the .YAML file to save the data to.
        """
        # Copies instance data to prevent it from being modified by reference when executing the steps below
        original = deepcopy(self)

        # Converts all Path objects to strings before dumping the data, as .YAML encoder does not recognize Path objects
        original.filesystem.root_directory = str(original.filesystem.root_directory)  # type: ignore[assignment]
        original.filesystem.server_directory = str(original.filesystem.server_directory)  # type: ignore[assignment]
        original.filesystem.nas_directory = str(original.filesystem.nas_directory)  # type: ignore[assignment]
        original.filesystem.mesoscope_directory = str(  # type: ignore[assignment]
            original.filesystem.mesoscope_directory
        )

        # Converts valve calibration data into dictionary format
        if isinstance(original.microcontrollers.valve_calibration_data, tuple):
            original.microcontrollers.valve_calibration_data = dict(original.microcontrollers.valve_calibration_data)

        # Saves the data to the YAML file
        original.to_yaml(file_path=path)


@dataclass()
class ServerConfiguration(YamlConfig):
    """Defines the access credentials and the filesystem layout of the Sun lab's remote compute server."""

    username: str = ""
    """The username to use for server authentication."""
    password: str = ""
    """The password to use for server authentication."""
    host: str = "cbsuwsun.biohpc.cornell.edu"
    """The hostname or IP address of the server to connect to."""
    storage_root: str = "/local/storage"
    """The path to the server's storage (slow) HDD RAID volume."""
    working_root: str = "/local/workdir"
    """The path to the server's working (fast) NVME RAID volume."""
    shared_directory_name: str = "sun_data"
    """The name of the shared directory that stores Sun lab's project data on both server volumes."""
    shared_storage_root: str = field(init=False, default_factory=lambda: "/local/storage/sun_data")
    """The path to the root Sun lab's shared directory on the storage server's volume."""
    shared_working_root: str = field(init=False, default_factory=lambda: "/local/workdir/sun_data")
    """The path to the root Sun lab's shared directory on the working server's volume."""
    user_data_root: str = field(init=False, default_factory=lambda: "/local/storage/YourNetID")
    """The path to the root user's directory on the storage server's volume."""
    user_working_root: str = field(init=False, default_factory=lambda: "/local/workdir/YourNetID")
    """The path to the root user's directory on the working server's volume."""

    def __post_init__(self) -> None:
        """Resolves all server-side directory paths."""
        # Stores directory paths as strings as this is used by the paramiko bindings in the Server class from the
        # sl-forgery library.
        self.shared_storage_root = str(Path(self.storage_root).joinpath(self.shared_directory_name))
        self.shared_working_root = str(Path(self.working_root).joinpath(self.shared_directory_name))
        self.user_data_root = str(Path(self.storage_root).joinpath(f"{self.username}"))
        self.user_working_root = str(Path(self.working_root).joinpath(f"{self.username}"))


def set_working_directory(path: Path) -> None:
    """Sets the specified directory as the Sun lab's working directory for the local machine (PC).

    Notes:
        This function caches the path to the working directory in the user's data directory.

        If the input path does not point to an existing directory, the function creates the requested directory.

    Args:
        path: The path to the directory to set as the local Sun lab's working directory.
    """
    # Resolves the path to the static .txt file used to store the path to the system configuration file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("working_directory_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Ensures that the input path's directory exists
    ensure_directory_exists(path)

    # Also ensures that the working directory contains the 'configuration' subdirectory.
    ensure_directory_exists(path.joinpath("configuration"))

    # Replaces the contents of the working_directory_path.txt file with the provided path
    with path_file.open("w") as f:
        f.write(str(path))

    console.echo(message=f"Sun lab's working directory set to: {path}.", level=LogLevel.SUCCESS)


def get_working_directory() -> Path:
    """Resolves and returns the path to the local Sun lab's working directory.

    Returns:
        The path to the local working directory.

    Raises:
        FileNotFoundError: If the local working directory has not been configured for the host-machine.
    """
    # Uses appdirs to locate the user data directory and resolve the path to the configuration file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("working_directory_path.txt")

    # If the cache file or the Sun lab's data directory does not exist, aborts with an error
    if not path_file.exists():
        message = (
            "Unable to resolve the path to the local Sun lab's working directory, as it has not been set. "
            "Set the local working directory by using the 'sl-configure directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Loads the path to the local working directory
    with path_file.open() as f:
        working_directory = Path(f.read().strip())

    # If the configuration file does not exist, also aborts with an error
    if not working_directory.exists():
        message = (
            "Unable to resolve the path to the local Sun lab's working directory, as the currently configured "
            "directory does not exist at the expected path. Set a new working directory by using the 'sl-configure "
            "directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Returns the path to the working directory
    return working_directory


def create_system_configuration_file(system: AcquisitionSystems | str) -> None:
    """Creates the .YAML configuration file for the requested Sun lab's data acquisition system and configures the local
    machine (PC) to use this file for all future acquisition-system-related calls.

    Notes:
        This function creates the configuration file inside the local Sun lab's working directory.

    Args:
        system: The name (type) of the data acquisition system for which to create the configuration file.

    Raises:
        ValueError: If the input acquisition system name (type) is not recognized.
    """
    # Resolves the path to the local Sun lab's working directory.
    directory = get_working_directory()
    directory = directory.joinpath("configuration")  # Navigates to the 'configuration' subdirectory

    # Removes any existing system configuration files to ensure only one system configuration exists on each configured
    # machine
    existing_configs = tuple(directory.glob("*_system_configuration.yaml"))
    for config_file in existing_configs:
        console.echo(f"Removing the existing configuration file {config_file.name}...")
        config_file.unlink()

    if system == AcquisitionSystems.MESOSCOPE_VR:
        # Creates the precursor configuration file for the mesoscope-vr system
        configuration = MesoscopeSystemConfiguration()
        configuration_path = directory.joinpath(f"{system}_system_configuration.yaml")
        configuration.save(path=configuration_path)

        # Prompts the user to finish configuring the system by editing the parameters inside the configuration file
        message = (
            f"Mesoscope-VR data acquisition system configuration file: Saved to {configuration_path}. Edit the "
            f"default parameters inside the configuration file to finish configuring the system."
        )
        console.echo(message=message, level=LogLevel.SUCCESS)
        input("Enter anything to continue...")

    # If the input acquisition system is not recognized, raises a ValueError
    else:
        systems = tuple(AcquisitionSystems)
        message = (
            f"Unable to generate the system configuration file for the acquisition system '{system}'. The specified "
            f"acquisition system is not supported (not recognized). Currently, only the following acquisition systems "
            f"are supported: {', '.join(systems)}."
        )
        console.error(message=message, error=ValueError)


def get_system_configuration_data() -> MesoscopeSystemConfiguration:
    """Resolves the path to the local data acquisition system configuration file and loads the configuration data as
    a SystemConfiguration instance.

    Returns:
        The initialized SystemConfiguration class instance that stores the loaded configuration parameters.

    Raises:
        FileNotFoundError: If the local machine does not have a valid data acquisition system configuration file.
    """
    # Maps supported file names to configuration classes.
    _supported_configuration_files = {
        f"{AcquisitionSystems.MESOSCOPE_VR}_system_configuration.yaml": MesoscopeSystemConfiguration,
    }

    # Resolves the path to the local Sun lab's working directory.
    directory = get_working_directory()
    directory = directory.joinpath("configuration")  # Navigates to the 'configuration' subdirectory

    # Finds all configuration files stored in the local working directory.
    config_files = tuple(directory.glob("*_system_configuration.yaml"))

    # Ensures exactly one configuration file exists in the working directory
    if len(config_files) != 1:
        file_names = [f.name for f in config_files]
        message = (
            f"Expected a single data acquisition system configuration file to be found inside the local Sun lab's "
            f"working directory ({directory}), but found {len(config_files)} files ({', '.join(file_names)}). Call the "
            f"'sl-configure system' CLI command to reconfigure the host-machine to only contain a single data "
            f"acquisition system configuration file."
        )
        console.error(message=message, error=FileNotFoundError)
        # Fallback to appease mypy, should not be reachable
        raise FileNotFoundError(message)  # pragma: no cover

    # Gets the single configuration file
    configuration_file = config_files[0]
    file_name = configuration_file.name

    # Ensures that the file name is supported
    if file_name not in _supported_configuration_files:
        message = (
            f"The data acquisition system configuration file '{file_name}' stored in the local Sun lab's working "
            f"directory is not recognized. Call the 'sl-configure system' CLI command to reconfigure the host-machine "
            f"to use a supported configuration file."
        )
        console.error(message=message, error=ValueError)
        # Fallback to appease mypy, should not be reachable
        raise ValueError(message)  # pragma: no cover

    # Loads and return the configuration data
    configuration_class = _supported_configuration_files[file_name]
    return configuration_class.from_yaml(file_path=configuration_file)


def set_google_credentials_path(path: Path) -> None:
    """Configures the local machine (PC) to use the provided Google Sheets service account credentials .JSON file for
    all future interactions with the Google's API.

    Notes:
        This function caches the path to the Google Sheets credentials file in the user's data directory.

    Args:
        path: The path to the .JSON file containing the Google Sheets service account credentials.

    Raises:
        FileNotFoundError: If the specified .JSON file does not exist at the provided path.
    """
    # Verifies that the specified credentials file exists
    if not path.exists():
        message = (
            f"Unable to set the Google Sheets credentials path. The specified file ({path}) does not exist. "
            f"Ensure the .JSON credentials file exists at the specified path before calling this function."
        )
        console.error(message=message, error=FileNotFoundError)

    # Verifies that the file has a .json extension
    if path.suffix.lower() != ".json":
        message = (
            f"Unable to set the Google Sheets credentials path. The specified file ({path}) does not have a .json "
            f"extension. Provide the path to the Google Sheets service account credentials .JSON file."
        )
        console.error(message=message, error=ValueError)

    # Resolves the path to the static .txt file used to store the path to the Google Sheets credentials file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("google_credentials_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Writes the absolute path to the credentials file
    with path_file.open("w") as f:
        f.write(str(path.resolve()))


def get_google_credentials_path() -> Path:
    """Resolves and returns the path to the Google service account credentials .JSON file.

    Returns:
        The path to the Google service account credentials .JSON file.

    Raises:
        FileNotFoundError: If the Google service account credentials path has not been configured for the host-machine,
            or if the previously configured credentials file no longer exists at the expected path.
    """
    # Uses appdirs to locate the user data directory and resolve the path to the credentials' path cache file
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("google_credentials_path.txt")

    # If the cache file does not exist, aborts with an error
    if not path_file.exists():
        message = (
            "Unable to resolve the path to the Google account credentials file, as it has not been set. "
            "Set the Google service account credentials path by using the 'sl-configure google' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Once the location of the path storage file is resolved, reads the file path from the file
    with path_file.open() as f:
        credentials_path = Path(f.read().strip())

    # If the credentials' file does not exist at the cached path, aborts with an error
    if not credentials_path.exists():
        message = (
            "Unable to resolve the path to the Google account credentials file, as the previously configured "
            f"credentials file does not exist at the expected path ({credentials_path}). Set a new credentials path "
            "by using the 'sl-configure google' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    # Returns the path to the credentials' file
    return credentials_path


def create_server_configuration_file(
    username: str,
    password: str,
    host: str = "cbsuwsun.biopic.cornell.edu",
    storage_root: str = "/local/workdir",
    working_root: str = "/local/storage",
    shared_directory_name: str = "sun_data",
) -> None:
    """Creates the .YAML configuration file for the Sun lab compute server and configures the local machine (PC) to use
    this file for all future server-related calls.

    Notes:
        This function creates the configuration file inside the shared Sun lab's working directory on the local machine.

    Args:
        username: The username to use for server authentication.
        password: The password to use for server authentication.
        host: The hostname or IP address of the server to connect to.
        storage_root: The path to the server's storage (slow) HDD RAID volume.
        working_root: The path to the server's working (fast) NVME RAID volume.
        shared_directory_name: The name of the shared directory that stores Sun lab's project data on both server
            volumes.
    """
    output_directory = get_working_directory().joinpath("configuration")
    ServerConfiguration(
        username=username,
        password=password,
        host=host,
        storage_root=storage_root,
        working_root=working_root,
        shared_directory_name=shared_directory_name,
    ).to_yaml(file_path=output_directory.joinpath("server_configuration.yaml"))
    console.echo(message="Server configuration file: Created.", level=LogLevel.SUCCESS)


def get_server_configuration() -> ServerConfiguration:
    """Resolves and returns the Sun lab compute server's configuration data as a ServerConfiguration instance.

    Returns:
        The loaded and validated server configuration data, stored in a ServerConfiguration instance.

    Raises:
        FileNotFoundError: If the configuration file does not exist in the local Sun lab's working directory.
        ValueError: If the configuration file exists, but is not properly configured.
    """
    # Gets the path to the local working directory.
    working_directory = get_working_directory().joinpath("configuration")

    # Resolves the path to the server configuration file.
    config_path = working_directory.joinpath("server_configuration.yaml")

    # Ensures that the configuration file exists.
    if not config_path.exists():
        message = (
            f"Unable to locate the 'server_configuration.yaml' file in the Sun lab's working directory "
            f"{config_path}. Call the 'sl-configure server' CLI command to create the server configuration file."
        )
        console.error(message=message, error=FileNotFoundError)
        raise FileNotFoundError(message)  # Fallback to appease mypy, should not be reachable

    # Loads the configuration file.
    configuration = ServerConfiguration.from_yaml(file_path=config_path)

    # Validates that the configuration is properly set up.
    if configuration.username == "" or configuration.password == "":
        message = (
            "The 'server_configuration.yaml' file appears to be unconfigured or contains placeholder access "
            "credentials. Call the 'sl-configure server' CLI command to reconfigure the server access credentials."
        )
        console.error(message=message, error=ValueError)
        raise ValueError(message)  # Fallback to appease mypy, should not be reachable

    # Returns the loaded configuration data to the caller.
    message = f"Server configuration: Resolved. Using the {configuration.username} account."
    console.echo(message=message, level=LogLevel.SUCCESS)
    return configuration
