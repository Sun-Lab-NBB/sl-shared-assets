"""This module stores the classes used to configure the multi-day (across-session) sl-suite2p pipeline. This pipeline
extends the original suite2p code to support tracking the same objects (cells) across multiple days. Both single-day
(original) and multi-day (extended) pipelines are available as part of the Sun lab maintained sl-suite2p package."""

from typing import Any
from dataclasses import field, asdict, dataclass
from pathlib import Path
import numpy as np
from ataraxis_base_utilities import ensure_directory_exists

from ataraxis_data_structures import YamlConfig


@dataclass()
class IO:
    """Stores parameters that control data input and output during various stages of the pipeline."""

    session_ids: list[str] = field(default_factory=list)
    """Stores the list of session IDs to register across days. This field should have the same length and order as the 
    session_folders list. Primarily, session IDs are used in terminal printouts to identify processed sessions to human 
    operators."""

    session_folders: list[str] = field(default_factory=list)
    """Specifies the list of sessions to register across days, as absolute paths to their /suite2p directories 
    e.g: root/session/processed_data/mesoscope_data/suite2p. The suite2p directory is created as part of the 
    single-session suite2p processing, assuming the default value of the 'save_folder' SingleDayS2PConfiguration class 
    attribute was not modified. Note, each suite2p directory has to contain the 'combined' plane folder, which is 
    created if the 'combined' SingleDayS2PConfiguration attribute is 'True'."""


@dataclass()
class Hardware:
    """Stores parameters that control how the suite2p interacts with the hardware of the host-computer to accelerate
    processing speed."""

    parallelize_registration: bool = True
    """Determines whether to parallelize certain multi-day registration pipeline steps. Running these steps in parallel
    results in faster overall processing, but increases the RAM usage. Since multi-day processing does not automatically
    parallelize operations to all cores, it is generally safe and recommended to always enable this option."""

    registration_workers: int = -1
    """The number of parallel workers (cores) to use when parallelizing multi-day registration. Setting this to a 
    negative value uses all available cores. Setting this to zero or one disables parallelization."""

    parallelize_extraction: bool = False
    """Determines whether to extract multi-day cell fluorescence from multiple sessions at the same time. Note, 
    fluorescence extraction already contains automatic parallelization and will use all available cores to a certain 
    extent. Extracting data for multiple sessions at the same time is still faster due to a more efficient core 
    utilization, but typically does not not scale well (peaks for 2-3 parallel sessions) and majorly increase the RAM 
    usage.
    """

    parallel_sessions: int = 3
    """The number of sessions to process in-parallel when extracting multi-day fluorescence data. Since this 
    parallelization works on top of existing suite2p numba-parallelization, it will use all available cores regardless 
    of the number of parallelized sessions. Instead, this parameter can be tuned to control the total RAM usage and 
    the extent of overall core utilization. Setting this to a value at or below one will disable session 
    parallelization."""


@dataclass()
class CellDetection:
    """Stores parameters for selecting single-day-registered cells (ROIs) to be tracked across multiple sessions (days).
    """

    probability_threshold: float = 0.85
    """The minimum required probability score assigned to the cell (ROI) by the single-day suite2p classifier. Cells 
    with a lower classifier score are excluded from multi-day processing."""

    maximum_size: int = 1000
    """The maximum allowed cell (ROI) size, in pixels. Cells with a larger pixel size are excluded from processing."""

    mesoscope_stripe_borders: list[int] = field(default_factory=list)
    """Stores the x-coordinates of combined mesoscope image stripe (ROI) borders. For mesoscope images, 'stripes' are 
    the individual imaging ROIs acquired in the 'multiple-ROI' mode. Keep this field set to an empty list to skip 
    stripe border-filtering or when working with non-mesoscope images.
    """

    stripe_margin: int = 30
    """The minimum required distance, in pixels, between the center-point (the median x-coordinate) of the cell (ROI) 
    and the mesoscope stripe border. Cells that are too close to stripe borders are excluded from processing to avoid 
    ambiguities associated with tracking cells that span multiple stripes. This parameter is only used if 
    'mesoscope_stripe_borders' field is not set to an empty list."""


@dataclass()
class Registration:
    """Stores parameters for aligning (registering) the sessions from multiple days to the same visual (sampling) space.
    """

    image_type: str = "enhanced"
    """The type of suite2p-generated reference image to use for across-day registration. Supported options are 
    'enhanced', 'mean' and 'max'. This 'template' image is used to calculate the necessary deformation (transformations)
    to register (align) all sessions to the same visual space."""

    grid_sampling_factor: float = 1
    """Determines to what extent the grid sampling scales with the deformed image scale. Has to be between 0 and 1. By 
    making this value lower than 1, the grid is relatively fine at the the higher scales, allowing for more 
    deformations. This is used when resizing session images as part of the registration process."""

    scale_sampling: int = 30
    """The number of iterations for each level (i.e. between each factor two in scale) to perform when computing the 
    deformations. Values between 20 and 30 are reasonable in most situations, but higher values yield better results in
    general. The speed of the algorithm scales linearly with this value."""

    speed_factor: float = 3
    """The relative force of the deformation transform applied when registering the sessions to the same visual space.
    This is the most important parameter to tune. For most cases, a value between 1 and 5 is reasonable."""


@dataclass()
class Clustering:
    """Stores parameters for tracking (clustering) cell (ROI) masks across multiple registered sessions (days)."""

    criterion: str = "distance"
    """Specifies the criterion for clustering (grouping) cell (ROI) masks from different sessions. Currently, the only 
    valid option is 'distance'."""

    threshold: float = 0.75
    """Specifies the threshold for the clustering algorithm. Cell masks will be clustered (grouped) together if their  
    clustering criterion is below this threshold value."""

    mask_prevalence: int = 50
    """Specifies the minimum percentage of all registered sessions that must include the clustered cell mask. Cell masks
    present in fewer percent of sessions than this value are excluded from processing. This parameter is used to filter
    out cells that are mostly silent or not distinguishable across sessions."""

    pixel_prevalence: int = 50
    """Specifies the minimum percentage of all registered sessions in which a cell mask pixel must be present for it to 
    be used to construct the template mask. Pixels present in fewer percent of sessions than this value are not used to 
    define the template masks. Template masks are used to extract the cell fluorescence from the original (non-deformed)
    visual space of every session. This parameter is used to isolate the part of the cell that is stable across 
    sessions, which is required for the extraction step to work correctly (target only the tracked cell)."""

    step_sizes: list[int] = field(default_factory=lambda: [200, 200])
    """Specifies the block size for the cell clustering (across-session tracking) process, in pixels, in the order of 
    (height, width). To reduce the memory (RAM) overhead, the algorithm divides the deformed (shared) visual space into 
    blocks and then processes one (or more) blocks at a time."""

    bin_size: int = 50
    """Specifies the size of bins used to discover cell masks within blocks during clustering. To avoid edge cases, the 
    algorithm clusters the cell masks within the region defined by the center-point of each cell +- bin_size. This works
    on top of pre-sorting cells into spatial blocks defined by 'step_sizes'."""

    maximum_distance: int = 20
    """Specifies the maximum distance, in pixels, that can separate masks across multiple sessions. The clustering 
    algorithm will consider cell masks located at most within this distance from each-other across days as the same 
    cells during tacking."""

    minimum_size: int = 25
    """The minimum size of the non-overlapping cell (ROI) region, in pixels, that has to be covered by the template 
    mask, for the cell to be assigned to that template. This is used to determine which template(s) the cell belongs to 
    (if any), for the purpose of tracking it across sessions."""


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
    """Stores parameters that control data input and output during various stages of the pipeline."""
    hardware: Hardware = field(default_factory=Hardware)
    """Stores parameters that control how the suite2p interacts with the hardware of the host-computer to accelerate
    processing speed."""
    cell_detection: CellDetection = field(default_factory=CellDetection)
    """Stores parameters for selecting single-day-registered cells (ROIs) to be tracked across multiple sessions (days).
    """
    registration: Registration = field(default_factory=Registration)
    """Stores parameters for aligning (registering) the sessions from multiple days to the same visual (sampling) space.
    """
    clustering: Clustering = field(default_factory=Clustering)
    """Stores parameters for tracking (clustering) cell (ROI) masks across multiple registered sessions (days)."""

    def to_npy(self, output_directory: Path) -> None:
        """Saves the managed configuration data as an 'ops.npy' file under the target directory.

        This method is mostly called by internal sl-suite2p functions to translate the user-specified configuration
        file into the format used by suite2p pipelines.

        Notes:
            If the target output directory does not exist when this method is called, it will be created.

        Args:
            output_directory: The path to the directory where the 'ops.npy' file should be saved.
        """
        ensure_directory_exists(output_directory)  # Creates the directory, if necessary
        file_path = output_directory.joinpath("ops.npy")  # Computes the output path
        np.save(file_path, self.to_ops(), allow_pickle=True)  # Dumps the configuration data to 'ops.npy' file.

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
        ensure_directory_exists(output_directory)  # Creates the directory, if necessary
        file_path = output_directory.joinpath("multi_day_s2p_configuration.yaml")   # Computes the output path

        # Note, this uses the same configuration name as the SessionData class, making it automatically compatible with
        # Sun lab data structure.
        self.to_yaml(file_path=file_path)  # Dumps the data to a 'yaml' file.

    def to_ops(self) -> dict[str, Any]:
        """Converts the class instance to a dictionary and returns it to caller.

        This method is mostly called by internal sl-suite2p functions to translate the default configuration parameters
        to the dictionary format used by suite2p pipelines.
        """
        return asdict(self)
