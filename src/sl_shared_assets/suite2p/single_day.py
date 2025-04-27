"""This module stores the classes used to configure the single-day (within-session) sl-suite2p pipeline. This is the
'original' suite2p pipeline used to process brain activity data collected as part of a single continuous recording. It
is used as the first step of the multi-day brain activity processing pipeline used in the lab. Both single-day
(original) and multi-day (extended) pipelines are available as part of the Sun lab maintained sl-suite2p package."""

from typing import Any
from dataclasses import field, asdict, dataclass

from ataraxis_data_structures import YamlConfig


@dataclass
class Main:
    """Stores global parameters that broadly define the suite2p single-day processing configuration."""

    nplanes: int = 3
    """The number of imaging planes in each TIFF file sequence. For Mesoscope frames, this is the number of individual 
    ROI boxes drawn over the cranial window."""

    nchannels: int = 1
    """The number of channels per imaging plane. Typically this is either 1 or 2."""

    functional_chan: int = 1
    """The channel used for extracting functional ROIs (uses 1-based indexing, e.g., 1 means the first channel)."""

    tau: float = 0.4
    """The timescale of the sensor, in seconds, used for computing the deconvolution kernel. The kernel is fixed to 
    have this decay and is not fit to the data. Note, the default value is optimized for GCamp6f animals recorded with 
    the Mesoscope."""

    force_sktiff: bool = True
    """Determines whether to force the use of scikit-image for reading TIFF files. Generally, it is recommended to have 
    this enabled as it forces suite2p to use tifffile library, which has better safety and compatibility than 
    ScanImage tiff reader for certain types of tiff files."""

    fs: float = 10.0014
    """The sampling rate per plane in Hertz. For instance, if you have a 10 plane recording acquired at 30Hz, then the 
    sampling rate per plane is 3Hz, so set this to 3."""

    do_bidiphase: bool = False
    """Determines whether to perform computation of bidirectional phase offset for misaligned line scanning 
    (applies to two-photon recordings only). The suite2p estimates the bidirectional phase offset from 
    ‘nimg_init’ frames if this is set to 1 (and ‘bidiphase’ to 0), and then applies this computed offset to all 
    frames."""

    bidiphase: int = 0
    """The user-specified bidirectional phase offset for line scanning experiments. If set to any value besides 0, then 
    this offset is used and applied to all frames in the recording."""

    bidi_corrected: bool = False
    """Indicates whether bidirectional phase correction has been applied tot he registered dataset."""

    frames_include: int = -1
    """Determines the number of frames to process, if greater than zero. If negative (-1), the suite2p is configured
     to process all available frames."""

    multiplane_parallel: bool = True
    """Determines whether to parallelize plane processing for multiplane data. Note, while enabling this option improves
    processing speeds, it also increases the memory (RAM) overhead resulting from processing all planes in-parallel.
    """

    ignore_flyback: list[int] = field(default_factory=list)
    """The list of plane indices to ignore as flyback planes that typically contain no valid imaging data."""


@dataclass
class FileIO:
    """Stores general I/O parameters that specify input data location, format, and working and output directories."""

    fast_disk: list[str] = field(default_factory=list)
    """Specifies the locations where to store the temporary binary files created during processing. If no directories 
    are provided here, 'save_path0' is used to store the temporary files."""

    delete_bin: bool = False
    """Determines whether to delete the binary file created during the cell registration stage (registered cells .bin 
    file). Since registered cell binaries are used by multi-day registration extension, this need to be False for all 
    lab recordings."""

    mesoscan: bool = True
    """Indicates whether the input file is a ScanImage Mesoscope recording. For our data, this is always True and all 
    other formats are False."""

    bruker: bool = False
    """Indicates whether the provided TIFF files are single-page BRUKER TIFFs."""

    bruker_bidirectional: bool = False
    """Specifies whether BRUKER files are bidirectional multiplane recordings."""

    h5py: list[str] = field(default_factory=list)
    """The list of paths to h5py files that will be used as inputs. If provided, these paths overwrite the 'data_path' 
    field."""

    h5py_key: str = "data"
    """The key used to access the data array in an h5py file. This should only be provided if 'h5py' is not set to 
    an empty list."""

    nwb_file: str = ""
    """Specifies the path to the NWB file to use as an input."""

    nwb_driver: str = ""
    """The location or name of the driver for reading the NWB file."""

    nwb_series: str = ""
    """The name of the TwoPhotonSeries in the NWB file to retrieve data from."""

    save_path0: list[str] = field(default_factory=list)
    """Lists directory paths where the pipeline results should be saved. Typically, this is defined as a single-item 
    list that stores the path to the output folder used by the processed session's data."""

    save_folder: list[str] = field(default_factory=list)
    """Lists folder names under which the results should be stored. If this is not provided, the pipeline defaults to 
    using 'suite2p' as the root folder, created under the path specified by save_path0. Note, if the data produced by 
    the 'single-day' pipeline is also processed using sl-suite2p 'multi-day' pipeline, do not modify this field. The 
    multi-day pipeline expects the save_folder to be 'suite2p' (default)."""

    look_one_level_down: bool = False
    """Determines whether to search for TIFF files in the subfolders when searching for Tiff files. If this is True, 
    the list of evaluated subfolders have to be defined via the 'subfolders' field."""

    subfolders: list[str] = field(default_factory=list)
    """The list of specific subfolder names to search through for TIFF files."""

    move_bin: bool = False
    """Determines whether to move the binary file to the save directory after processing, if 'fast_disk' differs from 
    the 'save_path0'."""


@dataclass
class Output:
    """Stores I/O settings that specify the output format and organization of the data processing results."""

    preclassify: float = 0.5
    """The probability threshold for pre-classification of cells to use before signal extraction. If this is set to 
    0.0, then all detected ROIs are kept and signals are computed."""

    save_nwb: bool = False
    """Determines whether to save the output as an NWB file."""

    save_mat: bool = False
    """Determines whether to save the results in MATLAB format (e.g., Fall.mat)."""

    combined: bool = True
    """Determines whether to combine results across planes into a separate 'combined' folder at the end of 
    processing."""

    aspect: float = 0.666666666
    """The pixel-to-micron ratio (X:Y) for correctly displaying the image aspect ratio in the GUI (not used in headless
    processing)."""

    report_time: bool = False
    """Determines whether to return a dictionary reporting the processing time for each plane."""


@dataclass
class Registration:
    """Stores parameters for rigid registration, which is used to correct motion artifacts between frames."""

    do_registration: bool = True
    """Determines whether to run the motion registration."""

    align_by_chan: int = 1
    """The channel to use for alignment (uses 1-based indexing, so 1 means 1st channel and 2 means 2nd channel). If the
    recording features both a functional and non-functional channels, it may be better to use the non-functional 
    channel for this purpose."""

    nimg_init: int = 500
    """The number of frames to use to compute the reference image for registration."""

    batch_size: int = 100
    """The number of frames to register simultaneously in each batch. When processing data on fast (NVME) drives, 
    increasing this parameter has minimal benefits and results in undue RAM use overhead. Therefore, on fast drives, 
    keep this number low. On slow drives, increasing this number may result in faster runtime, at the expense of 
    increased RAM use."""

    maxregshift: float = 0.1
    """The maximum allowed shift during registration, given as a fraction of the frame size, in pixels
    (e.g., 0.1 indicates 10%)."""

    smooth_sigma: float = 1.15
    """The standard deviation (in pixels) of the Gaussian used to smooth the phase correlation between the reference
    image and the current frame."""

    smooth_sigma_time: float = 0.0
    """The standard deviation (in frames) of the Gaussian used to temporally smooth the data before computing 
    phase correlation."""

    keep_movie_raw: bool = False
    """Determines whether to keep the binary file of the raw (non-registered) frames. This is desirable when initially 
    configuring the suite2p parameters, as it allows visually comparing registered frames to non-registered frames in 
    the GUI. For well-calibrated runtime, it is advised to have this set to False."""

    two_step_registration: bool = False
    """Determines whether to perform a two-step registration (initial registration followed by refinement registration).
    This may be necessary for low signal-to-noise data. This requires 'keep_movie_raw' to be set to True."""

    reg_tif: bool = False
    """Determines whether to write the registered binary data to TIFF files."""

    reg_tif_chan2: bool = False
    """Determines whether to generate TIFF files for the registered non-functional (channel 2) data."""

    subpixel: int = 10
    """The precision for the subpixel registration (1/subpixel steps)."""

    th_badframes: float = 1.0
    """The threshold for excluding poor-quality frames when performing cropping. Setting this to a smaller value 
    excludes more frames."""

    norm_frames: bool = True
    """Determines whether to normalize frames during shift detection to improve registration accuracy."""

    force_refImg: bool = False
    """Determines whether to force the use of a pre-stored reference image for registration."""

    pad_fft: bool = False
    """Determines whether to pad the image during the FFT portion of the registration to reduce edge effects."""


@dataclass
class OnePRegistration:
    """Stores parameters for additional pre-registration processing used to improve the registration of 1-photon
    datasets."""

    one_p_reg: bool = False
    """Determines whether to perform high-pass spatial filtering and tapering to improve one-photon image 
    registration. For 2-photon datasets, this should be set to False."""

    spatial_hp_reg: int = 42
    """The window size, in pixels, for spatial high-pass filtering performed before registration."""

    pre_smooth: float = 0.0
    """The standard deviation for Gaussian smoothing applied before spatial high-pass filtering 
    (applied only if > 0)."""

    spatial_taper: float = 40.0
    """The number of pixels to ignore at the image edges to reduce edge artifacts during registration."""


@dataclass
class NonRigid:
    """Stores parameters for non-rigid registration, which is used to improve motion registration in complex
    datasets."""

    nonrigid: bool = True
    """Determines whether to perform non-rigid registration to correct for local motion and deformation. This is used 
    for correcting non-uniform motion."""

    block_size: list[int] = field(default_factory=lambda: [128, 128])
    """The block size, in pixels, for non-rigid registration, defining the dimensions of subregions used in 
    the correction. It is recommended to keep this size a power of 2 and / or 3 for more efficient FFT computation."""

    snr_thresh: float = 1.2
    """The signal-to-noise ratio threshold. The phase correlation peak must be this many times higher than the 
    noise level for the algorithm to accept the block shift and apply it to the output dataset."""

    maxregshiftNR: float = 5.0
    """The maximum allowed shift, in pixels, for each block relative to the rigid registration shift."""


@dataclass
class ROIDetection:
    """Stores parameters for cell ROI detection and extraction."""

    roidetect: bool = True
    """Determines whether to perform ROI detection and subsequent signal extraction."""

    sparse_mode: bool = True
    """Determines whether to use the sparse mode for cell detection, which is well-suited for data with sparse 
    signals."""

    spatial_scale: int = 0
    """The optimal spatial scale, in pixels, of the recording. This is used to adjust detection sensitivity. A value of
    0 means automatic detection based on the recording's spatial scale. Values above 0 are applied in increments of 6 
    pixels (1 -> 6 pixels, 2-> 12 pixels, etc.)."""

    connected: bool = True
    """Determines whether to require the detected ROIs to be fully connected regions."""

    threshold_scaling: float = 2.0
    """The scaling factor for the detection threshold. This determines how distinctly ROIs have to stand out from 
    background noise to be considered valid."""

    spatial_hp_detect: int = 25
    """The window size, in pixels, for spatial high-pass filtering applied before neuropil subtraction during 
    ROI detection."""

    max_overlap: float = 0.75
    """The maximum allowed fraction of overlapping pixels between ROIs. ROIs that overlap above this threshold are be 
    discarded."""

    high_pass: int = 100
    """The window size, in frames, for running mean subtraction over time to remove low-frequency drift."""

    smooth_masks: bool = True
    """Determines whether to smooth the ROI masks in the final pass of cell detection."""

    max_iterations: int = 50
    """The maximum number of iterations allowed for cell extraction."""

    nbinned: int = 5000
    """The maximum number of binned frames to use for ROI detection. Settings this value to a higher number leads to 
    more ROIs being detected, but reduces processing speed and increases RAM overhead."""

    denoise: bool = False
    """Determines whether to denoise the binned movie before cell detection in sparse mode to enhance performance. 
    If enabled, 'sparse_mode' has to be True."""


@dataclass
class CellposeDetection:
    """Stores parameters for the Cellpose algorithm, which can optionally be used to improve cell ROI extraction."""

    anatomical_only: int = 0
    """Specifies the Cellpose mode for cell detection:
        0: Do not use Cellpose. This automatically disables all other fields in this section.
        1: Detect masks on the max projection divided by the mean image.
        2: Detect masks on the mean image.
        3: Detect masks on the enhanced mean image.
        4: Detect masks on the max projection image.
    """

    diameter: int = 0
    """Specifies the diameter, in pixels, of cells to look for. If set to 0, Cellpose estimates the diameter 
    automatically.."""

    cellprob_threshold: float = 0.0
    """The threshold for cell detection, used to filter out low-confidence detections."""

    flow_threshold: float = 1.5
    """The flow threshold, used to control the sensitivity to cell boundaries."""

    spatial_hp_cp: int = 0
    """The window size, in pixels, for spatial high-pass filtering applied to the image before Cellpose processing."""

    pretrained_model: str = "cyto"
    """Specifies the pretrained model to use for cell detection. Can be a built-in model name (e.g., 'cyto') or a 
    path to a custom model."""


@dataclass
class SignalExtraction:
    """Stores parameters for extracting fluorescence signals from ROIs and surrounding neuropil regions."""

    neuropil_extract: bool = True
    """Determines whether to extract neuropil signals."""

    allow_overlap: bool = False
    """Determines whether to allow overlap pixels (pixels shared by multiple ROIs) to be used in the signal extraction. 
    Typically this is set to False to avoid contamination."""

    min_neuropil_pixels: int = 350
    """The minimum number of pixels required to compute the neuropil signal for each cell."""

    inner_neuropil_radius: int = 2
    """The number of pixels to keep between the ROI and the surrounding neuropil region to avoid signal bleed-over."""

    lam_percentile: int = 50
    """The percentile of Lambda within area to ignore when excluding the brightest pixels during neuropil extraction."""


@dataclass
class SpikeDeconvolution:
    """Stores parameters for deconvolve fluorescence signals to infer spike trains."""

    spikedetect: bool = True
    """Determines whether to perform spike deconvolution."""

    neucoeff: float = 0.7
    """The neuropil coefficient applied for signal correction before deconvolution."""

    baseline: str = "maximin"
    """Specifies the method to compute the baseline of each trace. This baseline is then subtracted from each cell. 
    ‘maximin’ computes a moving baseline by filtering the data with a Gaussian of width 'sig_baseline' * 'fs', and then 
    minimum filtering with a window of 'win_baseline' * 'fs', and then maximum filtering with the same window. 
    ‘constant’ computes a constant baseline by filtering with a Gaussian of width 'sig_baseline' * 'fs' and then taking 
    the minimum value of this filtered trace. ‘constant_percentile’ computes a constant baseline by taking the 
    'prctile_baseline' percentile of the trace."""

    win_baseline: float = 60.0
    """The time window, in seconds, over which to compute the baseline filter."""

    sig_baseline: float = 10.0
    """The standard deviation, in seconds, of the Gaussian filter applied to smooth the baseline signal."""

    prctile_baseline: float = 8.0
    """The percentile used to determine the baseline level of each trace (typically a low percentile reflecting 
    minimal activity)."""


@dataclass
class Classification:
    """Stores parameters for classifying detected ROIs as real cells or artifacts."""

    soma_crop: bool = True
    """Determines whether to crop dendritic regions from detected ROIs to focus on the cell body for classification 
    purposes."""

    use_builtin_classifier: bool = False
    """Determines whether to use the built-in classifier for cell detection."""

    classifier_path: str = ""
    """The path to a custom classifier file, if not using the built-in classifier."""


@dataclass
class Channel2:
    """Stores parameters for processing the second channel in multichannel datasets."""

    chan2_thres: float = 0.65
    """The threshold for considering an ROI registered in one channel as detected in the second channel."""


@dataclass
class SingleDayS2PConfiguration(YamlConfig):
    """Stores the user-addressable suite2p configuration parameters for the single-day (original) pipeline, organized
    into subsections.

    This class is used during single-day processing to instruct suite2p on how to process the data. This class is based
    on the 'default_ops' from the original suite2p package. As part of the suite2p refactoring performed in sl-suite2p
    package, the 'default_ops' has been replaced with this class instance. Compared to 'original' ops, it allows saving
    configuration parameters as a .YAML file, which offers a better way of viewing and editing the parameters and
    running suite2p pipeline on remote compute servers.

    Notes:
        The .YAML file uses section names that match the suite2p documentation sections. This way, users can always
        consult the suite2p documentation for information on the purpose of each field inside every subsection.
    """

    # Define the instances of each nested settings class as fields
    main: Main = field(default_factory=Main)
    """Stores global parameters that broadly define the suite2p single-day processing configuration."""
    file_io: FileIO = field(default_factory=FileIO)
    """Stores general I/O parameters that specify input data location, format, and working and output directories."""
    output: Output = field(default_factory=Output)
    """Stores I/O settings that specify the output format and organization of the data processing results."""
    registration: Registration = field(default_factory=Registration)
    """Stores parameters for rigid registration, which is used to correct motion artifacts between frames."""
    one_p_registration: OnePRegistration = field(default_factory=OnePRegistration)
    """Stores parameters for additional pre-registration processing used to improve the registration of 1-photon
    datasets."""
    non_rigid: NonRigid = field(default_factory=NonRigid)
    """Stores parameters for non-rigid registration, which is used to improve motion registration in complex 
    datasets."""
    roi_detection: ROIDetection = field(default_factory=ROIDetection)
    """Stores parameters for cell ROI detection and extraction."""
    cellpose_detection: CellposeDetection = field(default_factory=CellposeDetection)
    """Stores parameters for the Cellpose algorithm, which can optionally be used to improve cell ROI extraction."""
    signal_extraction: SignalExtraction = field(default_factory=SignalExtraction)
    """Stores parameters for extracting fluorescence signals from ROIs and surrounding neuropil regions."""
    spike_deconvolution: SpikeDeconvolution = field(default_factory=SpikeDeconvolution)
    """Stores parameters for deconvolve fluorescence signals to infer spike trains."""
    classification: Classification = field(default_factory=Classification)
    """Stores parameters for classifying detected ROIs as real cells or artifacts."""
    channel2: Channel2 = field(default_factory=Channel2)
    """Stores parameters for processing the second channel in multichannel datasets."""

    def to_ops(self) -> dict[str, Any]:
        """Converts the class instance to a dictionary and returns it to caller.

        This dictionary can be passed to suite2p functions either as an 'ops' or 'db' argument to control the
        processing runtime.
        """

        # Creates an empty dictionary to store all keys and values
        combined_ops = {}

        # Iterates through all dataclass fields
        # noinspection PyTypeChecker
        for section_name, section in asdict(self).items():
            # Adds all keys and values from each section to the combined dictionary
            if isinstance(section, dict):
                # Since some keys in the original suite2p configuration file use 'unconventional' names, we opted to use
                # conventional names in our configuration file. To make the 'ops' version of this file fully compatible
                # with suite2p, we need to translate all such modified keys back to values expected by suite2p.
                if "one_p_reg" in section.keys():
                    section["1Preg"] = section.pop("one_p_reg")
                combined_ops.update(section)

        return combined_ops
