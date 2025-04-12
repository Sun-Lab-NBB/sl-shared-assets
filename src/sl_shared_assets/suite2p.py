"""This module provides the classes used to store suite2p runtime configuration data. This is used by the sl-forgery
class to configure mesoscope data processing via the suite2p library."""

import json
from typing import Any, Dict, List
from pathlib import Path
from dataclasses import field, asdict, dataclass

import yaml
import numpy as np
from dacite import Config, from_dict
from ataraxis_base_utilities import console, ensure_directory_exists


@dataclass
class Main:
    """Global settings defining basic imaging parameters."""

    nplanes: int = 1
    """Number of imaging planes in each TIFF file sequence."""

    nchannels: int = 1
    """Number of channels per imaging plane."""

    functional_chan: int = 1
    """Channel used for extracting functional ROIs (1-based indexing, e.g., 1 means the first channel)."""

    tau: float = 1.0
    """Sensor time constant in seconds, used for computing the deconvolution kernel."""

    force_sktiff: bool = False
    """If True, force the use of scikit-image for reading TIFF files."""

    fs: float = 10.0
    """Sampling rate per plane in Hertz."""

    do_bidiphase: bool = False
    """Enable computation of bidirectional phase offset for misaligned line scanning (applies to two-photon
    recordings only)."""

    bidiphase: int = 0
    """User-specified bidirectional phase offset for line scanning experiments."""

    bidi_corrected: bool = False
    """Indicates whether bidirectional phase correction has been applied."""

    frames_include: int = -1
    """If greater than zero, only process that many frames; if negative, process all frames."""

    multiplane_parallel: bool = False
    """Enable parallel processing of multiplane data on server environments if set to True."""

    ignore_flyback: List[int] = field(default_factory=list)
    """List of plane indices to ignore as flyback planes that typically contain no valid imaging data."""


@dataclass
class FileIO:
    """File input/output settings for specifying data file locations, formats, and output storage options."""

    fast_disk: List[str] = field(default_factory=list)
    """List of paths for fast disks where temporary binary files will be stored."""

    delete_bin: bool = False
    """If True, delete the binary file created during the registration stage after processing."""

    mesoscan: bool = False
    """Indicates whether the input file is a ScanImage Mesoscope recording."""

    bruker: bool = False
    """Indicates whether the provided TIFF files are single-page BRUKER TIFFs."""

    bruker_bidirectional: bool = False
    """Specifies whether BRUKER files are bidirectional multiplane recordings."""

    h5py: List[str] = field(default_factory=list)
    """List of paths to h5py files that will be used as inputs."""

    h5py_key: str = "data"
    """Key used to access the data array in an h5py file."""

    nwb_file: str = ""
    """Path to the NWB file used as input."""

    nwb_driver: str = ""
    """Location or name of the driver for reading the NWB file."""

    nwb_series: str = ""
    """Name of the TwoPhotonSeries in the NWB file to retrieve data from."""

    save_path0: List[str] = field(default_factory=list)
    """List of directory paths where the pipeline results should be saved."""

    save_folder: List[str] = field(default_factory=list)
    """List of folder names under which the results should be stored."""

    look_one_level_down: bool = False
    """If True, search for TIFF files in the subfolders one level down."""

    subfolders: List[str] = field(default_factory=list)
    """List of specific subfolder names to search through for TIFF files."""

    move_bin: bool = False
    """If True and the 'fast_disk' differs from the save directory, move the binary file to the save directory 
    after processing."""


@dataclass
class Output:
    """Output settings defining the format and organization of the processing results."""

    preclassify: float = 0.0
    """Probability threshold for pre-classification of cells before signal extraction."""

    save_nwb: bool = False
    """If True, save the output as an NWB file."""

    save_mat: bool = False
    """If True, save the results in MATLAB format (e.g., Fall.mat)."""

    combined: bool = True
    """If True, combine results across planes into a separate 'combined' folder at the end of processing."""

    aspect: float = 1.0
    """Pixel-to-micron ratio (X:Y) for correctly displaying the image aspect ratio in the GUI (not used in 
    processing)."""

    report_time: bool = True
    """If True, return a dictionary reporting the processing time for each plane."""


@dataclass
class Registration:
    """Rigid registration settings used for correcting motion artifacts between frames."""

    do_registration: bool = True
    """Enable the registration process to correct for motion."""

    align_by_chan: int = 1
    """Channel to use for alignment (1-based index, typically the functional channel)."""

    nimg_init: int = 300
    """Number of frames used to compute the reference image for registration."""

    batch_size: int = 500
    """Number of frames to register simultaneously in each batch."""

    maxregshift: float = 0.1
    """Maximum allowed shift during registration as a fraction of the frame size (e.g., 0.1 indicates 10%)."""

    smooth_sigma: float = 1.15
    """Standard deviation (in pixels) of the Gaussian used to smooth the phase correlation between the reference
    image and the current frame."""

    smooth_sigma_time: float = 0.0
    """Standard deviation (in frames) of the Gaussian used to temporally smooth the data before computing 
    phase correlation."""

    keep_movie_raw: bool = False
    """If True, keep the binary file of the raw (non-registered) frames."""

    two_step_registration: bool = False
    """If True, perform a two-step registration (initial registration followed by refinement) for 
    low signal-to-noise data."""

    reg_tif: bool = False
    """If True, write the registered binary data to TIFF files."""

    reg_tif_chan2: bool = False
    """If True, generate TIFF files for the registered non-functional (channel 2) data."""

    subpixel: int = 10
    """Precision for subpixel registration (defines 1/subpixel steps)."""

    th_badframes: float = 1.0
    """Threshold for excluding poor-quality frames when performing cropping."""

    norm_frames: bool = True
    """Normalize frames during shift detection to improve registration accuracy."""

    force_refImg: bool = False
    """If True, force the use of a pre-stored reference image for registration."""

    pad_fft: bool = False
    """If True, pad the image during FFT-based registration to reduce edge effects."""


@dataclass
class OnePRegistration:
    """One-photon registration settings including spatial high-pass filtering and edge tapering."""

    one_p_reg: bool = False
    """If True, apply high-pass spatial filtering and tapering to improve one-photon image registration."""

    spatial_hp_reg: int = 42
    """Window size in pixels for spatial high-pass filtering before registration."""

    pre_smooth: float = 0.0
    """Standard deviation for Gaussian smoothing applied before spatial high-pass filtering 
    (applied only if > 0)."""

    spatial_taper: float = 40.0
    """Number of pixels to ignore at the image edges to reduce edge artifacts during registration."""


@dataclass
class NonRigid:
    """Non-rigid registration settings used to correct for local deformations and motion."""

    nonrigid: bool = True
    """Enable non-rigid registration to correct for local motion and deformation."""

    block_size: List[int] = field(default_factory=lambda: [128, 128])
    """Block size in pixels for non-rigid registration, defining the dimensions of subregions used in 
    the correction."""

    snr_thresh: float = 1.2
    """Signal-to-noise ratio threshold: the phase correlation peak must be this many times higher than the 
    noise level to accept the block shift."""

    maxregshiftNR: float = 5.0
    """Maximum allowed shift in pixels for each block relative to the rigid registration shift."""


@dataclass
class ROIDetection:
    """ROI detection and extraction settings for identifying cells and their activity signals."""

    roidetect: bool = True
    """Enable ROI detection and subsequent signal extraction."""

    sparse_mode: bool = True
    """Use sparse mode for cell detection, which is well-suited for data with sparse signals."""

    spatial_scale: int = 0
    """Optimal spatial scale (in pixels) of the recording to adjust detection sensitivity."""

    connected: bool = True
    """Require detected ROIs to be fully connected regions."""

    threshold_scaling: float = 1.0
    """Scaling factor for the detection threshold, controlling how distinctly ROIs stand out from 
    background noise."""

    spatial_hp_detect: int = 25
    """Window size in pixels for spatial high-pass filtering applied before neuropil subtraction during 
    ROI detection."""

    max_overlap: float = 0.75
    """Maximum allowed fraction of overlapping pixels between ROIs; ROIs exceeding this overlap 
    will be discarded."""

    high_pass: int = 100
    """Window size in frames for running mean subtraction over time to remove low-frequency drift."""

    smooth_masks: bool = True
    """Smooth the ROI masks in the final pass of cell detection if set to True."""

    max_iterations: int = 20
    """Maximum number of iterations allowed for cell extraction."""

    nbinned: int = 5000
    """Maximum number of binned frames to use for ROI detection to speed up processing."""

    denoise: bool = False
    """If True, denoise the binned movie before cell detection in sparse mode to enhance performance."""


@dataclass
class CellposeDetection:
    """Settings for cell detection using the Cellpose algorithm."""

    anatomical_only: int = 0
    """Mode for cell detection:
        0: Standard mode.
        1: Detect masks on the max projection divided by the mean image.
        2: Detect masks on the mean image.
        3: Detect masks on the enhanced mean image.
        4: Detect masks on the max projection image.
    """

    diameter: int = 0
    """Expected cell diameter (in pixels) to adjust the detection scale in Cellpose."""

    cellprob_threshold: float = 0.0
    """Threshold for cell probability in Cellpose, used to filter out low-confidence detections."""

    flow_threshold: float = 1.5
    """Flow threshold in Cellpose that controls sensitivity to cell boundaries."""

    spatial_hp_cp: int = 0
    """Window size in pixels for spatial high-pass filtering applied to the image before Cellpose processing."""

    pretrained_model: str = "cyto"
    """Pretrained model used by Cellpose. Can be a built-in model name (e.g., 'cyto') or a path to 
    a custom model."""


@dataclass
class SignalExtraction:
    """Settings for extracting fluorescence signals from ROIs and surrounding neuropil regions."""

    neuropil_extract: bool = True
    """If True, extract neuropil signals for background correction."""

    allow_overlap: bool = False
    """If True, allow pixels to be used in the signal extraction for multiple ROIs (typically False to 
    avoid contamination)."""

    min_neuropil_pixels: int = 350
    """Minimum number of pixels required to compute the neuropil signal for each cell."""

    inner_neuropil_radius: int = 2
    """Number of pixels to leave as a gap between the ROI and the surrounding neuropil region to avoid 
    signal bleed-over."""

    lam_percentile: int = 50
    """Percentile used to exclude the brightest pixels when computing the neuropil signal."""


@dataclass
class SpikeDeconvolution:
    """Settings for deconvolving calcium signals to infer spike trains."""

    spikedetect: bool = True
    """If True, perform spike deconvolution to convert calcium signals into estimated spike trains."""

    neucoeff: float = 0.7
    """Neuropil coefficient applied for signal correction before deconvolution."""

    baseline: str = "maximin"
    """Method to compute the baseline of each trace (e.g., 'maximin', 'mean')."""

    win_baseline: float = 60.0
    """Time window (in seconds) used for the maximin filter to compute the baseline."""

    sig_baseline: float = 10.0
    """Standard deviation (in seconds) of the Gaussian filter applied to smooth the baseline signal."""

    prctile_baseline: int = 8
    """Percentile used to determine the baseline level of each trace (typically a low percentile reflecting 
    minimal activity)."""


@dataclass
class Classification:
    """Settings for classifying detected ROIs as real cells or artifacts."""

    soma_crop: bool = True
    """If True, crop dendritic regions from detected ROIs to focus on the cell body for classification purposes."""

    use_builtin_classifier: bool = False
    """If True, use the built-in classifier for cell detection."""

    classifier_path: str = ""
    """Path to a custom classifier file if not using the built-in classifier."""


@dataclass
class Channel2:
    """Settings for processing the second channel in multi-channel datasets."""

    chan2_thres: int = 0
    """Threshold for considering an ROI as detected in the second channel."""


@dataclass
class Miscellaneous:
    """Miscellaneous settings and metadata, including version information."""

    suite2p_version: str = ""
    """Version of the Suite2p pipeline used, which aids in reproducibility and documentation."""


""" Nested class for extra configuration parameters.
    This field is intended to store extra subfields that exist in the input file
    but are not defined in the default MyConfig schema."""


@dataclass
class Extra:
    fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UniConfig:
    """
    A Python dataclass bundled with methods to save and load itself from a .json file.

    This class can be used as a base class for configuration classes.
    It provides methods to:
      - Convert the instance into a dictionary and write it to a JSON file.
      - Instantiate a new instance from data stored in a JSON file.

    Subclasses should define their own fields.
    """

    def to_json(self, file_path: Path) -> None:
        """
        Converts the dataclass instance to a dictionary and saves it as a .json file.

        Args:
            file_path: The path to the JSON file to write.
                       The file path must end with ".json". If the file does not exist, the directory
                       will be created; if it exists, it will be overwritten.

        Raises:
            ValueError: If the file path does not have a '.json' extension.
        """

        # Ensure the file extension is .json
        if file_path.suffix.lower() != ".json":
            message = f"Invalid file path provided. Expected a path ending with '.json', but got {file_path}."
            console.error(message=message, error=ValueError)

        # Ensure that the output directory exists
        ensure_directory_exists(file_path)

        instance_data = asdict(self)

        # Write the instance data to the JSON file with indentation for readability
        with open(file_path, "w") as json_file:
            json.dump(instance_data, json_file)

    @classmethod
    def from_json(cls, file_path: Path) -> "UniConfig":
        """
        Instantiates the class using data loaded from the provided .json file.

        This method reads the JSON file, converts it to a dictionary, and then uses dacite
        to instantiate the class. It disables dacite's built-in type checking, so you may need to
        add extra validation if required.

        Args:
            file_path: The path to the JSON file to read.

        Returns:
            A new dataclass instance created using the data read from the JSON file.

        Raises:
            ValueError: If the file path does not have a '.json' extension.
        """
        # Ensure the file extension is .json
        if file_path.suffix.lower() != ".json":
            message = f"Invalid file path provided. Expected a path ending with '.json', but got {file_path}."
            console.error(message=message, error=ValueError)

        # Disable dacite's built-in type checking
        class_config = Config(check_types=False)

        # Open and read the JSON file
        with open(file_path, "r") as json_file:
            data = json.load(json_file)

        # Convert the loaded data to a dictionary
        config_dict: dict[Any, Any] = dict(data)

        # Use dacite to instantiate the dataclass from the dictionary
        instance = from_dict(data_class=cls, data=config_dict, config=class_config)
        return instance

    def to_npy(self, file_path: Path) -> None:
        """
        Converts the dataclass instance to a dictionary and saves it as an .npy file.

        Args:
            file_path: The path to the NPY file to write.
                       The file path must end with ".npy". If the file does not exist, the directory
                       will be created; if it exists, it will be overwritten.

        Raises:
            ValueError: If the file path does not have a '.npy' extension.
        """
        if file_path.suffix.lower() != ".npy":
            message = f"Invalid file path provided. Expected a path ending with '.npy', but got {file_path}."
            console.error(message=message, error=ValueError)

        # Ensure that the output directory exists
        ensure_directory_exists(file_path)

        # Convert the dataclass instance to a dictionary
        instance_data = asdict(self)

        # Save the dictionary to an .npy file (using pickle under the hood)
        np.save(file_path, instance_data)

    @classmethod
    def from_npy(cls, file_path: Path) -> "UniConfig":
        """
        Instantiates the class using data loaded from the provided .npy file.

        This method reads the NPY file, converts it to a dictionary, and then uses dacite
        to instantiate the class. It disables dacite's built-in type checking, so you may need to
        add extra validation if required.

        Args:
            file_path: The path to the NPY file to read.

        Returns:
            A new dataclass instance created using the data read from the NPY file.

        Raises:
            ValueError: If the file path does not have a '.npy' extension.
        """
        if file_path.suffix.lower() != ".npy":
            message = f"Invalid file path provided. Expected a path ending with '.npy', but got {file_path}."
            console.error(message=message, error=ValueError)

        # Load the data from the .npy file.
        loaded = np.load(file_path, allow_pickle=True)
        # If the loaded object is a numpy array (as is typical), extract the original dictionary.
        if isinstance(loaded, np.ndarray):
            loaded = loaded.item()

        config_dict: dict[Any, Any] = dict(loaded)

        # Disable dacite's built-in type checking.
        class_config = Config(check_types=False)

        # Instantiate the dataclass using dacite.
        instance = from_dict(data_class=cls, data=config_dict, config=class_config)
        return instance

    def to_yaml(self, file_path: Path) -> None:
        """Converts the class instance to a dictionary and saves it as a .yml (YAML) file at the provided path.

        This method is designed to dump the class data into an editable .yaml file. This allows storing the data in
        non-volatile memory and manually editing the data between save / load cycles.

        Args:
            file_path: The path to the .yaml file to write. If the file does not exist, it will be created, alongside
                any missing directory nodes. If it exists, it will be overwritten (re-created). The path has to end
                with a '.yaml' or '.yml' extension suffix.

        Raises:
            ValueError: If the output path does not point to a file with a '.yaml' or '.yml' extension.
        """
        # Defines YAML formatting options. The purpose of these settings is to make YAML blocks more readable when
        # being edited offline.
        yaml_formatting = {
            "default_style": "",  # Use single or double quotes for scalars as needed
            "default_flow_style": False,  # Use block style for mappings
            "indent": 10,  # Number of spaces for indentation
            "width": 200,  # Maximum line width before wrapping
            "explicit_start": True,  # Mark the beginning of the document with ___
            "explicit_end": True,  # Mark the end of the document with ___
            "sort_keys": False,  # Preserves the order of the keys as written by creators
        }

        # Ensures that the output file path points to a .yaml (or .yml) file
        if file_path.suffix != ".yaml" and file_path.suffix != ".yml":
            message: str = (
                f"Invalid file path provided when attempting to write the YamlConfig class instance to a yaml file. "
                f"Expected a path ending in the '.yaml' or '.yml' extension, but encountered {file_path}. Provide a "
                f"path that uses the correct extension."
            )
            console.error(message=message, error=ValueError)

        # Ensures that the output directory exists. Co-opts a method used by Console class to ensure log file directory
        # exists.
        # noinspection PyProtectedMember
        ensure_directory_exists(file_path)

        # Writes the data to a .yaml file using custom formatting defined at the top of this method.
        with open(file_path, "w") as yaml_file:
            yaml.dump(data=asdict(self), stream=yaml_file, **yaml_formatting)  # type: ignore

    @classmethod
    def from_yaml(cls, file_path: Path) -> "UniConfig":
        """Instantiates the class using the data loaded from the provided .yaml (YAML) file.

        This method is designed to re-initialize dataclasses from the data stored in non-volatile memory as .yaml / .yml
        files. The method uses dacite, which adds support for complex nested configuration class structures.

        Notes:
            This method disables built-in dacite type-checking before instantiating the class. Therefore, you may need
            to add explicit type-checking logic for the resultant class instance to verify it was instantiated
            correctly.

        Args:
            file_path: The path to the .yaml file to read the class data from.

        Returns:
            A new dataclass instance created using the data read from the .yaml file.

        Raises:
            ValueError: If the provided file path does not point to a .yaml or .yml file.
        """
        # Ensures that config_path points to a .yaml / .yml file.
        if file_path.suffix != ".yaml" and file_path.suffix != ".yml":
            message: str = (
                f"Invalid file path provided when attempting to create the YamlConfig class instance from a yaml file. "
                f"Expected a path ending in the '.yaml' or '.yml' extension, but encountered {file_path}. Provide a "
                f"path that uses the correct extension."
            )
            console.error(message=message, error=ValueError)

        # Disables built-in dacite type-checking
        class_config = Config(check_types=False)

        # Opens and reads the .yaml file. Note, safe_load may not work for reading python tuples, so it is advised
        # to avoid using tuple in configuration files.
        with open(file_path) as yml_file:
            data = yaml.safe_load(yml_file)

        # Converts the imported data to a python dictionary.
        config_dict: dict[Any, Any] = dict(data)

        # Uses dacite to instantiate the class using the imported dictionary. This supports complex nested structures
        # and basic data validation.
        instance = from_dict(data_class=cls, data=config_dict, config=class_config)

        # Uses the imported dictionary to instantiate a new class instance and returns it to caller.
        return instance


@dataclass
class MyConfig(UniConfig):
    """
    A configuration class with a hierarchical structure using nested classes.
    You can access configuration items like:
        config.main.nplanes
        config.file_io.save_folder
    """

    # Define the instances of each nested settings class as fields
    main: Main = field(default_factory=Main)
    file_io: FileIO = field(default_factory=FileIO)
    output: Output = field(default_factory=Output)
    registration: Registration = field(default_factory=Registration)
    one_p_registration: OnePRegistration = field(default_factory=OnePRegistration)
    non_rigid: NonRigid = field(default_factory=NonRigid)
    roi_detection: ROIDetection = field(default_factory=ROIDetection)
    cellpose_detection: CellposeDetection = field(default_factory=CellposeDetection)
    signal_extraction: SignalExtraction = field(default_factory=SignalExtraction)
    spike_deconvolution: SpikeDeconvolution = field(default_factory=SpikeDeconvolution)
    classification: Classification = field(default_factory=Classification)
    channel2: Channel2 = field(default_factory=Channel2)
    miscellaneous: Miscellaneous = field(default_factory=Miscellaneous)
    extra: Extra = field(default_factory=Extra)


# Tset Example
def main():
    input_file = Path("ops.json")
    output_file = Path("test.json")

    try:
        config = MyConfig.from_json(input_file)
    except Exception as e:
        print(f"loading error：{e}")
        return

    config.main.nplanes = config.main.nplanes + 1

    try:
        config.to_json(output_file)
    except Exception as e:
        print(f"saving error：{e}")
        return

    print(f"successfully loaded from '{input_file}' and saved to '{output_file}'.")


if __name__ == "__main__":
    main()
