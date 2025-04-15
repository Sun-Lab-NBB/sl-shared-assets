"""A Python library that stores assets shared between multiple Sun (NeuroAI) lab data pipelines.

See https://github.com/Sun-Lab-NBB/sl-shared-assets for more details.
API documentation: https://sl-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Yuantao Deng
"""

from .server import Server, ServerCredentials
from .suite2p import (
    Main,
    FileIO,
    Output,
    Channel2,
    NonRigid,
    ROIDetection,
    Registration,
    Classification,
    OnePRegistration,
    SignalExtraction,
    CellposeDetection,
    SpikeDeconvolution,
    Suite2PConfiguration,
)
from .data_classes import (
    RawData,
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    Destinations,
    InjectionData,
    MesoscopeData,
    ProcedureData,
    ProcessedData,
    PersistentData,
    ZaberPositions,
    ExperimentState,
    MesoscopePositions,
    ProjectConfiguration,
    HardwareConfiguration,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    ExperimentConfiguration,
    MesoscopeExperimentDescriptor,
    replace_root_path,
)
from .transfer_tools import transfer_directory
from .packaging_tools import calculate_directory_checksum

__all__ = [
    # Server module
    "Server",
    "ServerCredentials",
    # Suite2p module
    "Main",
    "FileIO",
    "Output",
    "Channel2",
    "NonRigid",
    "ROIDetection",
    "Registration",
    "Classification",
    "OnePRegistration",
    "SignalExtraction",
    "CellposeDetection",
    "SpikeDeconvolution",
    "Suite2PConfiguration",
    # Data classes module
    "RawData",
    "DrugData",
    "ImplantData",
    "SessionData",
    "SubjectData",
    "SurgeryData",
    "Destinations",
    "InjectionData",
    "MesoscopeData",
    "ProcedureData",
    "ProcessedData",
    "PersistentData",
    "ZaberPositions",
    "ExperimentState",
    "MesoscopePositions",
    "ProjectConfiguration",
    "HardwareConfiguration",
    "RunTrainingDescriptor",
    "LickTrainingDescriptor",
    "ExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    "replace_root_path",
    # Transfer tools module
    "transfer_directory",
    # Packaging tools module
    "calculate_directory_checksum",
]
