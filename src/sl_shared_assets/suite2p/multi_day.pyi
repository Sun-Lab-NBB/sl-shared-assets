from typing import Any
from pathlib import Path
from dataclasses import field, dataclass

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig

@dataclass()
class IO:
    """Stores parameters that control data input and output during various stages of the pipeline."""

    session_ids: list[str] = field(default_factory=list)
    session_folders: list[str] = field(default_factory=list)

@dataclass()
class Hardware:
    """Stores parameters that control how the suite2p interacts with the hardware of the host-computer to accelerate
    processing speed."""

    parallelize_registration: bool = ...
    registration_workers: int = ...
    parallelize_extraction: bool = ...
    parallel_sessions: int = ...

@dataclass()
class CellDetection:
    """Stores parameters for selecting single-day-registered cells (ROIs) to be tracked across multiple sessions (days)."""

    probability_threshold: float = ...
    maximum_size: int = ...
    mesoscope_stripe_borders: list[int] = field(default_factory=list)
    stripe_margin: int = ...

@dataclass()
class Registration:
    """Stores parameters for aligning (registering) the sessions from multiple days to the same visual (sampling) space."""

    image_type: str = ...
    grid_sampling_factor: float = ...
    scale_sampling: int = ...
    speed_factor: float = ...

@dataclass()
class Clustering:
    """Stores parameters for tracking (clustering) cell (ROI) masks across multiple registered sessions (days)."""

    criterion: str = ...
    threshold: float = ...
    mask_prevalence: int = ...
    pixel_prevalence: int = ...
    step_sizes: list[int] = field(default_factory=Incomplete)
    bin_size: int = ...
    maximum_distance: int = ...
    minimum_size: int = ...

@dataclass()
class MultiDayS2PConfiguration(YamlConfig):
    """Aggregates all parameters for the multi-day suite2p pipeline used to track cells across multiple days
    (sessions) and extract their activity.

    These settings are used to configure the multi-day suite2p extraction pipeline, which is based on the reference
    implementation here: https://github.com/sprustonlab/multiday-suite2p-public. This class behaves similar to the
    SingleDayS2PConfiguration class. It can be saved and loaded from a .YAML file and translated to dictionary or
    ops.npy format, expected by the multi-day sl-suite2p pipeline.
    """

    io: IO = field(default_factory=IO)
    hardware: Hardware = field(default_factory=Hardware)
    cell_detection: CellDetection = field(default_factory=CellDetection)
    registration: Registration = field(default_factory=Registration)
    clustering: Clustering = field(default_factory=Clustering)
    def to_npy(self, output_directory: Path) -> None:
        """Saves the managed configuration data as an 'ops.npy' file under the target directory.

        This method is mostly called by internal sl-suite2p functions to translate the user-specified configuration
        file into the format used by suite2p pipelines.

        Notes:
            If the target output directory does not exist when this method is called, it will be created.

        Args:
            output_directory: The path to the directory where the 'ops.npy' file should be saved.
        """
    def to_config(self, output_directory: Path) -> None:
        """Saves the managed configuration data as a 'multi_day_s2p_configuration.yaml' file under the target
        directory.

        This method is typically used to dump the 'default' configuration parameters to disk as a user-editable
        .yaml file. The user is then expected to modify these parameters as needed, before the class data is loaded and
        used by the suite2p pipeline.

        Notes:
            If the target output directory does not exist when this method is called, it will be created.

        Args:
            output_directory: The path to the directory where the 'multi_day_s2p_configuration.yaml' file should be
            saved.
        """
    def to_ops(self) -> dict[str, Any]:
        """Converts the class instance to a dictionary and returns it to caller.

        This method is mostly called by internal sl-suite2p functions to translate the default configuration parameters
        to the dictionary format used by suite2p pipelines.
        """
